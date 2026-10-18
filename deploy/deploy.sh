#!/usr/bin/env bash
# Build and deploy MitraField: worker first, then API, each as a gated canary.
#
#   PROJECT=mitrafield-aibc26 ./deploy/deploy.sh          # from a laptop, or from GitHub Actions
#
# For each service: deploy the new revision with NO traffic and a tag, smoke-test it through the tag URL,
# and only then move traffic. A failed smoke test leaves the previous revision serving.
set -euo pipefail

PROJECT="${PROJECT:?set PROJECT}"
REGION="${REGION:-asia-southeast1}"
BUCKET="${BUCKET:-${PROJECT}-mitrafield-data}"
REPO="${REPO:-mitrafield}"
TAG="${IMAGE_TAG:-$(git rev-parse --short=12 HEAD)}"
REPO_IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/mitrafield"
IMAGE="${REPO_IMAGE}:${TAG}"
SA_DOMAIN="${PROJECT}.iam.gserviceaccount.com"
API_SA="mitrafield-api@${SA_DOMAIN}"; WORKER_SA="mitrafield-worker@${SA_DOMAIN}"
TASKS_SA="mitrafield-tasks@${SA_DOMAIN}"; DEPLOY_SA="mitrafield-deploy@${SA_DOMAIN}"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
# Cloud Run URLs are deterministic, which breaks the api<->worker chicken-and-egg without a second deploy.
WORKER_URL="https://mitrafield-worker-${PROJECT_NUMBER}.${REGION}.run.app"
API_URL="https://mitrafield-api-${PROJECT_NUMBER}.${REGION}.run.app"
# Model provider. Default: the Gemini API, with the key held in Secret Manager and readable by the worker only.
# STUDIO_VERTEX=1 switches to Vertex AI as the worker's service account (no key), whose GA Veo ids exist only in
# us-central1 (checked against the Vertex model catalogue on 2026-10-18).
STUDIO_VERTEX="${STUDIO_VERTEX:-0}"
if [ "$STUDIO_VERTEX" = 1 ]; then
  VEO_FAST="${VEO_FAST:-veo-3.1-fast-generate-001}"; VEO_LITE="${VEO_LITE:-veo-3.1-lite-generate-001}"
  PROVIDER_ENV=",STUDIO_VERTEX=1,STUDIO_MODEL_VEO=${VEO_FAST},STUDIO_MODEL_VEO_DRAFT=${VEO_LITE},STUDIO_VERTEX_LOCATIONS=${VERTEX_LOCATIONS:-${VEO_FAST}=us-central1;${VEO_LITE}=us-central1}"
  PROVIDER_SECRETS=""
else
  PROVIDER_ENV=",STUDIO_VERTEX=0${VEO_FAST:+,STUDIO_MODEL_VEO=${VEO_FAST}}${VEO_LITE:+,STUDIO_MODEL_VEO_DRAFT=${VEO_LITE}}"
  PROVIDER_SECRETS=",GEMINI_API_KEY=gemini-api-key:latest"
fi
VOICE_SA="mitrafield-voice@${SA_DOMAIN}"
VOICE_URL="https://mitrafield-voice-${PROJECT_NUMBER}.${REGION}.run.app"
VOICE_REPO_IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/mitrafield-voice"
VOLUME_OPTS="uid=10001,gid=10001,file-mode=666,dir-mode=777,implicit-dirs,metadata-cache-ttl-secs=30"
cd "$(dirname "$0")/.."

echo "== build $IMAGE"
gcloud builds submit --project "$PROJECT" --config deploy/cloudbuild.yaml --region "$REGION" \
  --substitutions="_IMAGE=${IMAGE},_REPO_IMAGE=${REPO_IMAGE}" .

exists() { gcloud run services describe "$1" --region "$REGION" --project "$PROJECT" >/dev/null 2>&1; }

# deploy <service> <extra gcloud flags...>: no-traffic canary when the service already exists
deploy() {
  local svc="$1"; shift
  local mode=()
  exists "$svc" && mode=(--no-traffic --tag canary)
  gcloud run deploy "$svc" --project "$PROJECT" --region "$REGION" --image "$IMAGE" "${mode[@]}" \
    --execution-environment gen2 --cpu-boost \
    --add-volume "name=data,type=cloud-storage,bucket=${BUCKET},mount-options=${VOLUME_OPTS//,/;}" \
    --add-volume-mount volume=data,mount-path=/data \
    --labels "app=mitrafield,commit=${TAG:0:12}" "$@"
}

promote() { # promote <service>: send all traffic to the newest revision (a no-op on first deploy)
  gcloud run services update-traffic "$1" --project "$PROJECT" --region "$REGION" --to-latest >/dev/null
  gcloud run services update-traffic "$1" --project "$PROJECT" --region "$REGION" --remove-tags canary >/dev/null 2>&1 || true
}

canary_url() { # canary_url <service>: tag URL when a canary exists, else the service URL
  local u; u="$(gcloud run services describe "$1" --region "$REGION" --project "$PROJECT" --format='value(status.url)')"
  if gcloud run services describe "$1" --region "$REGION" --project "$PROJECT" --format='value(status.traffic[].tag)' | grep -q canary; then
    echo "${u/https:\/\//https://canary---}"
  else echo "$u"; fi
}

retry() { local n=0; until "$@"; do n=$((n+1)); [ $n -ge 6 ] && return 1; sleep 10; done; }

# OmniVoice on a Cloud Run GPU: private, stateless, scales to zero. Optional (VOICE=0 skips it): without it the
# studio narrates in Gemini voices and hides voice cloning. A failed first deploy (e.g. no GPU quota in the
# region) does not block the release; a failed update leaves the previous revision serving.
deploy_voice() {
  local vtag; vtag="$(git ls-files -s voice | sha1sum | cut -c1-12)"   # the image changes only when voice/ does
  local vimg="${VOICE_REPO_IMAGE}:${vtag}"
  if ! gcloud artifacts docker images describe "$vimg" --project "$PROJECT" >/dev/null 2>&1; then
    echo "== build $vimg (torch + weights, slow the first time)"
    gcloud builds submit voice --project "$PROJECT" --config deploy/cloudbuild-voice.yaml --region "$REGION" \
      --substitutions="_IMAGE=${vimg},_REPO_IMAGE=${VOICE_REPO_IMAGE}" || return 1
  fi
  local mode=()
  exists mitrafield-voice && mode=(--no-traffic --tag canary)
  echo "== voice (private GPU, scales to zero)"
  gcloud run deploy mitrafield-voice --project "$PROJECT" --region "$REGION" --image "$vimg" ${mode[@]+"${mode[@]}"} \
    --no-allow-unauthenticated --service-account "$VOICE_SA" \
    --gpu 1 --gpu-type nvidia-l4 --no-gpu-zonal-redundancy --cpu 4 --memory 16Gi --no-cpu-throttling \
    --concurrency 4 --timeout 300 --min-instances 0 --max-instances 2 --labels "app=mitrafield,commit=${vtag}" || return 1
  for sa in "$WORKER_SA" "$DEPLOY_SA"; do
    gcloud run services add-iam-policy-binding mitrafield-voice --project "$PROJECT" --region "$REGION" \
      --member="serviceAccount:$sa" --role=roles/run.invoker >/dev/null || return 1
  done
  echo "== gate: voice service (model loaded on a GPU)"
  local tok; tok="$(gcloud auth print-identity-token --impersonate-service-account="$DEPLOY_SA" --audiences="$VOICE_URL" --include-email)"
  local n=0 u; u="$(canary_url mitrafield-voice)"
  until curl -fsS -H "Authorization: Bearer $tok" "$u/health" | tee /dev/stderr | grep -q '"cuda":true'; do
    n=$((n+1)); [ $n -ge 30 ] && return 1; sleep 10   # a cold GPU instance takes a few minutes
  done
  promote mitrafield-voice
}
if [ "${VOICE:-1}" = 0 ]; then
  VOICE_URL=""
elif ! deploy_voice; then
  if exists mitrafield-voice; then echo "WARNING: voice update failed; the previous revision keeps serving"
  else echo "WARNING: voice service not deployed; narration uses Gemini voices"; VOICE_URL=""; fi
fi

echo "== worker (private, one render per instance)"
deploy mitrafield-worker \
  --no-allow-unauthenticated --service-account "$WORKER_SA" \
  --cpu 4 --memory 8Gi --concurrency 1 --timeout 1800 --min-instances 0 --max-instances 6 \
  --set-env-vars "STUDIO_ROLE=worker,GOOGLE_CLOUD_PROJECT=${PROJECT},STUDIO_REGION=${REGION},STUDIO_WORKER_URL=${WORKER_URL},STUDIO_TASKS_SA=${TASKS_SA},STUDIO_CALLERS=${DEPLOY_SA},STUDIO_CAP_DAY_USD=${CAP_DAY_USD:-25},STUDIO_CAP_PROJECT_USD=${CAP_PROJECT_USD:-5}${PROVIDER_ENV},STUDIO_OMNI_URL=${VOICE_URL}" \
  --set-secrets "STUDIO_WATERMARK_KEY=watermark-key:latest${PROVIDER_SECRETS}"   # one flag: a second would replace the first
# Cloud Tasks (as the tasks SA) and the deploy gate may invoke the worker; nobody else.
for sa in "$TASKS_SA" "$DEPLOY_SA"; do
  gcloud run services add-iam-policy-binding mitrafield-worker --project "$PROJECT" --region "$REGION" \
    --member="serviceAccount:$sa" --role=roles/run.invoker >/dev/null
done

echo "== gate: worker selftest (Firestore round trip + a real model call from the worker)"
# Always act as the deploy service account (a user account cannot mint a token for a custom audience, and the
# worker checks the caller's email, which only --include-email puts in the token).
TOKEN="$(gcloud auth print-identity-token --impersonate-service-account="$DEPLOY_SA" --audiences="$WORKER_URL" --include-email)"
retry bash -c "curl -fsS -H 'Authorization: Bearer $TOKEN' '$(canary_url mitrafield-worker)/internal/selftest' | tee /dev/stderr | grep -q '\"firestore\":\"ok\".*\"watermark\":\"ok\"'" \
  || { echo "worker selftest FAILED; previous revision keeps serving"; exit 1; }
promote mitrafield-worker

echo "== api (public, stateless)"
deploy mitrafield-api \
  --allow-unauthenticated --service-account "$API_SA" \
  --cpu 1 --memory 2Gi --concurrency 40 --timeout 300 --min-instances 0 --max-instances 5 \
  --set-env-vars "STUDIO_ROLE=api,GOOGLE_CLOUD_PROJECT=${PROJECT},STUDIO_REGION=${REGION},STUDIO_WORKER_URL=${WORKER_URL},STUDIO_TASKS_SA=${TASKS_SA},STUDIO_CORS=${STUDIO_CORS:-${API_URL}},STUDIO_OMNI_URL=${VOICE_URL}" \
  --set-secrets STUDIO_PASSCODE=studio-passcode:latest
echo "== gate: api readiness and metadata"
U="$(canary_url mitrafield-api)"
retry bash -c "curl -fsS '$U/readyz' | grep -q '\"ok\":true'" || { echo "api /readyz FAILED"; exit 1; }
retry bash -c "curl -fsS '$U/api/meta' | grep -q looks" || { echo "api /api/meta FAILED"; exit 1; }
promote mitrafield-api

echo "== live"
echo "api    : $(gcloud run services describe mitrafield-api --region "$REGION" --project "$PROJECT" --format='value(status.url)')"
echo "worker : $WORKER_URL (private)"

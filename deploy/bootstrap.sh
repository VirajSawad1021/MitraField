#!/usr/bin/env bash
# One-time, idempotent infrastructure for MitraField. Safe to re-run.
#
#   PROJECT=mitrafield-aibc26 GITHUB_REPO=owner/repo BILLING_ACCOUNT=... ./deploy/bootstrap.sh
#
# Creates: APIs, Firestore, Cloud Storage bucket, Artifact Registry, Cloud Tasks queue, three service
# accounts with least privilege, Secret Manager entry for the passcode, a budget alert, and the
# Workload Identity Federation trust that lets GitHub Actions deploy without any stored key.
set -euo pipefail

PROJECT="${PROJECT:?set PROJECT}"
REGION="${REGION:-asia-southeast1}"
GITHUB_REPO="${GITHUB_REPO:?set GITHUB_REPO as owner/name}"
BUCKET="${BUCKET:-${PROJECT}-mitrafield-data}"
REPO="${REPO:-mitrafield}"
QUEUE="${QUEUE:-mitrafield-render}"
BUDGET_USD="${BUDGET_USD:-50}"
SA_DOMAIN="${PROJECT}.iam.gserviceaccount.com"
API_SA="mitrafield-api@${SA_DOMAIN}"          # public service: reads state, enqueues jobs. Cannot render, cannot call models.
WORKER_SA="mitrafield-worker@${SA_DOMAIN}"
VOICE_SA="mitrafield-voice@${SA_DOMAIN}"      # private GPU service (OmniVoice): stateless, no data access.
TASKS_SA="mitrafield-tasks@${SA_DOMAIN}"      # identity Cloud Tasks presents to the worker. May only invoke it.
DEPLOY_SA="mitrafield-deploy@${SA_DOMAIN}"    # identity GitHub Actions assumes.
cd "$(dirname "$0")/.."

gcloud config set project "$PROJECT" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"

if [ -n "${BILLING_ACCOUNT:-}" ]; then
  echo "== billing"
  gcloud billing projects link "$PROJECT" --billing-account="$BILLING_ACCOUNT" >/dev/null
fi
gcloud billing projects describe "$PROJECT" --format='value(billingEnabled)' | grep -qi true \
  || { echo "Billing is not enabled on $PROJECT. Link it (BILLING_ACCOUNT=...) and re-run."; exit 1; }

echo "== APIs"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com cloudtasks.googleapis.com aiplatform.googleapis.com secretmanager.googleapis.com \
  storage.googleapis.com iamcredentials.googleapis.com sts.googleapis.com firebasehosting.googleapis.com \
  billingbudgets.googleapis.com logging.googleapis.com monitoring.googleapis.com

echo "== Firestore (native mode, $REGION)"
gcloud firestore databases describe --database='(default)' >/dev/null 2>&1 \
  || gcloud firestore databases create --database='(default)' --location="$REGION" --type=firestore-native

echo "== bucket gs://$BUCKET (media; uniform access, no public reads)"
gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://$BUCKET" --location="$REGION" --uniform-bucket-level-access --public-access-prevention

echo "== Artifact Registry"
gcloud artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1 \
  || gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION"

echo "== Cloud Tasks queue $QUEUE"
# maxConcurrentDispatches caps parallel renders (and so Gemini/Veo quota and spend); retries back off.
QFLAGS=(--max-concurrent-dispatches=6 --max-dispatches-per-second=3 --max-attempts=3 --min-backoff=20s --max-backoff=300s --max-doublings=3)
gcloud tasks queues describe "$QUEUE" --location="$REGION" >/dev/null 2>&1 \
  && gcloud tasks queues update "$QUEUE" --location="$REGION" "${QFLAGS[@]}" >/dev/null \
  || gcloud tasks queues create "$QUEUE" --location="$REGION" "${QFLAGS[@]}"

echo "== service accounts"
for sa in api worker tasks voice deploy; do
  gcloud iam service-accounts describe "mitrafield-$sa@${SA_DOMAIN}" >/dev/null 2>&1 \
    || gcloud iam service-accounts create "mitrafield-$sa" --display-name="MitraField $sa"
done
bind() { gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$1" --role="$2" --condition=None >/dev/null; }
# api: read/write project documents, enqueue jobs, read media. No model access.
bind "$API_SA" roles/datastore.user
bind "$API_SA" roles/cloudtasks.enqueuer
bind "$API_SA" roles/logging.logWriter
# worker: renders. Firestore + media + the Gemini key. Nothing else.
bind "$WORKER_SA" roles/datastore.user
bind "$WORKER_SA" roles/aiplatform.user
bind "$WORKER_SA" roles/cloudtasks.enqueuer
bind "$WORKER_SA" roles/logging.logWriter
# voice: OmniVoice on a GPU. Stateless, holds no data, reads nothing; it only needs to write logs.
bind "$VOICE_SA" roles/logging.logWriter
for sa in "$API_SA" "$WORKER_SA"; do
  gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$sa" --role=roles/storage.objectAdmin >/dev/null
done
# Cloud Tasks signs jobs as the tasks SA; the enqueuers must be allowed to attach that identity.
for sa in "$API_SA" "$WORKER_SA"; do
  gcloud iam service-accounts add-iam-policy-binding "$TASKS_SA" --member="serviceAccount:$sa" --role=roles/iam.serviceAccountUser >/dev/null
done
# deploy: build, deploy, run the Firebase hosting release. No access to data or models.
for r in roles/run.admin roles/cloudbuild.builds.editor roles/artifactregistry.writer roles/firebasehosting.admin \
         roles/serviceusage.serviceUsageConsumer roles/storage.admin; do bind "$DEPLOY_SA" "$r"; done
for sa in "$API_SA" "$WORKER_SA" "$VOICE_SA"; do
  gcloud iam service-accounts add-iam-policy-binding "$sa" --member="serviceAccount:$DEPLOY_SA" --role=roles/iam.serviceAccountUser >/dev/null
done
# The deploy gate mints an identity token for the worker (impersonating itself), and Cloud Build runs as the
# default compute SA, which the deploy identity must be allowed to act as.
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --member="serviceAccount:$DEPLOY_SA" --role=roles/iam.serviceAccountTokenCreator >/dev/null
ME="$(gcloud config get-value account 2>/dev/null)"   # whoever bootstraps (or deploys by hand) may mint the gate's token
case "$ME" in *iam.gserviceaccount.com) ;; ?*) gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --member="user:$ME" --role=roles/iam.serviceAccountTokenCreator >/dev/null ;; esac
gcloud iam service-accounts add-iam-policy-binding "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --member="serviceAccount:$DEPLOY_SA" --role=roles/iam.serviceAccountUser >/dev/null
# Cloud Build runs as the default compute SA: let it push images.
bind "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" roles/artifactregistry.writer
bind "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" roles/logging.logWriter
bind "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" roles/storage.objectViewer

echo "== passcode secret"
gcloud secrets describe studio-passcode >/dev/null 2>&1 || gcloud secrets create studio-passcode --replication-policy=automatic
if [ -n "${STUDIO_PASSCODE:-}" ]; then printf '%s' "$STUDIO_PASSCODE" | gcloud secrets versions add studio-passcode --data-file=- >/dev/null; fi
gcloud secrets versions list studio-passcode --limit=1 --format='value(name)' | grep -q . \
  || { echo "No passcode stored. Re-run with STUDIO_PASSCODE=... (the public link needs it)."; exit 1; }
gcloud secrets add-iam-policy-binding studio-passcode --member="serviceAccount:$API_SA" --role=roles/secretmanager.secretAccessor >/dev/null

echo "== Gemini API key secret (worker only)"
gcloud secrets describe gemini-api-key >/dev/null 2>&1 || gcloud secrets create gemini-api-key --replication-policy=automatic
if [ -n "${GEMINI_API_KEY:-}" ]; then printf '%s' "$GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=- >/dev/null; fi
gcloud secrets versions list gemini-api-key --limit=1 --format='value(name)' | grep -q . \
  || echo "No Gemini API key stored; re-run with GEMINI_API_KEY=... (not needed with STUDIO_VERTEX=1)."
gcloud secrets add-iam-policy-binding gemini-api-key --member="serviceAccount:$WORKER_SA" --role=roles/secretmanager.secretAccessor >/dev/null

echo "== watermark key secret (worker only; losing it makes older exports unverifiable, so never delete versions)"
gcloud secrets describe watermark-key >/dev/null 2>&1 || gcloud secrets create watermark-key --replication-policy=automatic
gcloud secrets versions list watermark-key --limit=1 --format='value(name)' | grep -q . \
  || { openssl rand -hex 32 | tr -d '\n' | gcloud secrets versions add watermark-key --data-file=- >/dev/null; }
gcloud secrets add-iam-policy-binding watermark-key --member="serviceAccount:$WORKER_SA" --role=roles/secretmanager.secretAccessor >/dev/null

echo "== delete unfinished Verify uploads after a day"
LC="$(mktemp)"; printf '{"rule":[{"action":{"type":"Delete"},"condition":{"age":1,"matchesPrefix":["projects/verify/"]}}]}' > "$LC"
gcloud storage buckets update "gs://$BUCKET" --lifecycle-file="$LC" >/dev/null; rm -f "$LC"

echo "== Workload Identity Federation for $GITHUB_REPO"
gcloud iam workload-identity-pools describe github --location=global >/dev/null 2>&1 \
  || gcloud iam workload-identity-pools create github --location=global --display-name="GitHub Actions"
gcloud iam workload-identity-pools providers describe github --location=global --workload-identity-pool=github >/dev/null 2>&1 \
  || gcloud iam workload-identity-pools providers create-oidc github --location=global --workload-identity-pool=github \
       --issuer-uri="https://token.actions.githubusercontent.com" \
       --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
       --attribute-condition="assertion.repository=='${GITHUB_REPO}'"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/${GITHUB_REPO}" >/dev/null

if [ -n "${BILLING_ACCOUNT:-}" ]; then
  echo "== budget alert (\$$BUDGET_USD)"
  gcloud billing budgets list --billing-account="$BILLING_ACCOUNT" --filter="displayName=mitrafield" --format='value(name)' | grep -q . \
    || gcloud billing budgets create --billing-account="$BILLING_ACCOUNT" --display-name=mitrafield \
         --filter-projects="projects/${PROJECT_NUMBER}" --budget-amount="${BUDGET_USD}USD" \
         --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
fi

cat <<EOF

== done
WIF provider : projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/providers/github
Deploy SA    : ${DEPLOY_SA}
Next         : ./deploy/deploy.sh   (first deploy from this machine), then every push to main deploys via GitHub Actions.
EOF

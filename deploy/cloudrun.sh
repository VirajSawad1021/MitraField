#!/usr/bin/env bash
# Deploy MitraField to Cloud Run (one service: API + render workers + web app).
#
#   PROJECT=my-gcp-project ./deploy/cloudrun.sh
#
# Needs: gcloud logged in (gcloud auth login), billing enabled on the project,
# GEMINI_API_KEY in .env (stored in Secret Manager, never in the image) and a
# STUDIO_PASSCODE for the public demo (writes need it; browsing does not).
set -euo pipefail

PROJECT="${PROJECT:?set PROJECT to your Google Cloud project id}"
REGION="${REGION:-asia-southeast1}"           # Singapore
SERVICE="${SERVICE:-mitrafield}"
BUCKET="${BUCKET:-${PROJECT}-mitrafield-data}"
REPO="${REPO:-mitrafield}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:$(git rev-parse --short HEAD)"
cd "$(dirname "$0")/.."

KEY="$(grep -E '^GEMINI_API_KEY=' .env | cut -d= -f2-)"
PASSCODE="${STUDIO_PASSCODE:-$(grep -E '^STUDIO_PASSCODE=' .env | cut -d= -f2- || true)}"
[ -n "$KEY" ] || { echo "GEMINI_API_KEY missing in .env"; exit 1; }
[ -n "$PASSCODE" ] || { echo "Set STUDIO_PASSCODE (env or .env) so the public link cannot spend credits"; exit 1; }

gcloud config set project "$PROJECT" >/dev/null
echo "== enabling APIs"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  secretmanager.googleapis.com storage.googleapis.com aiplatform.googleapis.com

echo "== bucket for projects and media: gs://$BUCKET"
gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1 || gcloud storage buckets create "gs://$BUCKET" --location="$REGION"

echo "== secrets"
for name in gemini-api-key studio-passcode; do
  gcloud secrets describe "$name" >/dev/null 2>&1 || gcloud secrets create "$name" --replication-policy=automatic
done
printf '%s' "$KEY" | gcloud secrets versions add gemini-api-key --data-file=- >/dev/null
printf '%s' "$PASSCODE" | gcloud secrets versions add studio-passcode --data-file=- >/dev/null

echo "== service account"
SA="${SERVICE}-runner@${PROJECT}.iam.gserviceaccount.com"
gcloud iam service-accounts describe "$SA" >/dev/null 2>&1 || gcloud iam service-accounts create "${SERVICE}-runner" --display-name="MitraField runner"
for role in roles/storage.objectAdmin roles/secretmanager.secretAccessor roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$SA" --role="$role" --condition=None >/dev/null
done

echo "== image (Cloud Build): $IMAGE"
gcloud artifacts repositories describe "$REPO" --location="$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION"
gcloud builds submit --tag "$IMAGE" --machine-type=e2-highcpu-8 --timeout=40m .

echo "== deploy"
# One always-on instance: renders run as background jobs inside the service, and project
# state lives on the Cloud Storage mount, so a single writer keeps it consistent.
gcloud run deploy "$SERVICE" --image "$IMAGE" --region "$REGION" --service-account "$SA" \
  --cpu 4 --memory 8Gi --timeout 3600 --no-cpu-throttling --min-instances 1 --max-instances 1 \
  --execution-environment gen2 --allow-unauthenticated \
  --add-volume name=data,type=cloud-storage,bucket="$BUCKET" --add-volume-mount volume=data,mount-path=/data \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest,STUDIO_PASSCODE=studio-passcode:latest

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo "== live: $URL"

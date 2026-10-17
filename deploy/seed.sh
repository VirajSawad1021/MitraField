#!/usr/bin/env bash
# Copy finished demo projects from this machine into the Cloud Storage bucket so the
# deployed app shows them.  PROJECT=my-gcp-project ./deploy/seed.sh 0846ab6934 a834483018 ...
set -euo pipefail
PROJECT="${PROJECT:?set PROJECT}"
BUCKET="${BUCKET:-${PROJECT}-mitrafield-data}"
cd "$(dirname "$0")/.."
for id in "$@"; do
  # absolute paths in project.json point at this machine; rewrite them to the mount
  tmp="$(mktemp -d)"
  cp -r "data/projects/$id" "$tmp/"
  sed -i "s#$(pwd)/data/projects#/data/projects#g" "$tmp/$id/project.json"
  gcloud storage cp -r "$tmp/$id" "gs://$BUCKET/projects/"
  rm -rf "$tmp"
  echo "seeded $id"
done

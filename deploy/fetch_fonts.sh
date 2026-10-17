#!/usr/bin/env bash
# Noto fonts for non-Latin narration languages (Devanagari, Tamil, Bengali, Thai, CJK).
# Used by the Dockerfile and for local setup:  ./deploy/fetch_fonts.sh ~/.local/share/fonts/noto
set -euo pipefail
DEST="${1:-/usr/share/fonts/truetype/noto-mitrafield}"
mkdir -p "$DEST"
BASE="https://github.com/google/fonts/raw/main/ofl"
for f in "notosansdevanagari/NotoSansDevanagari[wdth,wght].ttf" "notosanstamil/NotoSansTamil[wdth,wght].ttf" \
         "notosansbengali/NotoSansBengali[wdth,wght].ttf" "notosansthai/NotoSansThai[wdth,wght].ttf" \
         "notosansjp/NotoSansJP[wght].ttf" "notosanskr/NotoSansKR[wght].ttf" "notosanssc/NotoSansSC[wght].ttf"; do
  name="$(basename "$f" | sed 's/\[.*\]//')"
  [ -s "$DEST/$name" ] || curl -fsSL -o "$DEST/$name" "$BASE/$(printf '%s' "$f" | sed 's/\[/%5B/; s/\]/%5D/')"
done
fc-cache -f "$DEST" >/dev/null 2>&1 || true
ls "$DEST"

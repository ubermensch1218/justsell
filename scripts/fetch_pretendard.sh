#!/usr/bin/env bash
set -euo pipefail

# Downloads Pretendard TTFs into assets/fonts/ (local dev convenience).
# License: Pretendard is distributed under SIL OFL 1.1.

VERSION="${PRETENDARD_VERSION:-1.3.9}"
ZIP_URL="https://github.com/orioncactus/pretendard/releases/download/v${VERSION}/Pretendard-${VERSION}.zip"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/assets/fonts"
TMP_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

mkdir -p "$OUT_DIR"

echo "Downloading Pretendard v${VERSION}..."
curl -fsSL "$ZIP_URL" -o "$TMP_DIR/pretendard.zip"

echo "Extracting TTFs..."
unzip -q "$TMP_DIR/pretendard.zip" -d "$TMP_DIR/unzipped"

pick_one() {
  local name="$1"
  local found
  found="$(find "$TMP_DIR/unzipped" -type f -name "$name" | head -n 1 || true)"
  if [[ -z "$found" ]]; then
    echo "Missing in zip: $name" >&2
    exit 1
  fi
  cp -f "$found" "$OUT_DIR/$name"
}

pick_one "Pretendard-Regular.ttf"
pick_one "Pretendard-Medium.ttf"
pick_one "Pretendard-SemiBold.ttf"
pick_one "Pretendard-Bold.ttf"

echo "Done:"
ls -1 "$OUT_DIR"/Pretendard-*.ttf


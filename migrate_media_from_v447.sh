#!/usr/bin/env bash
set -euo pipefail
OLD="${1:-/opt/liftorg/liftorg_b2b_4.4.7_buyer_visibility}"
NEW="${2:-$(cd "$(dirname "$0")" && pwd)}"
mkdir -p "$NEW/media-library" "$NEW/winches"
if [ -d "$OLD/app/static/media-library" ]; then
  cp -a "$OLD/app/static/media-library/." "$NEW/media-library/"
fi
if [ -d "$OLD/app/static/winches" ]; then
  cp -a "$OLD/app/static/winches/." "$NEW/winches/"
fi
printf 'media-library files: '; find "$NEW/media-library" -type f ! -name .keep | wc -l
printf 'winches files: '; find "$NEW/winches" -type f ! -name .keep | wc -l

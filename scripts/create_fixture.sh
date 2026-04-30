#!/usr/bin/env bash
# Cut a 5-minute 720p test fixture from a DJI tennis recording.
# Usage: ./scripts/create_fixture.sh [source_video]
set -euo pipefail

SOURCE="${1:-$HOME/Movies/DJI Action 5pro/Tennis/DJI_20260117213735_0135_D.MP4}"
OUTPUT="tests/fixtures/sample_tennis.mp4"

mkdir -p "$(dirname "$OUTPUT")"

ffmpeg -i "$SOURCE" \
  -ss 30 -t 300 \
  -vf scale=1280:720 \
  -c:v libx264 -crf 28 -preset fast \
  -an \
  -y "$OUTPUT"

echo "Fixture written to $OUTPUT ($(du -sh "$OUTPUT" | cut -f1))"

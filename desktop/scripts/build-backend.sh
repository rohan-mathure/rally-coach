#!/usr/bin/env bash
# Build the Python backend into a single binary for bundling in the Electron app.
# Output: ../dist-server/rally-coach-server  (macOS/Linux)
#         ../dist-server/rally-coach-server.exe  (Windows)
#
# Prerequisites:
#   pip install pyinstaller
#   All Python dependencies installed (pip install -e ..)
#
# Run from the desktop/ directory:
#   bash scripts/build-backend.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$REPO_ROOT/dist-server"

echo "==> Building Rally Coach server binary"
echo "    Repo root : $REPO_ROOT"
echo "    Output    : $OUT_DIR"

cd "$REPO_ROOT"

# Ensure PyInstaller is available
if ! python3 -c "import PyInstaller" 2>/dev/null; then
  echo "Installing PyInstaller..."
  pip install pyinstaller
fi

mkdir -p "$OUT_DIR"

pyinstaller \
  --noconfirm \
  --onefile \
  --name "rally-coach-server" \
  --distpath "$OUT_DIR" \
  --workpath "$REPO_ROOT/build/pyinstaller" \
  --specpath "$REPO_ROOT/build" \
  --hidden-import "uvicorn.logging" \
  --hidden-import "uvicorn.loops" \
  --hidden-import "uvicorn.loops.auto" \
  --hidden-import "uvicorn.protocols" \
  --hidden-import "uvicorn.protocols.http" \
  --hidden-import "uvicorn.protocols.http.auto" \
  --hidden-import "uvicorn.protocols.websockets" \
  --hidden-import "uvicorn.protocols.websockets.auto" \
  --hidden-import "uvicorn.lifespan" \
  --hidden-import "uvicorn.lifespan.on" \
  --hidden-import "aiosqlite" \
  --hidden-import "fastapi" \
  --hidden-import "app.main" \
  --hidden-import "app.routers.upload" \
  --hidden-import "app.routers.sessions" \
  --hidden-import "app.routers.shots" \
  --hidden-import "app.routers.video" \
  --hidden-import "pipeline.runner" \
  --hidden-import "ultralytics" \
  --hidden-import "cv2" \
  --hidden-import "mediapipe" \
  --hidden-import "filterpy" \
  --collect-all "ultralytics" \
  --collect-all "mediapipe" \
  --collect-all "cv2" \
  --add-data "app:app" \
  --add-data "pipeline:pipeline" \
  server.py

echo ""
echo "==> Build complete: $OUT_DIR/rally-coach-server"
echo ""
echo "Next steps:"
echo "  cd desktop && npm run package"

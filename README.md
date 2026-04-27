# Rally Coach

Analyze tennis sessions from iPhone video. Upload a match recording and get back an annotated video plus a web dashboard with shot-by-shot stats.

## What it does

- **Ball tracking** — follows the ball across every frame using YOLOv8 + Kalman filtering
- **Court detection** — auto-detects court lines and computes a pixel↔feet homography
- **In/Out** — maps bounce points to real court coordinates and classifies each as in, out, or close call
- **Net clearance** — measures ball height at net crossing in inches
- **Shot classification** — forehand, backhand, volley, overhead (via MediaPipe pose)
- **Spin classification** — topspin, underspin, flat (trajectory curvature analysis)
- **Ball speed** — mph as ball leaves the racquet
- **RPM estimate** — rotational spin derived from Magnus effect trajectory deviation
- **Quality score** — composite 0–100 per shot (in-bounds, net clearance, landing depth, speed)
- **Annotated video** — output MP4 with ball trail, bounce dots, HUD overlay
- **Web dashboard** — charts, 2D court map, sortable shot table, CSV export

## Requirements

- Python 3.11+
- ffmpeg (for H.264 re-encoding) — `brew install ffmpeg`
- iPhone footage at 60fps works best; 30fps is supported but speed/RPM accuracy degrades

## Setup

```bash
git clone <repo>
cd rally-coach

# Install dependencies
pip install -e .
# or with uv:
uv pip install -e .

# Copy env config
cp .env.example .env

# Start server
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Usage

1. Drop a video file on the upload page
2. Processing runs in the background (takes ~2–5× video duration on CPU, faster on Apple Silicon GPU)
3. When status shows **complete**, click **View** to open the session dashboard
4. Click any row in the shot table to seek the video to that shot
5. Use the court map filters to isolate shot types
6. Export shot data as CSV for external analysis

## Model weights

By default the ball detector uses YOLOv8n's COCO "sports ball" class (class 32), which works but misses fast balls. For better accuracy, drop a fine-tuned model at:

```
weights/yolov8n_tennis_ball.pt
```

The pipeline auto-detects it on startup.

## Court detection fallback

If auto-detection fails (non-standard court color, heavy shadows), a manual calibration endpoint is available:

```
POST /api/sessions/{session_id}/calibrate
Body: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
```

Pass the 4 pixel coordinates of the court corners (near-left, near-right, far-right, far-left baseline corners).

## Accuracy notes

| Metric | Accuracy at 60fps |
|---|---|
| Ball detection | ~70% with COCO weights; ~90%+ with fine-tuned weights |
| Speed | ±10–15% when court homography is valid |
| RPM | ±15–25%; directional only below 50mph |
| Spin type | Reliable above 30mph; "unknown" returned below |
| In/Out | Dependent on homography quality; close calls flagged within 6 inches |

## License

MIT

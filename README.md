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

## How to create `weights/yolov8n_tennis_ball.pt`

Fine-tuning takes ~30–60 minutes on a GPU (M-series Mac works fine). Steps:

### 1. Get a labeled dataset

**Option A — use a public dataset (fastest)**

The [Roboflow Tennis Ball Detection](https://universe.roboflow.com/roboflow-100/tennis-ball-detection-6cbzr) dataset has ~9k labeled images and exports directly to YOLOv8 format.

```bash
pip install roboflow
```

```python
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_KEY")   # free account at roboflow.com
project = rf.workspace("roboflow-100").project("tennis-ball-detection-6cbzr")
dataset = project.version(4).download("yolov8")
```

This creates a folder like `tennis-ball-detection-6cbzr-4/` with `data.yaml`, `train/`, `valid/`, `test/`.

**Option B — label your own footage (better domain match)**

1. Process a few of your own videos through Rally Coach first (COCO weights are good enough to generate a starting point)
2. Extract frames where the ball was missed (`is_interpolated=True` and `confidence=0`):

```python
import cv2, json, sqlite3

conn = sqlite3.connect("storage/sessions.db")
shots = conn.execute("SELECT trajectory FROM shots").fetchall()

cap = cv2.VideoCapture("storage/uploads/YOUR_SESSION_ID.mp4")
for row in shots:
    traj = json.loads(row[0])
    for pos in traj:
        if pos["confidence"] == 0 and pos["is_interpolated"]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos["frame_idx"])
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(f"labeling/frame_{pos['frame_idx']}.jpg", frame)
```

3. Label with [Label Studio](https://labelstud.io/) (free) or upload to Roboflow for annotation. Draw bounding boxes around the ball. Label class name: `tennis_ball`.
4. Export in **YOLOv8 format** — produces the same `data.yaml` + image/label folder structure.

Aim for at least **500 labeled frames** covering: fast serves, slow rallies, different court colors, partial occlusion.

### 2. Fine-tune YOLOv8n

```bash
pip install ultralytics

yolo detect train \
  data=tennis-ball-detection-6cbzr-4/data.yaml \
  model=yolov8n.pt \
  epochs=50 \
  imgsz=640 \
  batch=16 \
  name=tennis_ball_v1 \
  patience=10
```

On Apple Silicon (MPS):
```bash
yolo detect train data=... model=yolov8n.pt epochs=50 imgsz=640 device=mps
```

Training output lands in `runs/detect/tennis_ball_v1/weights/`. The best checkpoint is `best.pt`.

### 3. Validate before deploying

```bash
yolo detect val \
  data=tennis-ball-detection-6cbzr-4/data.yaml \
  model=runs/detect/tennis_ball_v1/weights/best.pt

# Quick visual check on a sample video
yolo detect predict \
  model=runs/detect/tennis_ball_v1/weights/best.pt \
  source=storage/uploads/YOUR_VIDEO.mp4 \
  conf=0.35 \
  save=True
```

Target metrics: **mAP50 > 0.80**, **recall > 0.85**. If recall is low the tracker will have too many gaps. Increase epochs or add more training data.

### 4. Deploy

```bash
cp runs/detect/tennis_ball_v1/weights/best.pt weights/yolov8n_tennis_ball.pt
```

Rally Coach picks it up automatically on the next run — no config change needed.

### Troubleshooting

| Problem | Fix |
|---|---|
| `data.yaml` class name doesn't match | Edit `data.yaml`: set `names: [tennis_ball]` and confirm class index 0 |
| mAP plateaus below 0.70 | Add more varied training data; ensure labels are tight bounding boxes (not loose) |
| Model detects court lines as balls | Add hard negative examples: frames with no ball, label them empty |
| Fast serves still missed | Add labeled frames from serve sequences specifically; increase `imgsz` to 1280 |
| COCO class 32 was used during detection instead of class 0 | The pipeline checks for the custom weights file — confirm it exists at `weights/yolov8n_tennis_ball.pt` |

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

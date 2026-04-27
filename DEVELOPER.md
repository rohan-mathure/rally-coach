# Developer Guide

## Project structure

```
rally-coach/
├── app/                    # FastAPI web application
│   ├── main.py             # App factory, lifespan, router mounts, static files
│   ├── config.py           # Settings (pydantic BaseSettings, reads .env)
│   ├── database.py         # aiosqlite setup, table creation, get_db()
│   ├── routers/            # One file per resource
│   │   ├── upload.py       # POST /api/sessions — file upload, kicks off pipeline
│   │   ├── sessions.py     # GET /api/sessions, GET /api/sessions/{id}, POST /api/sessions/{id}/calibrate
│   │   ├── shots.py        # GET /api/sessions/{id}/shots, GET .../shots/csv
│   │   └── video.py        # GET /api/sessions/{id}/video — serves annotated MP4
│   ├── models/
│   │   ├── session.py      # Session pydantic model
│   │   └── shot.py         # Shot, BallPosition, BounceEvent, PoseLandmarks models
│   └── static/             # Served at /static/
│       ├── index.html      # Upload page + sessions list
│       ├── session.html    # Per-session dashboard
│       ├── css/style.css
│       └── js/
│           ├── upload.js       # XHR upload with progress, session polling
│           ├── session.js      # KPIs, Chart.js charts, shot table, CSV export
│           └── court_viz.js    # Canvas 2D court map (CourtViz class)
│
├── pipeline/               # All CV processing — no HTTP concerns
│   ├── runner.py           # Orchestrates all 13 stages; called by upload.py BackgroundTask
│   ├── stages/             # One file per pipeline stage
│   │   ├── frame_extractor.py      # Stage 1
│   │   ├── court_detector.py       # Stage 2
│   │   ├── ball_tracker.py         # Stage 3
│   │   ├── bounce_detector.py      # Stage 4
│   │   ├── shot_segmenter.py       # Stage 5
│   │   ├── pose_analyzer.py        # Stage 6
│   │   ├── shot_classifier.py      # Stage 7
│   │   ├── spin_analyzer.py        # Stage 8
│   │   ├── speed_estimator.py      # Stage 9
│   │   ├── net_clearance.py        # Stage 10
│   │   ├── inout_classifier.py     # Stage 11
│   │   ├── shot_quality.py         # Stage 12
│   │   └── annotator.py            # Stage 13
│   ├── models/
│   │   ├── kalman.py       # KalmanBallTracker — wraps filterpy KalmanFilter
│   │   └── homography.py   # CourtHomography — pixel↔court_feet transform via cv2.perspectiveTransform
│   └── utils/
│       ├── court_constants.py  # ITF court dimensions, SINGLES_BOUNDS polygon, CLOSE_CALL_THRESHOLD_FT
│       ├── geometry.py         # point_in_polygon, line_intersection, min_distance_to_polygon_boundary
│       └── video_io.py         # VideoReader — thin cv2.VideoCapture wrapper with seek
│
├── weights/                # Model weights (gitignored except .gitkeep)
├── storage/                # Runtime data (gitignored)
│   ├── uploads/            # Raw uploaded videos
│   ├── processed/          # Annotated output MP4s
│   └── sessions.db         # SQLite database
└── tests/
    ├── test_geometry.py
    ├── test_kalman.py
    └── fixtures/           # Short test video clips (gitignored)
```

## Dev setup

```bash
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Run tests:
```bash
pytest tests/ -v
```

## Pipeline architecture

The pipeline is a linear sequence of pure functions. Each stage takes a list/object, returns a new list/object — no in-place mutation. `runner.py` is the only place that calls DB and filesystem I/O between stages.

### Stage execution order

```
Stage 1  extract_metadata()         → fps, width, height, total_frames
Stage 2  detect_court()             → CourtHomography | None
Stage 3  track_balls()              → list[BallPosition]
Stage 4  detect_bounces()           → list[BounceEvent]
Stage 5  segment_shots()            → list[Shot]
Stage 9  estimate_speeds()          → list[Shot]   ← speed before spin (spin needs speed)
Stage 8  analyze_spin()             → list[Shot]
Stage 10 compute_net_clearance()    → list[Shot]
Stage 11 classify_inout()           → list[Shot]
Stage 6  extract_poses()            → list[Shot]
Stage 7  classify_shots()           → list[Shot]
Stage 12 compute_quality_scores()   → list[Shot]
Stage 13 annotate_video()           → MP4 on disk
```

### Coordinate systems

Two coordinate systems are used:

| Name | Unit | Origin | Notes |
|---|---|---|---|
| Pixel | px | Top-left of frame | y increases downward |
| Court | feet | Near baseline center | y increases toward far baseline (0–78ft) |

`CourtHomography.pixel_to_court(px, py)` and `.court_to_pixel(cx, cy)` convert between them. The homography is a 3×3 perspective transform matrix computed by `cv2.findHomography` from 4 detected court corners.

### Ball tracking

`KalmanBallTracker` state vector: `[x, y, vx, vy]` (pixel coordinates). Constant-velocity model. When YOLOv8 returns no detection, the tracker runs a predict-only step. Gaps ≤8 frames are filled with Kalman predictions and marked `is_interpolated=True`. Speed and spin are not computed on shots with `detection_gap_frames > 8`.

### Court detection

`detect_court()` runs once on frame 30. Algorithm:
1. Canny edge → `HoughLinesP`
2. Cluster lines into horizontal (baselines/net/service) and vertical (sidelines) by angle
3. Deduplicate nearby lines by midpoint distance
4. Select outermost horizontal and vertical candidates
5. Compute 4 corner intersections
6. `cv2.findHomography(corners_px, itf_feet_corners, RANSAC)`

If `inlier_ratio < 0.6`, homography is set to `None` and all downstream steps that require it gracefully degrade (speed/RPM become unavailable, in/out falls back to rough frame-position heuristic).

Manual override: `POST /api/sessions/{id}/calibrate` with 4 pixel corner coordinates recomputes H and stores it to the session.

### Spin and RPM estimation

Spin type is determined by fitting a degree-2 polynomial to `(t, y_pixel)` and measuring the mean vertical residual normalized by trajectory length:

```
curvature_score = mean(y_actual - y_parabola) / trajectory_length
topspin   if score < -0.15
underspin if score > +0.15
flat      otherwise
```

RPM is derived from the Magnus effect:
```
F_magnus ≈ C_L × ρ × π × r² × v × ω
ω = F_magnus / (C_L × ρ × π × r² × v)
rpm = ω × 60 / 2π
```

Where `F_magnus` is approximated from the trajectory curvature residual × ball mass. Accuracy: ±15–25%. Only computed when `speed_mph > 30`.

### Quality score

```python
quality = 40 * is_in + 25 * cleared_net + 25 * depth_score + 10 * norm_speed
```

`depth_score`: 1.0 if bounce lands in far 25% of opponent's half, 0.5× partial credit in opponent's near half, 0.0 otherwise.

`norm_speed`: `min(1.0, shot_speed / session_avg_speed)`.

## Database schema

Two tables. All shot fields are nullable — stages set them to `None` if they cannot compute reliably.

### `sessions`
| Column | Type | Notes |
|---|---|---|
| session_id | TEXT PK | uuid4 |
| filename | TEXT | Original upload filename |
| uploaded_at | TEXT | ISO datetime |
| status | TEXT | queued / processing / complete / error |
| fps, total_frames, width, height | REAL/INT | Set after Stage 1 |
| total_shots, avg_speed_mph, avg_quality_score | INT/REAL | Set after Stage 12 |
| homography_matrix | TEXT | JSON 3×3 float array; NULL if detection failed |
| processed_video_path | TEXT | Absolute path to output MP4 |

### `shots`
One row per detected shot. Key fields: `shot_type`, `spin_type`, `speed_mph`, `rpm_estimate`, `net_clearance_inches`, `cleared_net`, `is_in`, `is_close_call`, `quality_score`.

`trajectory`, `pose`, and `bounce` are stored as JSON blobs.

`pipeline_warnings` is a JSON string array — values: `long_detection_gap`, `pose_low_conf`, `court_not_detected`.

## Adding a new pipeline stage

1. Create `pipeline/stages/my_stage.py` with a pure function signature:
   ```python
   def my_stage(shots: list[Shot], ...) -> list[Shot]:
       ...
   ```
2. Add the call in `pipeline/runner.py` in the correct position
3. Any new fields on `Shot` go in `app/models/shot.py` (pydantic) and `app/database.py` (SQL column)

## Improving ball detection

The default COCO "sports ball" weights miss fast balls and small balls at distance. To improve:

1. Extract frames where detection failed (confidence = 0, `is_interpolated=True`)
2. Label them with [Label Studio](https://labelstud.io/) or Roboflow
3. Fine-tune YOLOv8n:
   ```bash
   yolo detect train data=tennis_ball.yaml model=yolov8n.pt epochs=50 imgsz=640
   ```
4. Copy the best weights to `weights/yolov8n_tennis_ball.pt`

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `STORAGE_DIR` | `./storage` | Root for uploads, processed, DB |
| `WEIGHTS_DIR` | `./weights` | Model weight files |
| `HOST` | `127.0.0.1` | uvicorn bind host |
| `PORT` | `8000` | uvicorn port |
| `LOG_LEVEL` | `info` | loguru log level |

## Key dependencies

| Package | Purpose |
|---|---|
| `ultralytics` | YOLOv8 ball detection |
| `filterpy` | Kalman filter |
| `mediapipe` | BlazePose for shot classification |
| `opencv-python` | Video I/O, Hough lines, homography, drawing |
| `scipy` | Savitzky-Golay smoothing, signal processing |
| `numpy` | All numerical computation |
| `fastapi` + `uvicorn` | Async web server |
| `aiosqlite` | Async SQLite |
| `pydantic` | Data models and validation |
| `ffmpeg-python` | H.264 re-encode for browser playback |
| `loguru` | Structured logging |

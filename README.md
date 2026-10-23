# AI Weapon Detection & Threat Classification System

An advanced, real-time Computer Vision security system powered by **YOLO11s**, **PyTorch**, **OpenCV**, and **FastAPI**, with a cyberpunk-styled responsive dashboard for live webcam analysis, image scanning, and automated video surveillance.

---

## 📌 Key Capabilities

- **Real-Time Weapon Detection**: Handguns, pistols, revolvers, knives, machetes, and bladed threats detected with sub-30ms latency on GPU and ~80ms on CPU.
- **Physical vs. Printed-Depiction Analysis**: Filters out flat 2D weapon illustrations printed on t-shirts, posters, or stickers to eliminate false alarms without suppressing real weapons.
- **Toy vs. Real Weapon Classification**: Distinguishes real firearms/knives from toy replicas, nerf blasters, and water guns based on colorimetry (safety blaze orange tips) and trained feature margins.
- **Strict Threat Categorization**:
  - `REAL_WEAPON`: Confirmed physical firearm or knife (HIGH threat alert).
  - `TOY_WEAPON`: Toy gun or replica (LOW threat advisory).
  - `NO_WEAPON`: Weapon-free frame or flat printed depiction filtered out.
  - `UNCERTAIN`: Borderline confidence or ambiguous silhouette requiring human verification.
- **Full Video Upload & Analysis**: Ingests `.mp4`, `.avi`, `.mov`, `.mkv`, and `.webm` surveillance footage, analyzes frames, overlays bounding boxes and HUD diagnostics, and exports a downloadable annotated video with interactive jump-to-timestamp navigation.
- **Live Camera Studio**: Real-time snapshot capture and multi-threat confidence meters.

---

## 🔬 Model Verification & Checkpoint Provenance

The system uses a two-phase trained YOLO11s checkpoint:
1. **Phase 1 Baseline Training (`weapon_yolo11s-2`)**:
   - Architecture: Ultralytics YOLO11s (9.42M parameters, 21.4 GFLOPs)
   - Dataset: 3,385 train, 725 val, 727 test images (Sohas knives + Armas firearms + background negatives)
   - Duration: 100 epochs with AdamW optimizer, cosine learning rate scheduling, and mosaic augmentation.
   - Result: Reached peak mAP@50 of **88.1%** and mAP@50-95 of **61.2%** at epoch 79.
2. **Phase 2 Fine-Tuning (`weapon_yolo11s_toy_finetune`)**:
   - Initial Weights: Resumed from `weapon_yolo11s-2/weights/best.pt`
   - Dataset: Augmented with Roboflow toy firearm dataset (expanded toy weapon samples from 217 to 907; 4,072 total training images)
   - Duration: 25 epochs at reduced learning rate (`lr0=0.0002`).
   - Result: Elevated overall mAP@50 to **90.84%** and mAP@50-95 to **67.31%**.
   - Test Split Benchmark (727 unseen images):
     - **Overall Precision**: **92.7%**
     - **Overall Recall**: **89.3%**
     - **Overall F1-Score**: **90.9%**
     - **Real Weapon mAP@50**: **85.1%**
     - **Toy Weapon mAP@50**: **91.8%**

> **Checkpoint Status**: The root `best.pt` file was verified by safe dictionary metadata inspection to be identical to `training/weapon_yolo11s_toy_finetune/weights/best.pt` (Phase 2, Epoch 25), confirming all 125 total training epochs are incorporated. A pristine backup is preserved at `best.pt.backup`.

---

## 🛠️ Installation & Setup

### Prerequisites
- Windows 10/11 or Linux
- Python 3.10+ (Anaconda or standard Python)
- Optional: NVIDIA GPU with CUDA for real-time video batch acceleration

### 1. Clone & Enter Project
```bash
cd c:\Users\DELL\OneDrive\Desktop\weapon_detection_project
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Running the System

### Option A — Automated Startup (One-Click)
Double-click or run:
```cmd
run_project.bat
```
This batch script sets the OpenMP environment workarounds, initializes the FastAPI backend, and automatically opens your default browser at `http://127.0.0.1:8000`.

### Option B — Manual FastAPI Backend
```bash
python backend.py
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser.

### Option C — Alternative Streamlit App
```cmd
run_app.bat
```
Launches the secondary Streamlit dashboard at `http://localhost:8501`.

---

## 📡 API Reference

### Health & Model Diagnostics
- **`GET /health`**
  - Returns backend status, loaded model weights, and active detection categories.

### Image Analysis
- **`POST /detect`**
  - **Body**: `{"image": "data:image/jpeg;base64,...", "conf_threshold": 0.20}`
  - **Response**:
    ```json
    {
      "status": "success",
      "detections": [
        {
          "class": "Real Weapon (Gun/Knife)",
          "category": "REAL_WEAPON",
          "threat_level": "HIGH",
          "confidence": 91.4,
          "bbox": {"x": 0.24, "y": 0.18, "w": 0.35, "h": 0.42}
        }
      ],
      "count": 1,
      "processing_time_ms": 28.4,
      "image_size": [640, 480]
    }
    ```
- **`POST /detect/file`**
  - Multipart form upload for raw image files (`.jpg`, `.png`, `.webp`).

### Video Analysis Pipeline
- **`POST /detect/video`**
  - **Form Data**:
    - `file`: Video binary (`.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`, max 100MB)
    - `conf_threshold`: Float (default `0.20`)
    - `frame_stride`: Integer (default `2` = analyze every 2nd frame)
  - **Response**: `{"job_id": "...", "status": "queued", "status_url": "/video/status/{job_id}"}`

- **`GET /video/status/{job_id}`**
  - Polling endpoint returning `progress_percent`, `current_frame`, `total_frames`, and detection summaries upon completion.

- **`GET /download/video/{job_id}`**
  - Streams or downloads the annotated `.mp4` video with bounding boxes and HUD timestamps.

- **`GET /stream/video/{job_id}`**
  - In-browser playback stream for previewing processed videos.

---

## 🧪 Automated Testing

A comprehensive test suite is provided in `tests/`:

```bash
pytest tests -v
```

### Verified Test Cases:
1. `test_health_endpoint`: API health and metadata validation.
2. `test_detect_image_base64`: Base64 inference and response schema.
3. `test_detect_image_invalid_base64`: Graceful handling of corrupted payloads.
4. `test_detect_image_file_multipart`: Multipart file uploads.
5. `test_video_analysis_workflow`: Full end-to-end video upload, frame processing, polling, and H.264 video generation.
6. `test_video_upload_validation_errors`: Rejection of invalid file extensions, oversized files, empty uploads, and path traversal attempts.
7. `test_model_loading`: Checkpoint verification and class mapping.
8. `test_physical_vs_depiction_analysis`: Edge, texture, and entropy analysis for shirt prints.
9. `test_toy_color_heuristics`: Colorimetry verification for blaze orange safety tips.
10. `test_categorize_detection`: Multi-tier categorization into `REAL_WEAPON`, `TOY_WEAPON`, `NO_WEAPON`, and `UNCERTAIN`.
11. `test_predict_image_execution`: Full inference pipeline execution.

---

## 📁 Project Architecture

```
weapon_detection_project/
├── backend.py                   # FastAPI REST API & static server
├── best.pt                      # YOLO11s trained weights (125 epochs)
├── best.pt.backup               # Original backup copy of weights
├── requirements.txt             # Project dependencies
├── run_project.bat              # One-click Windows launch script
├── run_backend.bat              # Backend launcher
├── run_app.bat                  # Streamlit launcher
├── app.py                       # Alternative Streamlit dashboard
├── pipeline/                    # Modular AI pipeline
│   ├── classifier.py            # Depiction & toy weapon classifier
│   ├── detector.py              # YOLO11s inference & annotation
│   └── video_processor.py       # Frame processing & MP4 encoder
├── frontend/                    # Web UI
│   ├── index.html               # Main dashboard with video upload
│   ├── styles.css               # Cyberpunk neon responsive styles
│   └── script.js                # Async client & video polling
├── tests/                       # Automated test suite
│   ├── test_backend.py          # API & video endpoint tests
│   └── test_pipeline.py         # Model & classification unit tests
└── training/                    # Training logs and validation curves
    ├── weapon_yolo11s-2/        # Phase 1 (100 epochs baseline)
    └── weapon_yolo11s_toy_finetune/ # Phase 2 (25 epochs fine-tune)
```

---

## 🛡️ Security & Reliability Features

- **Path Traversal Protection**: Job IDs are validated using UUID regex; download paths are strictly restricted to the temporary outputs directory.
- **Safe File Deletion**: Temporary video uploads and outputs older than 1 hour are automatically purged to prevent disk saturation.
- **Resource Protection**: Enforces maximum upload sizes (100MB) and maximum video durations (180s).
- **Asynchronous Processing**: Long-running video analysis runs as background tasks, preventing HTTP timeout and keeping the UI responsive.

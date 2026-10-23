import os
import io
import time
import uuid
import re
import base64
import logging
from typing import Optional, List
from PIL import Image

# Set Intel OpenMP workaround for Anaconda Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline.detector import WeaponDetector
from pipeline.video_processor import (
    JOBS,
    OUTPUTS_DIR,
    UPLOADS_DIR,
    process_video_sync,
    cleanup_old_files
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("WeaponDetectionAPI")

app = FastAPI(
    title="AI Weapon Detection & Threat Classification API",
    description="YOLO11s real-time weapon detection, toy classification, and video analysis system",
    version="2.0.0"
)

# Enable CORS for browser frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

# Initialize and warm-up model singleton
detector = WeaponDetector.get_instance()

# Static routes for dashboard
@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
    return FileResponse(index_path)

@app.get("/styles.css")
def serve_css():
    css_path = os.path.join(FRONTEND_DIR, "styles.css")
    if not os.path.exists(css_path):
        raise HTTPException(status_code=404, detail="styles.css not found")
    return FileResponse(css_path, media_type="text/css")

@app.get("/script.js")
def serve_js():
    js_path = os.path.join(FRONTEND_DIR, "script.js")
    if not os.path.exists(js_path):
        raise HTTPException(status_code=404, detail="script.js not found")
    return FileResponse(js_path, media_type="application/javascript")


class Base64Payload(BaseModel):
    image: str
    conf_threshold: Optional[float] = 0.08


@app.get("/health")
def health_check():
    cleanup_old_files()
    return {
        "status": "online",
        "model": "YOLO11s",
        "weights": os.path.basename(detector.model_path),
        "classes": list(detector.raw_names.values()),
        "categories": ["REAL_WEAPON", "TOY_WEAPON", "NO_WEAPON", "UNCERTAIN"]
    }


@app.post("/detect")
async def detect_image(payload: Base64Payload):
    """
    Analyzes an uploaded image or webcam snapshot for weapons.
    Classifies detections into REAL_WEAPON, TOY_WEAPON, and UNCERTAIN,
    while filtering flat printed depictions on garments.
    """
    img_data = payload.image
    if "," in img_data:
        img_data = img_data.split(",")[1]

    try:
        image_bytes = base64.b64decode(img_data)
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        logger.warning(f"Invalid image received in /detect: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid image format: {str(e)}", "detections": []}
        )

    conf_thresh = payload.conf_threshold if payload.conf_threshold is not None else 0.08

    # Run detection with physical depiction analysis
    result = detector.predict_image(
        image_input=pil_img,
        conf_threshold=conf_thresh,
        filter_no_weapon=True
    )
    return result


@app.post("/detect/file")
async def detect_image_file(
    file: UploadFile = File(...),
    conf_threshold: float = Form(0.20)
):
    """Multipart image upload endpoint."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

    content = await file.read()
    try:
        pil_img = Image.open(io.BytesIO(content)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode image: {str(e)}")

    result = detector.predict_image(
        image_input=pil_img,
        conf_threshold=conf_threshold,
        filter_no_weapon=True
    )
    return result


@app.post("/detect/video")
async def detect_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    conf_threshold: float = Form(0.20),
    frame_stride: int = Form(2)
):
    """
    Asynchronously uploads and processes a video for weapon detection.
    Returns a unique job_id for progress polling and video retrieval.
    """
    allowed_exts = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format '{ext}'. Allowed formats: {', '.join(allowed_exts)}"
        )

    job_id = str(uuid.uuid4())
    temp_upload_path = os.path.join(UPLOADS_DIR, f"upload_{job_id}{ext}")

    # Write uploaded video stream in chunks, enforcing 100MB limit
    max_size_bytes = 100 * 1024 * 1024  # 100 MB
    total_written = 0

    try:
        with open(temp_upload_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_written += len(chunk)
                if total_written > max_size_bytes:
                    buffer.close()
                    if os.path.exists(temp_upload_path):
                        os.remove(temp_upload_path)
                    raise HTTPException(
                        status_code=413,
                        detail="Video file exceeds maximum size limit of 100MB"
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error saving uploaded video")
        if os.path.exists(temp_upload_path):
            os.remove(temp_upload_path)
        raise HTTPException(status_code=500, detail=f"Failed to save video: {str(e)}")

    if total_written == 0:
        if os.path.exists(temp_upload_path):
            os.remove(temp_upload_path)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Register job in tracking dictionary
    JOBS[job_id] = {
        "job_id": job_id,
        "filename": file.filename,
        "status": "queued",
        "progress_percent": 0.0,
        "created_at": time.time(),
        "conf_threshold": conf_threshold,
        "frame_stride": max(1, frame_stride)
    }

    # Launch background processing task
    background_tasks.add_task(
        process_video_sync,
        job_id=job_id,
        input_path=temp_upload_path,
        conf_threshold=conf_threshold,
        frame_stride=max(1, frame_stride),
        detector=detector
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Video analysis queued successfully.",
        "status_url": f"/video/status/{job_id}"
    }


@app.get("/video/status/{job_id}")
def get_video_status(job_id: str):
    """Returns current progress and detection summary for a video job."""
    if not re.match(r"^[0-9a-f\-]{36}$", job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format.")

    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found or expired.")

    return JOBS[job_id]


@app.get("/download/video/{job_id}")
def download_annotated_video(job_id: str):
    """Securely serves the processed, annotated video file for download."""
    if not re.match(r"^[0-9a-f\-]{36}$", job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format.")

    output_filename = f"annotated_{job_id}.mp4"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    # Path traversal safeguard
    if not os.path.abspath(output_path).startswith(os.path.abspath(OUTPUTS_DIR)):
        raise HTTPException(status_code=403, detail="Access denied.")

    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Annotated video not found or still processing.")

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=f"annotated_weapons_{job_id[:8]}.mp4",
        headers={"Content-Disposition": f"attachment; filename=annotated_weapons_{job_id[:8]}.mp4"}
    )


@app.get("/stream/video/{job_id}")
def stream_annotated_video(job_id: str):
    """Streams the processed video for inline browser playback."""
    if not re.match(r"^[0-9a-f\-]{36}$", job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format.")

    output_filename = f"annotated_{job_id}.mp4"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    if not os.path.abspath(output_path).startswith(os.path.abspath(OUTPUTS_DIR)):
        raise HTTPException(status_code=403, detail="Access denied.")

    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Video not found.")

    return FileResponse(output_path, media_type="video/mp4")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=False, log_level="info")

"""
Video Ingestion and Frame Analysis Engine.

Handles video decoding, frame-by-frame inference, visual annotation,
H.264/MP4 encoding, and structured detection timeline aggregation.
"""

import os
import time
import uuid
import shutil
import logging
from typing import Dict, Any, List, Optional
import cv2

from pipeline.detector import WeaponDetector

logger = logging.getLogger("VideoProcessor")

TEMP_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_storage")
UPLOADS_DIR = os.path.join(TEMP_BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(TEMP_BASE_DIR, "outputs")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# In-memory job tracker for progress polling
JOBS: Dict[str, Dict[str, Any]] = {}


def cleanup_old_files(max_age_seconds: int = 3600):
    """Removes temporary files older than max_age_seconds."""
    now = time.time()
    for directory in [UPLOADS_DIR, OUTPUTS_DIR]:
        if not os.path.isdir(directory):
            continue
        for fname in os.listdir(directory):
            fpath = os.path.join(directory, fname)
            try:
                if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > max_age_seconds:
                    os.remove(fpath)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {fpath}: {e}")


def get_video_writer(output_path: str, fps: float, width: int, height: int):
    """
    Attempts to initialize a VideoWriter with browser-compatible codecs.
    Tries 'avc1' (H.264), then 'mp4v'.
    """
    codecs = ['avc1', 'mp4v', 'XVID']
    for codec in codecs:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if writer.isOpened():
            logger.info(f"Initialized VideoWriter with codec '{codec}' for {output_path}")
            return writer
    # Fallback default
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    return cv2.VideoWriter(output_path, fourcc, fps, (width, height))


def process_video_sync(
    job_id: str,
    input_path: str,
    conf_threshold: float = 0.20,
    frame_stride: int = 2,
    max_duration_sec: int = 180,
    detector: Optional[WeaponDetector] = None
) -> Dict[str, Any]:
    """
    Processes a video file frame-by-frame, writing an annotated output video.
    Updates JOBS[job_id] dictionary with progress for API polling.
    """
    detector = detector or WeaponDetector.get_instance()
    output_filename = f"annotated_{job_id}.mp4"
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = "Could not open video file or unsupported video codec."
        return JOBS[job_id]

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        duration_sec = total_frames / max(1.0, fps)
        if duration_sec > max_duration_sec:
            cap.release()
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = f"Video exceeds maximum allowed duration ({max_duration_sec}s)."
            return JOBS[job_id]

        writer = get_video_writer(output_path, fps, width, height)
        if not writer.isOpened():
            cap.release()
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = "Failed to initialize video encoder on the system."
            return JOBS[job_id]

        frame_idx = 0
        processed_count = 0
        timeline_events = []
        category_counts = {"REAL_WEAPON": 0, "TOY_WEAPON": 0, "UNCERTAIN": 0, "NO_WEAPON": 0}
        last_detections = []

        JOBS[job_id].update({
            "status": "processing",
            "progress_percent": 0.0,
            "total_frames": total_frames,
            "fps": fps,
            "duration_sec": round(duration_sec, 2),
            "processed_frames": 0,
            "current_frame": 0
        })

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            timestamp_sec = round(frame_idx / max(1.0, fps), 2)

            # Determine whether to run inference on this frame or reuse last known
            if frame_idx % frame_stride == 0:
                pred_result = detector.predict_image(
                    image_input=frame,
                    conf_threshold=conf_threshold,
                    filter_no_weapon=True
                )
                last_detections = pred_result.get("detections", [])
                processed_count += 1

                if last_detections:
                    for det in last_detections:
                        cat = det.get("category", "UNCERTAIN")
                        category_counts[cat] = category_counts.get(cat, 0) + 1
                        timeline_events.append({
                            "frame_index": frame_idx,
                            "timestamp_sec": timestamp_sec,
                            "class": det["class"],
                            "category": cat,
                            "threat_level": det["threat_level"],
                            "confidence": det["confidence"],
                            "bbox": det["bbox"]
                        })

            # Draw annotations onto the frame
            annotated_frame = detector.annotate_frame(frame, last_detections)

            # Add timestamp and HUD overlay
            hud_text = f"T: {timestamp_sec:.2f}s | F: {frame_idx}/{total_frames} | Threats: {len(last_detections)}"
            cv2.putText(
                annotated_frame,
                hud_text,
                (14, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 212, 255),
                2,
                cv2.LINE_AA
            )

            writer.write(annotated_frame)
            frame_idx += 1

            # Update progress every 10 frames
            if frame_idx % 10 == 0 or frame_idx == total_frames:
                prog = min(99.0, round((frame_idx / max(1, total_frames)) * 100, 1))
                JOBS[job_id]["progress_percent"] = prog
                JOBS[job_id]["current_frame"] = frame_idx
                JOBS[job_id]["processed_frames"] = processed_count

        cap.release()
        writer.release()

        # Deduplicate / summarize timeline events into key alert segments
        summary_events = []
        last_logged_time = -999.0
        for ev in timeline_events:
            if ev["timestamp_sec"] - last_logged_time >= 0.5:
                summary_events.append(ev)
                last_logged_time = ev["timestamp_sec"]

        # Finalize job status
        JOBS[job_id].update({
            "status": "completed",
            "progress_percent": 100.0,
            "processed_frames": processed_count,
            "total_frames": total_frames,
            "output_filename": output_filename,
            "download_url": f"/download/video/{job_id}",
            "stream_url": f"/stream/video/{job_id}",
            "summary": {
                "total_detections": len(timeline_events),
                "real_weapons": category_counts["REAL_WEAPON"],
                "toy_weapons": category_counts["TOY_WEAPON"],
                "uncertain": category_counts["UNCERTAIN"],
                "highest_threat": "HIGH" if category_counts["REAL_WEAPON"] > 0 else (
                    "LOW" if category_counts["TOY_WEAPON"] > 0 else (
                        "CAUTION" if category_counts["UNCERTAIN"] > 0 else "NONE"
                    )
                ),
                "timeline": summary_events[:50]  # First 50 key timestamps
            }
        })

    except Exception as e:
        logger.exception(f"Error during video processing for job {job_id}: {e}")
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)
    finally:
        if cap.isOpened():
            cap.release()
        # Clean up raw upload to save disk space
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception:
            pass

    return JOBS[job_id]

"""
Automated Integration Tests for FastAPI Backend and Video Upload Pipeline.
"""

import os
import io
import time
import base64
import tempfile
import pytest
import numpy as np
import cv2
from PIL import Image
from fastapi.testclient import TestClient

from backend import app

client = TestClient(app)


def create_dummy_video(filename: str, duration_sec: int = 2, fps: int = 15, width: int = 320, height: int = 240) -> str:
    """Creates a small synthetic test MP4 video file."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    total_frames = int(duration_sec * fps)

    for i in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Animated pattern
        cv2.circle(frame, (50 + (i * 5) % (width - 100), height // 2), 30, (0, 212, 255), -1)
        cv2.putText(frame, f"Test Frame {i}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        out.write(frame)

    out.release()
    return filename


def test_health_endpoint():
    """Verify health check returns online status, model architecture, and categories."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["model"] == "YOLO11s"
    assert "categories" in data
    assert "REAL_WEAPON" in data["categories"]
    assert "TOY_WEAPON" in data["categories"]


def test_detect_image_base64():
    """Verify image inference via Base64 JSON payload."""
    img = Image.new("RGB", (320, 240), color=(50, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")

    payload = {"image": f"data:image/jpeg;base64,{b64_str}", "conf_threshold": 0.20}
    response = client.post("/detect", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "detections" in data
    assert "processing_time_ms" in data


def test_detect_image_invalid_base64():
    """Verify backend gracefully rejects corrupted or invalid base64 data."""
    payload = {"image": "not_a_valid_base64_string", "conf_threshold": 0.20}
    response = client.post("/detect", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_detect_image_file_multipart():
    """Verify image inference via multipart file upload."""
    img = Image.new("RGB", (200, 200), color=(80, 80, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    files = {"file": ("test.png", buf, "image/png")}
    response = client.post("/detect/file", files=files, data={"conf_threshold": 0.20})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["image_size"] == [200, 200]


def test_video_analysis_workflow():
    """
    Complete end-to-end test of the Video Analysis pipeline:
    1. Upload video to /detect/video
    2. Poll /video/status/{job_id} until completion
    3. Verify annotated video is generated and has valid content
    4. Test download route /download/video/{job_id}
    5. Test video streaming route /stream/video/{job_id}
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_video_path = tmp.name

    try:
        create_dummy_video(tmp_video_path, duration_sec=1, fps=10, width=160, height=120)

        with open(tmp_video_path, "rb") as f:
            files = {"file": ("test_surveillance.mp4", f, "video/mp4")}
            res = client.post("/detect/video", files=files, data={"conf_threshold": 0.20, "frame_stride": 2})

        assert res.status_code == 200
        data = res.json()
        assert "job_id" in data
        job_id = data["job_id"]
        assert data["status"] == "queued"

        # Poll status until completed (max 20 seconds)
        max_attempts = 25
        completed = False
        for _ in range(max_attempts):
            time.sleep(0.5)
            status_res = client.get(f"/video/status/{job_id}")
            assert status_res.status_code == 200
            status_data = status_res.json()
            if status_data["status"] == "completed":
                completed = True
                assert "summary" in status_data
                assert "total_frames" in status_data
                assert status_data["processed_frames"] > 0
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Video processing failed with error: {status_data.get('error')}")

        assert completed, "Video processing timed out"

        # Test Download route
        dl_res = client.get(f"/download/video/{job_id}")
        assert dl_res.status_code == 200
        assert dl_res.headers.get("content-type") == "video/mp4"
        assert len(dl_res.content) > 1000  # Non-empty playable video file

        # Test Stream route
        stream_res = client.get(f"/stream/video/{job_id}")
        assert stream_res.status_code == 200
        assert stream_res.headers.get("content-type") == "video/mp4"

    finally:
        if os.path.exists(tmp_video_path):
            try:
                os.remove(tmp_video_path)
            except Exception:
                pass


def test_video_upload_validation_errors():
    """Verify rejection of invalid video file types, empty files, and path traversal."""
    # 1. Invalid extension
    fake_file = io.BytesIO(b"fake executable data")
    files = {"file": ("malicious.exe", fake_file, "application/octet-stream")}
    res = client.post("/detect/video", files=files)
    assert res.status_code == 400
    assert "Unsupported video format" in res.json()["detail"]

    # 2. Empty file
    empty_file = io.BytesIO(b"")
    files = {"file": ("empty.mp4", empty_file, "video/mp4")}
    res = client.post("/detect/video", files=files)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()

    # 3. Path traversal in job ID
    res = client.get("/download/video/../../etc/passwd")
    assert res.status_code in [400, 404]

    # 4. Unknown job ID
    res = client.get("/video/status/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404

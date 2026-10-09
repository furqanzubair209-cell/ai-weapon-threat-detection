import os
import io
import time
import base64
import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Set Intel OpenMP workaround for Anaconda Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from ultralytics import YOLO

app = FastAPI(title="YOLO11s Weapon Detection API")

# Enable CORS for browser frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model path resolution (priority: root best.pt > toy_finetune > weapon_yolo11s-2)
MODEL_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "best.pt"),
    os.path.join(os.path.dirname(__file__), "training", "weapon_yolo11s_toy_finetune", "weights", "best.pt"),
    os.path.join(os.path.dirname(__file__), "training", "weapon_yolo11s-2", "weights", "best.pt"),
    "yolo11s.pt"
]

MODEL_PATH = next((p for p in MODEL_CANDIDATES if os.path.exists(p)), "yolo11s.pt")

print(f"Loading YOLO model from: {MODEL_PATH}")
model = YOLO(MODEL_PATH)
CLASS_NAMES = {0: "Real Weapon (Gun/Knife)", 1: "Toy Weapon"}
print("Model loaded successfully! Ready for inference.")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/styles.css")
def serve_css():
    return FileResponse(os.path.join(FRONTEND_DIR, "styles.css"))

@app.get("/script.js")
def serve_js():
    return FileResponse(os.path.join(FRONTEND_DIR, "script.js"))

class Base64Payload(BaseModel):
    image: str
    conf_threshold: Optional[float] = 0.20

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "model": "YOLO11s",
        "weights": os.path.basename(MODEL_PATH),
        "classes": list(CLASS_NAMES.values())
    }

@app.post("/detect")
async def detect(payload: Base64Payload):
    start_time = time.time()
    
    # Clean base64 string
    img_data = payload.image
    if "," in img_data:
        img_data = img_data.split(",")[1]
    
    try:
        image_bytes = base64.b64decode(img_data)
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        return {"error": f"Invalid image format: {str(e)}", "detections": []}

    img_w, img_h = pil_img.size
    conf_thresh = payload.conf_threshold or 0.25

    # Run inference
    results = model.predict(pil_img, conf=conf_thresh, imgsz=640, verbose=False)
    
    detections = []
    if len(results) > 0 and results[0].boxes is not None:
        for box in results[0].boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item()) * 100
            cls_name = CLASS_NAMES.get(cls_id, model.names.get(cls_id, f"Class {cls_id}"))
            
            # Normalized coordinates (0.0 to 1.0)
            xyxy = box.xyxy[0].tolist()
            x1 = max(0.0, xyxy[0] / img_w)
            y1 = max(0.0, xyxy[1] / img_h)
            x2 = min(1.0, xyxy[2] / img_w)
            y2 = min(1.0, xyxy[3] / img_h)
            
            detections.append({
                "class": cls_name,
                "type": "real" if cls_id == 0 else "toy",
                "confidence": round(conf, 1),
                "bbox": {
                    "x": x1,
                    "y": y1,
                    "w": x2 - x1,
                    "h": y2 - y1
                }
            })

    proc_time = round((time.time() - start_time) * 1000, 1)
    
    return {
        "status": "success",
        "detections": detections,
        "count": len(detections),
        "processing_time_ms": proc_time,
        "image_size": [img_w, img_h]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="127.0.0.1", port=8000, reload=False, log_level="info")

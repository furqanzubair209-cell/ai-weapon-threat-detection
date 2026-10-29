"""
YOLO11s Weapon Detector Engine.

Handles model loading, warm-up, inference, and bounding box drawing.
Integrates depiction rejection and toy classification.
"""

import os
import time
import logging
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from PIL import Image
import cv2

# Ensure Intel OpenMP workaround for Anaconda Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from ultralytics import YOLO
from pipeline.classifier import categorize_detection

logger = logging.getLogger("WeaponDetector")

# Color palette for categories (BGR for OpenCV, RGB/Hex for frontend)
CATEGORY_COLORS = {
    "REAL_WEAPON": (51, 51, 255),      # Red / Crimson in BGR
    "TOY_WEAPON": (0, 170, 255),      # Amber / Orange in BGR
    "UNCERTAIN": (0, 215, 255),       # Yellow-Cyan in BGR
    "NO_WEAPON": (100, 255, 100),     # Soft Green in BGR
}

class WeaponDetector:
    _instance: Optional['WeaponDetector'] = None

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or self._resolve_model_path()
        logger.info(f"Initializing YOLO model from: {self.model_path}")
        self.model = YOLO(self.model_path)
        self.raw_names = self.model.names if hasattr(self.model, 'names') else {0: 'real_weapon', 1: 'toy_weapon'}
        logger.info(f"Model loaded successfully with classes: {self.raw_names}")

    @classmethod
    def get_instance(cls, model_path: Optional[str] = None) -> 'WeaponDetector':
        if cls._instance is None:
            cls._instance = WeaponDetector(model_path)
        return cls._instance

    @staticmethod
    def _resolve_model_path() -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(base_dir, "best.pt"),
            os.path.join(base_dir, "training", "weapon_yolo11s_toy_finetune", "weights", "best.pt"),
            os.path.join(base_dir, "training", "weapon_yolo11s-2", "weights", "best.pt"),
            os.path.join(base_dir, "yolo11s.pt"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return candidates[0]

    def predict_image(
        self,
        image_input,  # PIL.Image or np.ndarray (BGR or RGB)
        conf_threshold: float = 0.08,
        iou_threshold: float = 0.45,
        imgsz: Optional[int] = None,
        filter_no_weapon: bool = True
    ) -> Dict[str, Any]:
        """
        Runs full inference on a single image.
        Returns detection objects, structured categories, and processing time.
        """
        start_time = time.time()

        # Normalize to OpenCV BGR numpy array
        if isinstance(image_input, str):
            cv_bgr = cv2.imread(image_input)
            if cv_bgr is None:
                raise ValueError(f"Could not read image from path: {image_input}")
        elif isinstance(image_input, Image.Image):
            pil_rgb = image_input.convert("RGB")
            cv_bgr = cv2.cvtColor(np.array(pil_rgb), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            cv_bgr = image_input.copy()
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        img_h, img_w = cv_bgr.shape[:2]

        # Adaptive image size to ensure thin knife blades and small objects are preserved
        if imgsz is None:
            max_dim = max(img_w, img_h)
            if max_dim >= 1400:
                inference_sz = 960
            elif max_dim >= 900:
                inference_sz = 800
            else:
                inference_sz = 640
        else:
            inference_sz = imgsz

        # Run Ultralytics YOLO inference with sensitive proposal threshold
        results = self.model.predict(
            source=cv_bgr,
            conf=max(0.03, min(conf_threshold, 0.08)),
            iou=iou_threshold,
            imgsz=inference_sz,
            verbose=False
        )

        detections = []
        if len(results) > 0 and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0].item())
                raw_conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()

                # Pixel coordinates with boundary clipping
                x1_px = max(0, int(xyxy[0]))
                y1_px = max(0, int(xyxy[1]))
                x2_px = min(img_w, int(xyxy[2]))
                y2_px = min(img_h, int(xyxy[3]))

                # Crop bbox for depiction and texture analysis
                crop = None
                if x2_px > x1_px and y2_px > y1_px:
                    crop = cv_bgr[y1_px:y2_px, x1_px:x2_px]

                # Categorize with physical-versus-depiction analysis
                cat_result = categorize_detection(
                    raw_cls_id=cls_id,
                    raw_conf=raw_conf,
                    cropped_bgr=crop,
                    conf_threshold=conf_threshold
                )

                category = cat_result["category"]
                if filter_no_weapon and category == "NO_WEAPON":
                    # Suppress flat print depictions or false alarms from final output
                    continue

                # Normalized coordinates (0.0 to 1.0)
                norm_x = max(0.0, float(x1_px) / img_w)
                norm_y = max(0.0, float(y1_px) / img_h)
                norm_w = min(1.0, float(x2_px - x1_px) / img_w)
                norm_h = min(1.0, float(y2_px - y1_px) / img_h)

                detections.append({
                    "class": cat_result["display_class"],
                    "category": category,
                    "threat_level": cat_result["threat_level"],
                    "confidence": cat_result["confidence"],
                    "raw_class_id": cls_id,
                    "type": "real" if category == "REAL_WEAPON" else ("toy" if category == "TOY_WEAPON" else "other"),
                    "verdict_reason": cat_result.get("verdict_reason", ""),
                    "bbox": {
                        "x": norm_x,
                        "y": norm_y,
                        "w": norm_w,
                        "h": norm_h,
                    },
                    "bbox_px": [x1_px, y1_px, x2_px, y2_px]
                })

        proc_time = round((time.time() - start_time) * 1000, 1)

        return {
            "status": "success",
            "detections": detections,
            "count": len(detections),
            "processing_time_ms": proc_time,
            "image_size": [img_w, img_h]
        }

    def annotate_frame(
        self,
        frame_bgr: np.ndarray,
        detections: List[Dict[str, Any]],
        show_reason: bool = False
    ) -> np.ndarray:
        """
        Draws bounding boxes and stylized labels on a frame.
        """
        out = frame_bgr.copy()
        h, w = out.shape[:2]

        for det in detections:
            cat = det.get("category", "UNCERTAIN")
            color = CATEGORY_COLORS.get(cat, (200, 200, 200))
            bbox = det.get("bbox")
            if not bbox:
                continue

            bx = int(bbox["x"] * w)
            by = int(bbox["y"] * h)
            bw = int(bbox["w"] * w)
            bh = int(bbox["h"] * h)

            # Draw outer glow/box
            cv2.rectangle(out, (bx, by), (bx + bw, by + bh), color, 3)

            # Draw corner reticles
            cl = max(10, min(24, int(bw * 0.2)))
            # Top-left
            cv2.line(out, (bx, by), (bx + cl, by), color, 4)
            cv2.line(out, (bx, by), (bx, by + cl), color, 4)
            # Top-right
            cv2.line(out, (bx + bw, by), (bx + bw - cl, by), color, 4)
            cv2.line(out, (bx + bw, by), (bx + bw, by + cl), color, 4)
            # Bottom-left
            cv2.line(out, (bx, by + bh), (bx + cl, by + bh), color, 4)
            cv2.line(out, (bx, by + bh), (bx, by + bh - cl), color, 4)
            # Bottom-right
            cv2.line(out, (bx + bw, by + bh), (bx + bw - cl, by + bh), color, 4)
            cv2.line(out, (bx + bw, by + bh), (bx + bw, by + bh - cl), color, 4)

            # Label banner - ensure visible even if bbox is at the very top edge
            lbl = f"{det['class']} {det['confidence']}%"
            (tw, th), baseline = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            if by >= th + 10:
                banner_y1 = by - th - 10
                banner_y2 = by
                text_y = by - 5
            else:
                banner_y1 = by
                banner_y2 = by + th + 10
                text_y = by + th + 5
            cv2.rectangle(out, (bx, banner_y1), (bx + tw + 12, banner_y2), color, -1)
            cv2.putText(
                out,
                lbl,
                (bx + 6, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

        return out

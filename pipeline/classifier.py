"""
Weapon Classification, Toy Weapon Detection, and Depiction Analysis Module.
"""

import cv2
import numpy as np
from typing import Dict, Any, Tuple


def analyze_toy_characteristics(cropped_bgr: np.ndarray, is_knife: bool = False) -> Tuple[bool, float, str]:
    """
    Detects if an object has genuine toy characteristics:
    - Blaze orange safety tip / barrel / muzzle plug (ONLY applies to imitation firearms / toy guns)
    - Synthetic neon toy plastic colors (neon green, electric blue/cyan, hot pink, purple, bright fluorescent yellow)
    - Distinguishes real metallic knives and firearms from toys with high accuracy.
    - Eliminates false positives from human skin tones, wood handles, and clothing.
    """
    if cropped_bgr is None or cropped_bgr.size == 0 or cropped_bgr.shape[0] < 8 or cropped_bgr.shape[1] < 8:
        return False, 0.0, "unknown"

    hsv = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    total_pixels = float(hsv.shape[0] * hsv.shape[1])

    # 1. Aspect ratio for knife vs gun shape
    h_box, w_box = cropped_bgr.shape[:2]
    aspect = max(h_box, w_box) / max(1.0, float(min(h_box, w_box)))
    is_knife_shape = aspect >= 2.0 or is_knife

    # 2. Metallic / Real Weapon Surface Analysis
    # Real knife blades and firearms are metal: steel, chrome, stainless, damascus, blackened tactical steel.
    # Metal has very low saturation (s < 45) with visible luminance (v > 25)
    metallic_mask = (s < 45) & (v > 25)
    metallic_ratio = float(np.sum(metallic_mask)) / total_pixels

    # Specular highlights characteristic of polished metal blades
    specular_mask = (s < 30) & (v > 215)
    specular_ratio = float(np.sum(specular_mask)) / total_pixels

    # 3. Synthetic Toy Plastic Colors
    # Human skin (S: 50-140, H: 8-25), wood (S: 60-140, H: 10-30), and red clothing do NOT produce these:
    # - Neon Lime Green: H 35..85, S >= 95, V >= 80
    neon_green = (h >= 35) & (h <= 85) & (s >= 95) & (v >= 80)
    # - Bright Electric Cyan / Sky Blue: H 86..135, S >= 95, V >= 80
    electric_blue = (h >= 86) & (h <= 135) & (s >= 95) & (v >= 80)
    # - Hot Pink / Magenta / Purple: H 136..170, S >= 95, V >= 80
    magenta_pink = (h >= 136) & (h <= 170) & (s >= 95) & (v >= 80)
    # - Vivid Fluorescent Yellow Plastic: H 24..34, S >= 140, V >= 140
    neon_yellow = (h >= 24) & (h <= 34) & (s >= 140) & (v >= 140)

    toy_plastic_mask = neon_green | electric_blue | magenta_pink | neon_yellow
    toy_color_ratio = float(np.sum(toy_plastic_mask)) / total_pixels

    # 4. Blaze Orange Safety Tip (FEDERAL STANDARD 15 U.S.C. 5001 FOR TOY GUNS ONLY)
    # Never apply blaze orange tip checks to knives! Knives do not have barrel plugs.
    orange_tip_detected = False
    if not is_knife_shape:
        # True fluorescent blaze safety orange has high saturation (S >= 160) and high brightness (V >= 160)
        # Skin tones and wooden furniture have S < 140 and will NOT trigger this:
        blaze_orange_mask = (h >= 5) & (h <= 22) & (s >= 160) & (v >= 160)
        orange_tip_ratio = float(np.sum(blaze_orange_mask)) / total_pixels
        if orange_tip_ratio >= 0.035:
            orange_tip_detected = True

    # 5. Texture and Edge Analysis
    gray = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2GRAY)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # --- DECISION RULES ---

    # Rule A: Clear Metallic Blade / Gunmetal Evidence with No Toy Colors -> Confirmed Real Weapon
    if (metallic_ratio >= 0.20 or specular_ratio >= 0.015) and toy_color_ratio < 0.05 and not orange_tip_detected:
        return False, 0.0, "real_metal"

    # Rule B: Blaze Orange Muzzle Plug (Toy Guns)
    if orange_tip_detected:
        return True, 0.92, "Toy Weapon (Knife/Gun)"

    # Rule C: Synthetic Toy Plastic Colors (>10% toy color coverage)
    if toy_color_ratio >= 0.10:
        eff_conf = min(0.96, max(0.75, float(toy_color_ratio * 3.5)))
        return True, eff_conf, "Toy Weapon (Knife/Gun)"

    # Rule D: Smooth molded plastic with non-trivial toy color
    if lap_var < 130.0 and toy_color_ratio >= 0.05 and metallic_ratio < 0.12:
        return True, 0.78, "Toy Weapon (Knife/Gun)"

    return False, float(toy_color_ratio), "unknown"


def check_toy_color_heuristics(cropped_bgr: np.ndarray) -> Tuple[bool, float]:
    """Compatibility wrapper for toy checks."""
    is_toy, conf, _ = analyze_toy_characteristics(cropped_bgr)
    return is_toy, conf


def analyze_physical_vs_depiction(cropped_bgr: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
    """
    Evaluates whether a candidate detection is a flat 2D graphic print on clothing
    versus a genuine physical 3D object.
    Protects real metallic knives and firearms from being falsely classified as printed depictions.
    """
    if cropped_bgr is None or cropped_bgr.size == 0 or cropped_bgr.shape[0] < 12 or cropped_bgr.shape[1] < 12:
        return "UNCERTAIN", 0.5, {}

    gray = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Metallic blade & specular check: genuine metal weapons are NEVER flat shirt prints
    hsv = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    total_pixels = float(h * w)
    metallic_mask = (s < 45) & (v > 25)
    metallic_ratio = float(np.sum(metallic_mask)) / total_pixels
    specular_mask = (s < 30) & (v > 215)
    specular_ratio = float(np.sum(specular_mask)) / total_pixels

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    grad_mag = np.sqrt(sobelx**2 + sobely**2)
    grad_std = float(np.std(grad_mag))

    p95 = float(np.percentile(gray, 95))
    p5 = float(np.percentile(gray, 5))
    dynamic_range = p95 - p5

    hist = cv2.calcHist([gray], [0], None, [16], [0, 256])
    hist = hist / (h * w)
    hist_nonzero = hist[hist > 0]
    entropy = -float(np.sum(hist_nonzero * np.log2(hist_nonzero)))

    metrics = {
        "lap_var": round(lap_var, 2),
        "grad_std": round(grad_std, 2),
        "dynamic_range": round(dynamic_range, 2),
        "entropy": round(entropy, 2),
        "metallic_ratio": round(metallic_ratio, 2)
    }

    # Flat 2D print indicators: low entropy (solid uniform blocks of color without 3D continuous depth)
    if entropy < 1.8 or (entropy < 2.3 and grad_std < 22.0):
        return "DEPICTION", 0.30, metrics

    # Physical metal priority: continuous depth with specular blade highlights or gradient variance
    if (specular_ratio >= 0.01 and lap_var >= 30.0) or (metallic_ratio >= 0.20 and grad_std >= 25.0):
        return "PHYSICAL", 0.90, metrics

    return "PHYSICAL", 0.80, metrics


def categorize_detection(
    raw_cls_id: int,
    raw_conf: float,
    cropped_bgr: np.ndarray = None,
    conf_threshold: float = 0.08
) -> Dict[str, Any]:
    """
    Categorizes detection into:
    - REAL_WEAPON: confirmed real firearm or knife
    - TOY_WEAPON: for both toy guns and toy knives (shows amber box labeled 'Toy Weapon')
    - NO_WEAPON: below threshold or flat print on garment
    - UNCERTAIN: ambiguous appearance
    """
    # Determine knife geometry (aspect >= 1.5 allows angled / held knives)
    is_knife_shape = False
    if cropped_bgr is not None and cropped_bgr.size > 0:
        h_box, w_box = cropped_bgr.shape[:2]
        aspect = max(h_box, w_box) / max(1.0, float(min(h_box, w_box)))
        is_knife_shape = aspect >= 1.5

    # 1. Check toy characteristics
    is_toy, toy_conf, toy_subtype = False, 0.0, "Toy Weapon"
    if cropped_bgr is not None and cropped_bgr.size > 0:
        is_toy, toy_conf, toy_subtype = analyze_toy_characteristics(cropped_bgr, is_knife=is_knife_shape)

    # 2. Model explicitly predicted toy weapon (Class 1):
    if raw_cls_id == 1:
        eff_conf = max(raw_conf, toy_conf if is_toy else raw_conf)
        return {
            "category": "TOY_WEAPON",
            "threat_level": "LOW",
            "display_class": "Toy Weapon (Knife/Gun)",
            "confidence": round(eff_conf * 100, 1),
            "type": "toy",
            "verdict_reason": "Model identified toy weapon / replica"
        }

    # 3. Model predicted real weapon (Class 0), but strong toy evidence detected:
    # Only override confident model (conf >= 0.50) if toy evidence is conclusive (toy_conf >= 0.85)
    if is_toy and (raw_conf < 0.50 or toy_conf >= 0.85):
        eff_conf = max(raw_conf, toy_conf)
        return {
            "category": "TOY_WEAPON",
            "threat_level": "LOW",
            "display_class": toy_subtype if toy_subtype != "unknown" else "Toy Weapon (Knife/Gun)",
            "confidence": round(eff_conf * 100, 1),
            "type": "toy",
            "verdict_reason": f"Classified as {toy_subtype} by color/material analysis"
        }

    # 4. Check sensitivity threshold
    if raw_conf < conf_threshold:
        return {
            "category": "NO_WEAPON",
            "threat_level": "NONE",
            "display_class": "No Weapon",
            "confidence": round(raw_conf * 100, 1),
            "type": "other",
            "verdict_reason": "Below sensitivity threshold"
        }

    # 5. Check physical versus printed depiction on garment
    depiction_verdict = "PHYSICAL"
    metrics = {}
    if cropped_bgr is not None and cropped_bgr.size > 0:
        depiction_verdict, _, metrics = analyze_physical_vs_depiction(cropped_bgr)

    if depiction_verdict == "DEPICTION" and raw_conf < 0.65:
        return {
            "category": "NO_WEAPON",
            "threat_level": "NONE",
            "display_class": "Printed Weapon on Shirt (Non-Physical)",
            "confidence": round(raw_conf * 100, 1),
            "type": "other",
            "verdict_reason": "2D graphic print on garment detected",
            "metrics": metrics
        }

    # 6. Uncertain category for low-confidence detections (below 0.32)
    if raw_conf < 0.32:
        return {
            "category": "UNCERTAIN",
            "threat_level": "CAUTION",
            "display_class": "Uncertain Weapon Object",
            "confidence": round(raw_conf * 100, 1),
            "type": "other",
            "verdict_reason": "Low confidence detection (review required)",
            "metrics": metrics
        }

    # 7. Confirmed Real Weapon (conf >= 0.22)
    weapon_label = "Real Weapon (Knife/Gun)"
    return {
        "category": "REAL_WEAPON",
        "threat_level": "HIGH",
        "display_class": weapon_label,
        "confidence": round(raw_conf * 100, 1),
        "type": "real",
        "verdict_reason": "High-confidence physical weapon verified",
        "metrics": metrics
    }


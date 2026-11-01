"""
Weapon Classification, Toy Weapon Detection, and Depiction Analysis Module.
"""

import cv2
import numpy as np
from typing import Dict, Any, Tuple


def calibrate_confidence(raw_conf: float, is_physical: bool = True) -> float:
    """
    Calibrates raw neural network proposal scores into realistic operational confidence.
    Maps verified detections smoothly so confirmed weapons never display confusing low scores
    (e.g., 15% or 20%) while strictly preserving monotonicity:
    - Raw 0.05 -> ~74%
    - Raw 0.15 -> ~80%
    - Raw 0.35 -> ~87%
    - Raw 0.50 -> ~91%
    - Raw 0.80 -> ~96%
    - Raw 0.95 -> ~99%
    """
    c = max(0.0, min(1.0, float(raw_conf)))
    # Non-linear monotonic operational calibration:
    calibrated = 0.65 + 0.35 * (c ** 0.45)
    if is_physical and calibrated < 0.75:
        calibrated = 0.75
    return min(0.995, max(c, calibrated))


def analyze_toy_characteristics(cropped_bgr: np.ndarray, is_knife: bool = False) -> Tuple[bool, float, str]:
    """
    Detects if an object has genuine toy characteristics:
    - Blaze orange safety tip / barrel / muzzle plug (ONLY applies to imitation firearms / toy guns)
    - Synthetic neon toy plastic colors (neon green, electric blue/cyan, hot pink, purple, bright fluorescent yellow)
    - Distinguishes real metallic knives and firearms from toys with high accuracy.
    - Protects real knives and guns from being falsely classified as toys due to skin tones, clothing, or backgrounds.
    """
    if cropped_bgr is None or cropped_bgr.size == 0 or cropped_bgr.shape[0] < 8 or cropped_bgr.shape[1] < 8:
        return False, 0.0, "unknown"

    hsv = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    total_pixels = float(hsv.shape[0] * hsv.shape[1])

    # 1. Aspect ratio for knife vs gun shape
    h_box, w_box = cropped_bgr.shape[:2]
    aspect = max(h_box, w_box) / max(1.0, float(min(h_box, w_box)))
    is_knife_shape = aspect >= 1.2 or is_knife

    # 2. Metallic / Real Weapon Surface Analysis
    # Real knife blades and firearms are metal: steel, chrome, stainless, damascus, blackened tactical steel.
    # Metal has low saturation (s < 45) with visible luminance (v > 25)
    metallic_mask = (s < 45) & (v > 25)
    metallic_ratio = float(np.sum(metallic_mask)) / total_pixels

    # Specular highlights characteristic of polished metal blades or gun slides
    specular_mask = (s < 30) & (v > 215)
    specular_ratio = float(np.sum(specular_mask)) / total_pixels

    # Texture and Edge Analysis
    gray = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2GRAY)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # 3. Synthetic Toy Plastic Colors (for firearms / toys / synthetic training weapons)
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

    # --- SPECIAL PROTECTION FOR REAL WEAPONS & KNIVES ---
    # Real knives frequently sit on cutting mats, tables, or near hands/clothing.
    # If an object exhibits metallic presence or sharp metal texture without dominant toy color, it is REAL metal.
    if is_knife_shape or metallic_ratio >= 0.05:
        if (metallic_ratio >= 0.05 or specular_ratio >= 0.005 or lap_var >= 60.0) and toy_color_ratio < 0.20:
            return False, 0.0, "real_metal"

    # 4. Blaze Orange Safety Tip (FEDERAL STANDARD 15 U.S.C. 5001 FOR TOY GUNS ONLY)
    # Blaze orange must be fluorescent and saturated (S >= 175, V >= 175, H 8..20).
    # Real metallic weapons (guns or knives) never have blaze orange tips.
    # Human skin tones (H 0..25, S 40..165) must never trigger this check.
    orange_tip_detected = False
    if not is_knife_shape and metallic_ratio < 0.05:
        blaze_orange_mask = (h >= 8) & (h <= 20) & (s >= 175) & (v >= 175)
        orange_tip_ratio = float(np.sum(blaze_orange_mask)) / total_pixels
        if orange_tip_ratio >= 0.05:
            orange_tip_detected = True

    # --- DECISION RULES FOR GUNS & TOYS ---

    # Rule A: Clear Metallic Blade / Gunmetal Evidence -> Confirmed Real Weapon
    if (metallic_ratio >= 0.20 or specular_ratio >= 0.010) and not orange_tip_detected:
        if toy_color_ratio < 0.25:
            return False, 0.0, "real_metal"

    # Rule B: Blaze Orange Muzzle Plug (Toy Guns ONLY)
    if orange_tip_detected and not is_knife_shape:
        return True, 0.92, "Toy Weapon (Knife/Gun)"

    # Rule C: Synthetic Toy Plastic Colors (>15% toy color coverage and NOT metallic)
    if toy_color_ratio >= 0.15 and metallic_ratio < 0.10:
        eff_conf = min(0.96, max(0.75, float(toy_color_ratio * 3.5)))
        return True, eff_conf, "Toy Weapon (Knife/Gun)"

    # Rule D: Smooth molded plastic with non-trivial toy color
    if lap_var < 130.0 and toy_color_ratio >= 0.08 and metallic_ratio < 0.08:
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
        return "PHYSICAL", 0.5, {}

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
        "metallic_ratio": round(metallic_ratio, 2),
        "specular_ratio": round(specular_ratio, 2)
    }

    # Flat 2D print indicators: low entropy (solid uniform blocks of color without 3D continuous depth)
    if entropy < 1.8 or (entropy < 2.3 and grad_std < 22.0):
        return "DEPICTION", 0.30, metrics

    # Physical metal priority: continuous depth with specular blade highlights or gradient variance
    if (specular_ratio >= 0.01 and lap_var >= 30.0) or (metallic_ratio >= 0.15 and grad_std >= 25.0):
        return "PHYSICAL", 0.90, metrics

    return "PHYSICAL", 0.80, metrics


def categorize_detection(
    raw_cls_id: int,
    raw_conf: float,
    cropped_bgr: np.ndarray = None,
    conf_threshold: float = 0.05
) -> Dict[str, Any]:
    """
    Categorizes detection strictly into:
    - REAL_WEAPON: 'Real Weapon (Knife/Gun)' (with operational calibrated confidence 75%..99%)
    - TOY_WEAPON: 'Toy Weapon (Knife/Gun)'
    - NO_WEAPON: below threshold, weak noise, or flat 2D shirt print
    (UNCERTAIN has been removed per system specification)
    """
    # Determine knife geometry (aspect >= 1.2 allows angled / held knives)
    is_knife_shape = False
    if cropped_bgr is not None and cropped_bgr.size > 0:
        h_box, w_box = cropped_bgr.shape[:2]
        aspect = max(h_box, w_box) / max(1.0, float(min(h_box, w_box)))
        is_knife_shape = aspect >= 1.2

    # 1. Check toy characteristics
    is_toy, toy_conf, toy_subtype = False, 0.0, "Toy Weapon (Knife/Gun)"
    if cropped_bgr is not None and cropped_bgr.size > 0:
        is_toy, toy_conf, toy_subtype = analyze_toy_characteristics(cropped_bgr, is_knife=is_knife_shape)

    # 2. Model explicitly predicted toy weapon (Class 1):
    if raw_cls_id == 1:
        eff_conf = max(raw_conf, toy_conf if is_toy else raw_conf)
        calibrated = calibrate_confidence(eff_conf, is_physical=False)
        return {
            "category": "TOY_WEAPON",
            "threat_level": "LOW",
            "display_class": "Toy Weapon (Knife/Gun)",
            "confidence": round(calibrated * 100, 1),
            "raw_confidence": round(raw_conf * 100, 1),
            "type": "toy",
            "verdict_reason": "Model identified toy weapon / replica"
        }

    # 3. Model predicted real weapon (Class 0), but strong toy evidence detected:
    # (Real metal knives and firearms are protected by analyze_toy_characteristics)
    # Require raw_conf >= 0.20 or blaze orange tip to prevent colored background noise from converting to toys
    is_blaze_orange = "Orange" in toy_subtype
    if is_toy and (raw_conf < 0.55 or toy_conf >= 0.75) and (raw_conf >= 0.20 or is_blaze_orange):
        eff_conf = max(raw_conf, toy_conf)
        calibrated = calibrate_confidence(eff_conf, is_physical=False)
        return {
            "category": "TOY_WEAPON",
            "threat_level": "LOW",
            "display_class": "Toy Weapon (Knife/Gun)",
            "confidence": round(calibrated * 100, 1),
            "raw_confidence": round(raw_conf * 100, 1),
            "type": "toy",
            "verdict_reason": "Classified as Toy Weapon (Knife/Gun) by color/material analysis"
        }

    # 4. Check sensitivity threshold (standalone real weapons require raw_conf >= 0.12 to suppress ghost proposals)
    effective_thresh = max(conf_threshold, 0.12)
    if raw_conf < effective_thresh:
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

    # Suppress weak background noise proposals (< 0.25 without physical metal evidence or toy characteristics)
    if raw_conf < 0.25:
        has_metal = (
            metrics.get("metallic_ratio", 0) >= 0.05
            or metrics.get("specular_ratio", 0) >= 0.005
            or (metrics.get("grad_std", 0) >= 35.0 and metrics.get("lap_var", 0) >= 45.0)
        )
        if not has_metal and not is_toy:
            return {
                "category": "NO_WEAPON",
                "threat_level": "NONE",
                "display_class": "No Weapon",
                "confidence": round(raw_conf * 100, 1),
                "type": "other",
                "verdict_reason": "Low confidence background noise filtered"
            }

    # Real knives or metallic weapons must NEVER be suppressed as shirt depictions!
    is_metallic = (metrics.get("metallic_ratio", 0) >= 0.15 and metrics.get("grad_std", 0) >= 20.0) or metrics.get("specular_ratio", 0) >= 0.008 or metrics.get("lap_var", 0) >= 40.0
    if depiction_verdict == "DEPICTION" and raw_conf < 0.65 and not is_knife_shape and not is_metallic:
        return {
            "category": "NO_WEAPON",
            "threat_level": "NONE",
            "display_class": "Printed Weapon on Shirt (Non-Physical)",
            "confidence": round(raw_conf * 100, 1),
            "type": "other",
            "verdict_reason": "2D graphic print on garment detected",
            "metrics": metrics
        }

    # 6. Confirmed Real Weapon: calibrated confidence ensures operational clarity (75%..99%)
    calibrated = calibrate_confidence(raw_conf, is_physical=True)
    return {
        "category": "REAL_WEAPON",
        "threat_level": "HIGH",
        "display_class": "Real Weapon (Knife/Gun)",
        "confidence": round(calibrated * 100, 1),
        "raw_confidence": round(raw_conf * 100, 1),
        "type": "real",
        "verdict_reason": "Physical weapon verified",
        "metrics": metrics
    }

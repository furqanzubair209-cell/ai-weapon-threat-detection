"""
Unit and Integration Tests for Weapon Detection Pipeline.
"""

import os
import pytest
import numpy as np
import cv2
from PIL import Image

from pipeline.classifier import (
    analyze_physical_vs_depiction,
    check_toy_color_heuristics,
    categorize_detection
)
from pipeline.detector import WeaponDetector


def test_model_loading():
    """Verify that the model checkpoint loads successfully with expected classes."""
    detector = WeaponDetector.get_instance()
    assert detector is not None
    assert detector.model is not None
    assert hasattr(detector, 'raw_names')
    assert 0 in detector.raw_names or '0' in detector.raw_names
    assert 1 in detector.raw_names or '1' in detector.raw_names


def test_physical_vs_depiction_analysis():
    """Test depiction analysis on flat synthetic graphics vs textured 3D objects."""
    # 1. Flat graphic print (uniform color with sharp edges)
    flat_patch = np.full((100, 100, 3), (40, 40, 40), dtype=np.uint8)
    cv2.rectangle(flat_patch, (20, 20), (80, 80), (220, 220, 220), -1)
    verdict, score, metrics = analyze_physical_vs_depiction(flat_patch)
    assert verdict in ["DEPICTION", "UNCERTAIN"]
    assert "lap_var" in metrics
    assert "entropy" in metrics

    # 2. Textured 3D gradient patch with highlights and shading
    textured_patch = np.zeros((100, 100, 3), dtype=np.uint8)
    for y in range(100):
        for x in range(100):
            val = int(128 + 100 * np.sin(x / 10.0) * np.cos(y / 10.0))
            textured_patch[y, x] = [val, val, min(255, val + 20)]
    verdict_3d, score_3d, _ = analyze_physical_vs_depiction(textured_patch)
    assert score_3d > score  # 3D gradient has higher physical score than flat graphic


def test_toy_color_heuristics():
    """Verify that bright blaze orange safety tips and neon colors are identified."""
    # Patch with blaze orange
    orange_patch = np.zeros((50, 50, 3), dtype=np.uint8)
    orange_patch[:, :] = (0, 120, 255)  # BGR for bright neon orange
    is_toy, conf = check_toy_color_heuristics(orange_patch)
    assert is_toy is True
    assert conf > 0.5

    # Patch with dark steel / black (real gun color)
    steel_patch = np.full((50, 50, 3), (35, 35, 35), dtype=np.uint8)
    is_toy_steel, _ = check_toy_color_heuristics(steel_patch)
    assert is_toy_steel is False


def test_categorize_detection():
    """Verify categorization outcomes for REAL_WEAPON, TOY_WEAPON, NO_WEAPON, and UNCERTAIN."""
    steel_patch = np.zeros((80, 80, 3), dtype=np.uint8)
    for y in range(80):
        for x in range(80):
            v = int(80 + 70 * np.sin(x / 8.0))
            steel_patch[y, x] = [v, v, v]

    # High confidence real weapon candidate
    cat_real = categorize_detection(raw_cls_id=0, raw_conf=0.85, cropped_bgr=steel_patch)
    assert cat_real["category"] == "REAL_WEAPON"
    assert cat_real["threat_level"] == "HIGH"

    # Borderline confidence real weapon -> UNCERTAIN
    cat_uncertain = categorize_detection(raw_cls_id=0, raw_conf=0.28, cropped_bgr=steel_patch)
    assert cat_uncertain["category"] == "UNCERTAIN"

    # Toy weapon class
    cat_toy = categorize_detection(raw_cls_id=1, raw_conf=0.75, cropped_bgr=steel_patch)
    assert cat_toy["category"] == "TOY_WEAPON"
    assert cat_toy["threat_level"] == "LOW"

    # Below threshold -> NO_WEAPON
    cat_none = categorize_detection(raw_cls_id=0, raw_conf=0.12, cropped_bgr=steel_patch, conf_threshold=0.20)
    assert cat_none["category"] == "NO_WEAPON"


def test_predict_image_execution():
    """Verify inference pipeline produces valid structured dictionary and runs without error."""
    detector = WeaponDetector.get_instance()
    sample_img = np.full((480, 640, 3), 40, dtype=np.uint8)
    # Add a mock line
    cv2.line(sample_img, (100, 100), (400, 300), (255, 255, 255), 3)

    result = detector.predict_image(sample_img, conf_threshold=0.20)
    assert result["status"] == "success"
    assert "detections" in result
    assert "processing_time_ms" in result
    assert result["image_size"] == [640, 480]

"""
Diagnostico - Deteccao do aro por CONTORNO
Aro = contorno grande (area >= 350) | Sem aro = contornos pequenos
"""
import sys
import os
import time
import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.screen_capture_obs import OBSScreenCapture


def load_config():
    import json
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'bot_settings.json')
    with open(config_path, 'r') as f:
        settings = json.load(f)
        target = settings.get("screen_regions", {}).get("target_hp", {})
        halo = settings.get("combat", {}).get("combat_halo_detection", {})
        return {
            "x": target.get("x", 1744),
            "y": target.get("y", 438),
            "width": target.get("width", 165),
            "height": target.get("height", 106)
        }, halo


def analyze_frame(img, cfg):
    """Detecta contornos grandes (aro de combate)"""
    hsv_ranges = cfg.get("hsv_ranges", {})
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Mascaras de cor
    r1 = hsv_ranges.get("red1", {})
    red_mask1 = cv2.inRange(hsv,
        np.array([r1.get("h_lower", 0), r1.get("s_lower", 100), r1.get("v_lower", 100)]),
        np.array([r1.get("h_upper", 10), r1.get("s_upper", 255), r1.get("v_upper", 255)]))

    og = hsv_ranges.get("orange", {})
    orange_mask = cv2.inRange(hsv,
        np.array([og.get("h_lower", 10), og.get("s_lower", 100), og.get("v_lower", 100)]),
        np.array([og.get("h_upper", 25), og.get("s_upper", 255), og.get("v_upper", 255)]))

    r2 = hsv_ranges.get("red2", {})
    red_mask2 = cv2.inRange(hsv,
        np.array([r2.get("h_lower", 170), r2.get("s_lower", 100), r2.get("v_lower", 100)]),
        np.array([r2.get("h_upper", 180), r2.get("s_upper", 255), r2.get("v_upper", 255)]))

    combat_mask = cv2.bitwise_or(red_mask1, cv2.bitwise_or(orange_mask, red_mask2))

    # Encontra contornos
    contours, _ = cv2.findContours(combat_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = cfg.get("min_contour_area", 350)

    detected = False
    max_area = 0

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > max_area:
            max_area = area
        if area >= min_area:
            detected = True

    return {
        "detected": detected,
        "max_area": max_area,
        "threshold": min_area,
        "mask": combat_mask
    }


def main():
    print("=" * 60)
    print("DIAGNOSTICO - ARO POR CONTORNO")
    print("=" * 60)
    print()
    print("Aro = contorno GRANDE | Sem aro = contornos pequenos")
    print()
    print("Pressione Ctrl+C para parar.")
    print("-" * 60)

    capture = OBSScreenCapture()
    if not capture.is_available():
        print("ERRO: OBS nao disponivel!")
        return

    battle_list, halo_cfg = load_config()

    threshold = halo_cfg.get("min_contour_area", 350)
    print(f"\nThreshold: area >= {threshold}")
    print()
    print("-" * 60)
    print(f"{'MAX_AREA':>10} | {'THRESHOLD':>10} | DETECTADO")
    print("-" * 60)

    try:
        while True:
            frame = capture.capture_fullscreen()
            if frame is None:
                time.sleep(0.1)
                continue

            x = battle_list["x"]
            y = battle_list["y"]
            w = battle_list["width"]
            h = battle_list["height"]

            img = frame[y:y+h, x:x+w].copy()
            result = analyze_frame(img, halo_cfg)

            status = "*** SIM ***" if result["detected"] else "nao"
            print(f"{result['max_area']:>10.0f} | {result['threshold']:>10} | {status}")

            time.sleep(0.3)

    except KeyboardInterrupt:
        print("\n\nDiagnostico finalizado!")
        print(f"\nRegra: Se MAX_AREA >= {threshold} = EM COMBATE")


if __name__ == "__main__":
    main()

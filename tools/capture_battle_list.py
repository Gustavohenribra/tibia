"""
Captura uma imagem da battle list para analise visual
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
        return {
            "x": target.get("x", 1744),
            "y": target.get("y", 438),
            "width": target.get("width", 165),
            "height": target.get("height", 106)
        }


def main():
    print("CAPTURA DA BATTLE LIST")
    print("=" * 50)

    capture = OBSScreenCapture()
    if not capture.is_available():
        print("ERRO: OBS nao disponivel!")
        return

    battle_list = load_config()
    print(f"Regiao: x={battle_list['x']}, y={battle_list['y']}, w={battle_list['width']}, h={battle_list['height']}")

    print("\nATAQUE UMA CRIATURA e pressione ENTER...")
    input()

    # Limpa cache
    for _ in range(5):
        capture.capture_fullscreen()
        time.sleep(0.1)

    print("Capturando...")
    time.sleep(0.3)

    frame = capture.capture_fullscreen()
    if frame is None:
        print("Falha na captura!")
        return

    x = battle_list["x"]
    y = battle_list["y"]
    w = battle_list["width"]
    h = battle_list["height"]

    # Captura regiao
    img = frame[y:y+h, x:x+w].copy()

    # Salva original
    cv2.imwrite("debug_battlelist_original.png", img)

    # Salva ampliado 3x
    zoomed = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite("debug_battlelist_zoomed.png", zoomed)

    # Cria mascara HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Mascara vermelho/laranja
    red1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
    orange = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([25, 255, 255]))
    red2 = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
    mask = cv2.bitwise_or(red1, cv2.bitwise_or(orange, red2))

    cv2.imwrite("debug_battlelist_mask.png", mask)

    # Mascara ampliada
    mask_zoomed = cv2.resize(mask, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite("debug_battlelist_mask_zoomed.png", mask_zoomed)

    # Fullscreen com retangulo
    frame_copy = frame.copy()
    cv2.rectangle(frame_copy, (x, y), (x+w, y+h), (0, 255, 0), 2)
    cv2.imwrite("debug_fullscreen_with_rect.png", frame_copy)

    print("\nImagens salvas:")
    print("  - debug_battlelist_original.png (regiao capturada)")
    print("  - debug_battlelist_zoomed.png (ampliado 3x)")
    print("  - debug_battlelist_mask.png (mascara vermelho/laranja)")
    print("  - debug_battlelist_mask_zoomed.png (mascara ampliada)")
    print("  - debug_fullscreen_with_rect.png (tela com retangulo)")
    print("\nEnvie as imagens para eu analisar!")


if __name__ == "__main__":
    main()

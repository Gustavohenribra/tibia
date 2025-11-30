"""
Teste rápido da detecção de halo com cores BGR
"""

import cv2
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from screen_capture_obs import OBSScreenCapture
import json

def main():
    # Carrega config
    with open("config/bot_settings.json", 'r') as f:
        settings = json.load(f)

    # Inicializa captura
    screen = OBSScreenCapture(camera_index=settings["obs_camera"]["device_index"])

    # Região da battle list (target_hp)
    region = settings["screen_regions"]["target_hp"]

    print("="*60)
    print("TESTE DE DETECÇÃO DE HALO (BGR)")
    print("="*60)
    print(f"Região: x={region['x']}, y={region['y']}, {region['width']}x{region['height']}")
    print("\nPressione 'q' para sair, 's' para salvar debug")
    print("="*60)

    # Config do halo
    halo_cfg = settings.get("combat", {}).get("combat_halo_detection", {})
    bgr_colors = halo_cfg.get("bgr_colors", [
        [0, 0, 255],
        [0, 0, 200],
        [0, 50, 255],
        [0, 100, 255],
        [0, 128, 255],
        [0, 165, 255]
    ])
    tolerance = halo_cfg.get("color_tolerance", 30)
    min_area = halo_cfg.get("min_contour_area", 350)

    print(f"\nCores BGR configuradas: {bgr_colors}")
    print(f"Tolerância: ±{tolerance}")
    print(f"Área mínima contorno: {min_area}")

    while True:
        # Captura
        img = screen.capture_region(
            x=region['x'], y=region['y'],
            width=region['width'], height=region['height']
        )

        if img is None:
            print("Falha na captura")
            continue

        # Cria máscara BGR
        mask = np.zeros(img.shape[:2], dtype=np.uint8)

        for bgr in bgr_colors:
            lower = np.array([max(0, c - tolerance) for c in bgr], dtype=np.uint8)
            upper = np.array([min(255, c + tolerance) for c in bgr], dtype=np.uint8)
            color_mask = cv2.inRange(img, lower, upper)
            mask = cv2.bitwise_or(mask, color_mask)

        # Encontra contornos
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Analisa contornos
        max_area = 0
        for c in contours:
            area = cv2.contourArea(c)
            if area > max_area:
                max_area = area

        # Resultado
        detected = max_area >= min_area
        status = "✅ ARO DETECTADO" if detected else "❌ SEM ARO"

        print(f"\r{status} | Max área: {max_area:>5.0f} (min: {min_area}) | Pixels brancos: {cv2.countNonZero(mask):>5}", end="")

        # Visualização
        display = img.copy()
        cv2.drawContours(display, contours, -1, (0, 255, 0), 1)

        # Amplia para visualização
        display = cv2.resize(display, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
        mask_display = cv2.resize(mask, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)

        cv2.imshow("Battle List", display)
        cv2.imshow("Mascara BGR", mask_display)

        key = cv2.waitKey(100) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite("debug_halo_test_original.png", img)
            cv2.imwrite("debug_halo_test_mask.png", mask)
            print("\n💾 Imagens salvas!")

            # Analisa cores presentes na imagem
            print("\n📊 Cores mais comuns na imagem (BGR):")
            # Flatten e conta cores únicas
            pixels = img.reshape(-1, 3)
            unique, counts = np.unique(pixels, axis=0, return_counts=True)
            # Top 10 cores mais comuns
            top_idx = np.argsort(counts)[-10:][::-1]
            for i in top_idx:
                bgr = unique[i]
                count = counts[i]
                print(f"  BGR{tuple(bgr)}: {count} pixels")

    cv2.destroyAllWindows()
    print("\n\nFim do teste")

if __name__ == "__main__":
    main()

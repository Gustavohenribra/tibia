"""
Teste de deteccao do aro de combate
Captura frames da OBS e testa a nova logica de deteccao
"""
import sys
import os
import time
import cv2
import numpy as np

# Adiciona diretorio src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.screen_capture_obs import OBSScreenCapture
from src.ocr_reader import OCRReader


def load_battle_list_coords():
    """Carrega coordenadas da battle list do bot_settings.json"""
    import json
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'bot_settings.json')
    try:
        with open(config_path, 'r') as f:
            settings = json.load(f)
            target = settings.get("screen_regions", {}).get("target_hp", {})
            return {
                "x": target.get("x", 1744),
                "y": target.get("y", 438),
                "width": target.get("width", 165),
                "height": target.get("height", 106)
            }
    except:
        return {"x": 1744, "y": 438, "width": 165, "height": 106}


def analyze_detection(img, ocr_reader):
    """Analisa deteccao e mostra detalhes"""
    if img is None:
        return

    # Usa a funcao de deteccao
    result = ocr_reader.detect_active_combat(img)

    # Analisa detalhes para debug
    cfg = ocr_reader._halo_config
    hsv_ranges = cfg.get("hsv_ranges", {})

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, w = hsv.shape[:2]

    # Recria mascaras para analise
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

    border_thickness = cfg.get("border_thickness", 4)

    # Extrai regioes
    top_border = combat_mask[0:border_thickness, :]
    bottom_border = combat_mask[h-border_thickness:h, :]
    left_border = combat_mask[:, 0:border_thickness]
    right_border = combat_mask[:, w-border_thickness:w]
    center = combat_mask[border_thickness:h-border_thickness, border_thickness:w-border_thickness]

    # Conta pixels
    border_pixels = (cv2.countNonZero(top_border) + cv2.countNonZero(bottom_border) +
                    cv2.countNonZero(left_border) + cv2.countNonZero(right_border))
    center_pixels = cv2.countNonZero(center)

    # Calcula areas
    total_border_area = (h * border_thickness * 2) + ((w - 2*border_thickness) * border_thickness * 2)
    total_center_area = (h - 2*border_thickness) * (w - 2*border_thickness)

    border_density = (border_pixels / total_border_area) * 100 if total_border_area > 0 else 0
    center_density = (center_pixels / total_center_area) * 100 if total_center_area > 0 else 0

    if center_density > 0.1:
        ratio = border_density / center_density
    else:
        ratio = border_density * 10 if border_density > 0 else 0

    print(f"\n   === ANALISE DE DETECCAO ===")
    print(f"   Pixels nas bordas: {border_pixels} ({border_density:.2f}%)")
    print(f"   Pixels no centro:  {center_pixels} ({center_density:.2f}%)")
    print(f"   Razao borda/centro: {ratio:.2f}")
    print(f"   Thresholds: border>{cfg.get('border_density_threshold', 5.0)}% AND ratio>{cfg.get('ratio_threshold', 1.5)}")
    print(f"   ")
    if result:
        print(f"   RESULTADO: *** EM COMBATE ATIVO (aro detectado) ***")
    else:
        print(f"   RESULTADO: Sem aro de combate")

    return result, combat_mask


def main():
    print("=" * 60)
    print("TESTE DE DETECCAO DO ARO DE COMBATE")
    print("=" * 60)

    # Inicializa
    capture = OBSScreenCapture()
    ocr_reader = OCRReader()
    battle_list = load_battle_list_coords()

    if not capture.is_available():
        print("ERRO: OBS nao disponivel!")
        return

    print("OBS conectado!")
    print(f"Battle List: {battle_list}")
    print()
    print("Pressione ENTER para capturar, 'q' para sair")
    print("-" * 60)

    while True:
        user_input = input("\n[ENTER para capturar, 'q' para sair]: ").strip().lower()

        if user_input == 'q':
            break

        # Limpa cache
        for _ in range(3):
            capture.capture_fullscreen()
            time.sleep(0.05)

        # Captura
        frame = capture.capture_fullscreen()
        if frame is None:
            print("Falha na captura!")
            continue

        x = battle_list["x"]
        y = battle_list["y"]
        w = battle_list["width"]
        h = battle_list["height"]

        battle_list_img = frame[y:y+h, x:x+w].copy()

        # Analisa
        result, mask = analyze_detection(battle_list_img, ocr_reader)

        # Salva imagens de debug
        cv2.imwrite("debug_test_capture.png", battle_list_img)
        cv2.imwrite("debug_test_mask.png", mask)

        # Salva versao ampliada
        zoomed = cv2.resize(battle_list_img, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
        cv2.imwrite("debug_test_capture_zoomed.png", zoomed)

        mask_zoomed = cv2.resize(mask, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
        cv2.imwrite("debug_test_mask_zoomed.png", mask_zoomed)

        print(f"\n   Imagens salvas:")
        print(f"     - debug_test_capture.png")
        print(f"     - debug_test_mask.png")
        print(f"     - debug_test_capture_zoomed.png")

    print("\nTeste finalizado!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado")
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

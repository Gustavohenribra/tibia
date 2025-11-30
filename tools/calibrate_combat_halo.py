"""
Ferramenta de calibracao do Aro de Combate (Combat Halo)
Captura e analisa as cores do aro vermelho/laranja pulsante na battle list
"""
import sys
import os
import time
import cv2
import numpy as np

# Adiciona diretorio src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.screen_capture_obs import OBSScreenCapture


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


BATTLE_LIST = load_battle_list_coords()


def countdown(seconds):
    """Contagem regressiva visual"""
    for i in range(seconds, 0, -1):
        print(f"   Capturando em {i}...", end='\r', flush=True)
        time.sleep(1)
    print("   CAPTURANDO AGORA!       ")


def capture_battle_list(capture):
    """Captura regiao da battle list e retorna tanto o recorte quanto o fullscreen"""
    frame = capture.capture_fullscreen()

    if frame is None:
        return None, None

    x = BATTLE_LIST["x"]
    y = BATTLE_LIST["y"]
    w = BATTLE_LIST["width"]
    h = BATTLE_LIST["height"]

    # Verifica se coordenadas estao dentro dos limites
    if (y + h > frame.shape[0] or x + w > frame.shape[1] or y < 0 or x < 0):
        print(f"   AVISO: Coordenadas fora dos limites da tela!")
        print(f"   Tela: {frame.shape[1]}x{frame.shape[0]}")
        print(f"   Battle List: ({x},{y}) - ({x+w},{y+h})")
        return None, None

    battle_list_img = frame[y:y+h, x:x+w]

    return battle_list_img.copy(), frame.copy()


def draw_rectangle_on_screen(fullscreen_img):
    """Desenha retangulo mostrando area capturada"""
    img_copy = fullscreen_img.copy()

    x = BATTLE_LIST["x"]
    y = BATTLE_LIST["y"]
    w = BATTLE_LIST["width"]
    h = BATTLE_LIST["height"]

    # Desenha retangulo verde
    cv2.rectangle(img_copy, (x, y), (x+w, y+h), (0, 255, 0), 2)

    # Adiciona texto
    cv2.putText(img_copy, "BATTLE LIST",
               (x - 10, y - 10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return img_copy


def analyze_halo_colors(img, state_name):
    """Analisa cores da imagem focando em vermelho/laranja do aro"""
    print(f"\n   Analise de cores - Estado {state_name}:")
    print(f"   Dimensoes: {img.shape[1]}x{img.shape[0]} pixels ({img.shape[0] * img.shape[1]} pixels totais)")

    # Converte para HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Calcula medias
    avg_bgr = np.mean(img, axis=(0, 1))
    avg_hsv = np.mean(hsv, axis=(0, 1))

    print(f"   Media BGR: B={avg_bgr[0]:.1f} G={avg_bgr[1]:.1f} R={avg_bgr[2]:.1f}")
    print(f"   Media HSV: H={avg_hsv[0]:.1f} S={avg_hsv[1]:.1f} V={avg_hsv[2]:.1f}")

    # Verifica presenca de cores especificas
    print("\n   Deteccao de cores:")
    check_color_presence(hsv, "Vermelho Puro", [0, 100, 100], [10, 255, 255])
    check_color_presence(hsv, "Laranja     ", [10, 100, 100], [25, 255, 255])
    check_color_presence(hsv, "Verm. Escuro", [170, 100, 100], [180, 255, 255])
    check_color_presence(hsv, "Verde       ", [35, 80, 80], [85, 255, 255])

    return hsv


def check_color_presence(hsv, color_name, lower, upper):
    """Verifica quantos pixels de uma cor especifica existem"""
    mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
    count = cv2.countNonZero(mask)
    total = hsv.shape[0] * hsv.shape[1]
    percent = (count / total) * 100

    status = ""
    if percent > 10:
        status = "ALTO"
    elif percent > 2:
        status = "MEDIO"
    elif percent > 0.5:
        status = "BAIXO"
    else:
        status = "AUSENTE"

    print(f"   {color_name}: {count:4d}/{total} pixels ({percent:5.2f}%) {status}")
    return count, percent


def analyze_spatial_distribution(img, state_name):
    """Analisa distribuicao espacial dos pixels vermelho/laranja (bordas vs centro)"""
    print(f"\n   Distribuicao Espacial - {state_name}:")

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, w = hsv.shape[:2]

    # Cria mascara combinada vermelho/laranja
    red_mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
    orange_mask = cv2.inRange(hsv, np.array([10, 100, 100]), np.array([25, 255, 255]))
    red_mask2 = cv2.inRange(hsv, np.array([170, 100, 100]), np.array([180, 255, 255]))
    combined_mask = cv2.bitwise_or(red_mask1, cv2.bitwise_or(orange_mask, red_mask2))

    # Define espessura da borda para analise
    border_thickness = 4

    # Extrai regioes de borda
    top_border = combined_mask[0:border_thickness, :]
    bottom_border = combined_mask[h-border_thickness:h, :]
    left_border = combined_mask[:, 0:border_thickness]
    right_border = combined_mask[:, w-border_thickness:w]

    # Extrai regiao central
    center = combined_mask[border_thickness:h-border_thickness, border_thickness:w-border_thickness]

    # Conta pixels em cada regiao
    top_pixels = cv2.countNonZero(top_border)
    bottom_pixels = cv2.countNonZero(bottom_border)
    left_pixels = cv2.countNonZero(left_border)
    right_pixels = cv2.countNonZero(right_border)
    center_pixels = cv2.countNonZero(center)

    border_pixels = top_pixels + bottom_pixels + left_pixels + right_pixels

    # Calcula areas
    total_border_area = (h * border_thickness * 2) + ((w - 2*border_thickness) * border_thickness * 2)
    total_center_area = (h - 2*border_thickness) * (w - 2*border_thickness)

    border_density = (border_pixels / total_border_area) * 100 if total_border_area > 0 else 0
    center_density = (center_pixels / total_center_area) * 100 if total_center_area > 0 else 0

    print(f"   Espessura da borda analisada: {border_thickness} pixels")
    print(f"   ")
    print(f"   Pixels nas BORDAS:")
    print(f"     - Topo:     {top_pixels:4d} pixels")
    print(f"     - Base:     {bottom_pixels:4d} pixels")
    print(f"     - Esquerda: {left_pixels:4d} pixels")
    print(f"     - Direita:  {right_pixels:4d} pixels")
    print(f"     - TOTAL:    {border_pixels:4d} pixels ({border_density:.2f}% densidade)")
    print(f"   ")
    print(f"   Pixels no CENTRO:")
    print(f"     - TOTAL:    {center_pixels:4d} pixels ({center_density:.2f}% densidade)")
    print(f"   ")

    # Calcula razao
    if center_density > 0:
        ratio = border_density / center_density
    else:
        ratio = border_density * 100 if border_density > 0 else 0

    print(f"   RAZAO Borda/Centro: {ratio:.2f}")

    if ratio > 2.0 and border_density > 5:
        print(f"   RESULTADO: ARO DETECTADO (bordas >> centro)")
    elif center_density > border_density:
        print(f"   RESULTADO: CRIATURA VERMELHA (centro >> bordas)")
    else:
        print(f"   RESULTADO: INCONCLUSIVO")

    # Salva mascara de debug
    debug_mask = cv2.cvtColor(combined_mask, cv2.COLOR_GRAY2BGR)
    # Marca bordas em verde para visualizacao
    debug_mask[0:border_thickness, :] = [0, 255, 0] if top_pixels > 0 else debug_mask[0:border_thickness, :]
    debug_mask[h-border_thickness:h, :] = [0, 255, 0] if bottom_pixels > 0 else debug_mask[h-border_thickness:h, :]

    return {
        "border_pixels": border_pixels,
        "center_pixels": center_pixels,
        "border_density": border_density,
        "center_density": center_density,
        "ratio": ratio,
        "mask": combined_mask
    }


def save_debug_images(img, mask, prefix, state):
    """Salva imagens de debug"""
    # Original
    cv2.imwrite(f"debug_halo_{prefix}.png", img)

    # Mascara
    cv2.imwrite(f"debug_halo_{prefix}_mask.png", mask)

    # Ampliado 3x
    zoomed = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(f"debug_halo_{prefix}_zoomed.png", zoomed)

    # Mascara ampliada
    mask_zoomed = cv2.resize(mask, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(f"debug_halo_{prefix}_mask_zoomed.png", mask_zoomed)

    print(f"   Imagens salvas:")
    print(f"     - debug_halo_{prefix}.png")
    print(f"     - debug_halo_{prefix}_mask.png")
    print(f"     - debug_halo_{prefix}_zoomed.png")


def recommend_config(no_halo_result, with_halo_result):
    """Gera recomendacoes de configuracao baseadas nas capturas"""
    print("\n" + "=" * 60)
    print("CONFIGURACOES RECOMENDADAS")
    print("=" * 60)

    # Analisa os resultados
    halo_border = with_halo_result["border_density"] if with_halo_result else 0
    halo_center = with_halo_result["center_density"] if with_halo_result else 0
    no_halo_border = no_halo_result["border_density"] if no_halo_result else 0
    no_halo_center = no_halo_result["center_density"] if no_halo_result else 0

    print(f"\n   Comparativo:")
    print(f"   {'Estado':<20} {'Borda %':<12} {'Centro %':<12} {'Razao':<10}")
    print(f"   {'-'*54}")
    if no_halo_result:
        print(f"   {'SEM aro':<20} {no_halo_border:<12.2f} {no_halo_center:<12.2f} {no_halo_result['ratio']:<10.2f}")
    if with_halo_result:
        print(f"   {'COM aro':<20} {halo_border:<12.2f} {halo_center:<12.2f} {with_halo_result['ratio']:<10.2f}")

    # Sugere thresholds
    print(f"\n   Thresholds sugeridos:")

    # Border density threshold: entre sem aro e com aro
    if halo_border > 0 and no_halo_border >= 0:
        suggested_border_threshold = (halo_border + no_halo_border) / 2
        suggested_border_threshold = max(5.0, suggested_border_threshold)  # Minimo 5%
    else:
        suggested_border_threshold = 10.0

    # Ratio threshold
    if with_halo_result and with_halo_result["ratio"] > 0:
        suggested_ratio = max(1.5, with_halo_result["ratio"] * 0.7)
    else:
        suggested_ratio = 2.0

    print(f"     - border_density_threshold: {suggested_border_threshold:.1f}%")
    print(f"     - ratio_threshold: {suggested_ratio:.1f}")

    print(f"\n   Configuracao para bot_settings.json:\n")
    print('"combat_halo_detection": {')
    print('    "_comment": "Configuracao de deteccao do aro de combate",')
    print('    "enabled": true,')
    print('    "border_thickness": 4,')
    print(f'    "border_density_threshold": {suggested_border_threshold:.1f},')
    print(f'    "ratio_threshold": {suggested_ratio:.1f},')
    print('    "hsv_ranges": {')
    print('        "red1": {"h_lower": 0, "h_upper": 10, "s_lower": 100, "s_upper": 255, "v_lower": 100, "v_upper": 255},')
    print('        "orange": {"h_lower": 10, "h_upper": 25, "s_lower": 100, "s_upper": 255, "v_lower": 100, "v_upper": 255},')
    print('        "red2": {"h_lower": 170, "h_upper": 180, "s_lower": 100, "s_upper": 255, "v_lower": 100, "v_upper": 255}')
    print('    }')
    print('}')


def main():
    print("=" * 60)
    print("CALIBRACAO DO ARO DE COMBATE (COMBAT HALO)")
    print("=" * 60)
    print()
    print("Esta ferramenta analisa o aro vermelho/laranja pulsante")
    print("que aparece ao redor de criaturas selecionadas na battle list.")
    print()
    print(f"Coordenadas da Battle List (de bot_settings.json):")
    print(f"  Superior esquerdo: ({BATTLE_LIST['x']}, {BATTLE_LIST['y']})")
    print(f"  Dimensoes: {BATTLE_LIST['width']}x{BATTLE_LIST['height']} pixels")
    print()

    # Inicializa captura OBS
    print("Inicializando OBS Screen Capture...")
    capture = OBSScreenCapture()

    if not capture.is_available():
        print("ERRO: OBS nao esta disponivel!")
        print("Certifique-se de que:")
        print("  1. OBS Studio esta aberto")
        print("  2. Virtual Camera esta ativa")
        return

    print("OBS conectado com sucesso!")
    print()

    no_halo_result = None
    with_halo_result = None

    # Menu de opcoes
    while True:
        print("\n" + "-" * 60)
        print("OPCOES:")
        print("  1. Capturar SEM aro (criatura nao selecionada)")
        print("  2. Capturar COM aro (criatura selecionada/atacando)")
        print("  3. Capturar criatura VERMELHA (para teste de falso positivo)")
        print("  4. Ver recomendacoes de configuracao")
        print("  5. Sair")
        print("-" * 60)

        choice = input("Escolha uma opcao (1-5): ").strip()

        if choice == "1":
            print("\n" + "-" * 60)
            print("CAPTURA SEM ARO")
            print("-" * 60)
            print("Certifique-se de que NENHUMA criatura esta selecionada")
            print("(Nao deve haver aro vermelho na battle list)")
            print()
            input("Pressione ENTER quando estiver pronto...")

            # Limpa cache
            print("Limpando cache do OBS...")
            for _ in range(5):
                capture.capture_fullscreen()
                time.sleep(0.1)

            countdown(3)

            img, fullscreen = capture_battle_list(capture)
            if img is not None:
                analyze_halo_colors(img, "SEM ARO")
                no_halo_result = analyze_spatial_distribution(img, "SEM ARO")

                # Salva imagens
                cv2.imwrite("debug_halo_no_halo_fullscreen.png", draw_rectangle_on_screen(fullscreen))
                save_debug_images(img, no_halo_result["mask"], "no_halo", "SEM ARO")
                print("\n   Captura SEM aro concluida!")
            else:
                print("   Falha na captura!")

        elif choice == "2":
            print("\n" + "-" * 60)
            print("CAPTURA COM ARO")
            print("-" * 60)
            print("Selecione uma criatura para atacar")
            print("(Deve aparecer o aro vermelho/laranja pulsante)")
            print()
            input("Pressione ENTER quando estiver ATACANDO uma criatura...")

            # Limpa cache
            print("Limpando cache do OBS...")
            for _ in range(5):
                capture.capture_fullscreen()
                time.sleep(0.1)

            countdown(3)

            img, fullscreen = capture_battle_list(capture)
            if img is not None:
                analyze_halo_colors(img, "COM ARO")
                with_halo_result = analyze_spatial_distribution(img, "COM ARO")

                # Salva imagens
                cv2.imwrite("debug_halo_with_halo_fullscreen.png", draw_rectangle_on_screen(fullscreen))
                save_debug_images(img, with_halo_result["mask"], "with_halo", "COM ARO")
                print("\n   Captura COM aro concluida!")
            else:
                print("   Falha na captura!")

        elif choice == "3":
            print("\n" + "-" * 60)
            print("CAPTURA CRIATURA VERMELHA")
            print("-" * 60)
            print("Posicione uma criatura VERMELHA na battle list")
            print("mas NAO selecione ela (sem aro)")
            print("(Teste para verificar falso positivo)")
            print()
            input("Pressione ENTER quando estiver pronto...")

            # Limpa cache
            print("Limpando cache do OBS...")
            for _ in range(5):
                capture.capture_fullscreen()
                time.sleep(0.1)

            countdown(3)

            img, fullscreen = capture_battle_list(capture)
            if img is not None:
                analyze_halo_colors(img, "CRIATURA VERMELHA")
                red_creature_result = analyze_spatial_distribution(img, "CRIATURA VERMELHA")

                # Salva imagens
                cv2.imwrite("debug_halo_red_creature_fullscreen.png", draw_rectangle_on_screen(fullscreen))
                save_debug_images(img, red_creature_result["mask"], "red_creature", "CRIATURA VERMELHA")

                # Analisa se seria falso positivo
                print("\n   ANALISE DE FALSO POSITIVO:")
                if red_creature_result["ratio"] > 2.0 and red_creature_result["border_density"] > 10:
                    print("   ALERTA: Esta criatura SERIA detectada como aro!")
                    print("   Ajuste os thresholds para evitar falso positivo.")
                else:
                    print("   OK: Esta criatura NAO seria detectada como aro.")
            else:
                print("   Falha na captura!")

        elif choice == "4":
            if no_halo_result or with_halo_result:
                recommend_config(no_halo_result, with_halo_result)
            else:
                print("\n   Faca pelo menos uma captura primeiro!")

        elif choice == "5":
            print("\nSaindo...")
            break

        else:
            print("Opcao invalida!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCalibracao cancelada pelo usuario")
    except Exception as e:
        print(f"\n\nERRO: {e}")
        import traceback
        traceback.print_exc()

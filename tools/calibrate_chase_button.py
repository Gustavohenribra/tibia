"""
Ferramenta de calibração do botão Chase
Captura e analisa as cores do botão chase para configurar detecção
"""
import sys
import os
import time
import cv2
import numpy as np

# Adiciona diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.screen_capture_obs import OBSScreenCapture

# Coordenadas do botão chase (carrega do config)
def load_chase_coords():
    """Carrega coordenadas do bot_settings.json"""
    import json
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'bot_settings.json')
    try:
        with open(config_path, 'r') as f:
            settings = json.load(f)
            chase_btn = settings.get("combat", {}).get("chase_button", {})
            return (
                chase_btn.get("x1", 1892),
                chase_btn.get("y1", 163),
                chase_btn.get("x2", 1911),
                chase_btn.get("y2", 186)
            )
    except:
        return (1892, 163, 1911, 186)

CHASE_BUTTON_X1, CHASE_BUTTON_Y1, CHASE_BUTTON_X2, CHASE_BUTTON_Y2 = load_chase_coords()

def countdown(seconds):
    """Contagem regressiva visual"""
    for i in range(seconds, 0, -1):
        print(f"   Capturando em {i}...", end='\r', flush=True)
        time.sleep(1)
    print("   📸 CAPTURANDO AGORA!       ")

def main():
    print("=" * 60)
    print("CALIBRAÇÃO DO BOTÃO CHASE")
    print("=" * 60)
    print()
    print("Esta ferramenta irá capturar o botão chase em dois estados:")
    print("1. INATIVO (cinza/branco) - quando chase mode está desligado")
    print("2. ATIVO (verde) - quando chase mode está ligado")
    print()
    print(f"Coordenadas do botão (de bot_settings.json):")
    print(f"  Superior esquerdo: ({CHASE_BUTTON_X1}, {CHASE_BUTTON_Y1})")
    print(f"  Inferior direito: ({CHASE_BUTTON_X2}, {CHASE_BUTTON_Y2})")
    print(f"  Dimensões: {CHASE_BUTTON_X2 - CHASE_BUTTON_X1}x{CHASE_BUTTON_Y2 - CHASE_BUTTON_Y1} pixels")
    print()

    # Inicializa captura OBS
    print("Inicializando OBS Screen Capture...")
    capture = OBSScreenCapture()

    if not capture.is_available():
        print("❌ ERRO: OBS não está disponível!")
        print("Certifique-se de que:")
        print("  1. OBS Studio está instalado")
        print("  2. obs-websocket plugin está instalado")
        print("  3. OBS está aberto e rodando")
        return

    print("✅ OBS conectado com sucesso!")
    print()

    # Captura botão INATIVO
    print("-" * 60)
    print("PASSO 1: Capturar botão INATIVO")
    print("-" * 60)
    print("🔴 DESATIVE o chase mode no Tibia")
    print("   (Se já estiver desativado, apenas aguarde)")
    print()
    input("Pressione ENTER quando o chase estiver DESATIVADO...")
    print()

    # Limpa cache do OBS fazendo várias capturas dummy
    print("🔄 Limpando cache do OBS...")
    for i in range(5):
        capture.capture_fullscreen()
        time.sleep(0.1)

    countdown(3)

    print("📸 Capturando frame INATIVO agora...")
    time.sleep(0.2)
    inactive_capture, inactive_fullscreen = capture_chase_button(capture)

    if inactive_capture is None:
        print("❌ Falha ao capturar botão inativo!")
        return

    # Salva imagens
    cv2.imwrite("debug_chase_inactive.png", inactive_capture)
    cv2.imwrite("debug_chase_inactive_fullscreen.png", draw_rectangle_on_screen(inactive_fullscreen))

    # Amplia para visualização (10x)
    zoomed = cv2.resize(inactive_capture, None, fx=10, fy=10, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite("debug_chase_inactive_zoomed.png", zoomed)

    analyze_colors(inactive_capture, "INATIVO")
    print("💾 Imagens salvas:")
    print("   - debug_chase_inactive.png (original)")
    print("   - debug_chase_inactive_zoomed.png (ampliado 10x)")
    print("   - debug_chase_inactive_fullscreen.png (tela com retângulo)")
    print()

    # Captura botão ATIVO
    print("-" * 60)
    print("PASSO 2: Capturar botão ATIVO")
    print("-" * 60)
    print("🟢 ATIVE o chase mode no Tibia")
    print("   (Pressione K para ativar)")
    print()
    input("Pressione ENTER quando o chase estiver ATIVADO (verde)...")
    print()

    # Limpa cache do OBS fazendo várias capturas dummy
    print("🔄 Limpando cache do OBS...")
    for i in range(5):
        capture.capture_fullscreen()
        time.sleep(0.1)

    countdown(3)

    print("📸 Capturando frame ATIVO agora...")
    time.sleep(0.2)
    active_capture, active_fullscreen = capture_chase_button(capture)

    if active_capture is None:
        print("❌ Falha ao capturar botão ativo!")
        return

    # Salva imagens
    cv2.imwrite("debug_chase_active.png", active_capture)
    cv2.imwrite("debug_chase_active_fullscreen.png", draw_rectangle_on_screen(active_fullscreen))

    # Amplia para visualização (10x)
    zoomed = cv2.resize(active_capture, None, fx=10, fy=10, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite("debug_chase_active_zoomed.png", zoomed)

    analyze_colors(active_capture, "ATIVO")
    print("💾 Imagens salvas:")
    print("   - debug_chase_active.png (original)")
    print("   - debug_chase_active_zoomed.png (ampliado 10x)")
    print("   - debug_chase_active_fullscreen.png (tela com retângulo)")
    print()

    # Análise comparativa
    print("=" * 60)
    print("ANÁLISE COMPARATIVA")
    print("=" * 60)
    compare_states(inactive_capture, active_capture)

    # Recomendações
    print()
    print("=" * 60)
    print("CONFIGURAÇÕES RECOMENDADAS")
    print("=" * 60)
    recommend_config(inactive_capture, active_capture)

def draw_rectangle_on_screen(fullscreen_img):
    """Desenha retângulo mostrando área capturada"""
    img_copy = fullscreen_img.copy()

    # Desenha retângulo vermelho
    cv2.rectangle(img_copy,
                 (CHASE_BUTTON_X1, CHASE_BUTTON_Y1),
                 (CHASE_BUTTON_X2, CHASE_BUTTON_Y2),
                 (0, 0, 255), 2)

    # Adiciona texto
    cv2.putText(img_copy, "CHASE BUTTON",
               (CHASE_BUTTON_X1 - 100, CHASE_BUTTON_Y1 - 10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    return img_copy

def capture_chase_button(capture):
    """Captura região do botão chase e retorna tanto o recorte quanto o fullscreen"""
    frame = capture.capture_fullscreen()

    if frame is None:
        return None, None

    width = CHASE_BUTTON_X2 - CHASE_BUTTON_X1
    height = CHASE_BUTTON_Y2 - CHASE_BUTTON_Y1

    # Verifica se coordenadas estão dentro dos limites
    if (CHASE_BUTTON_Y2 > frame.shape[0] or CHASE_BUTTON_X2 > frame.shape[1] or
        CHASE_BUTTON_Y1 < 0 or CHASE_BUTTON_X1 < 0):
        print(f"⚠️  AVISO: Coordenadas fora dos limites da tela!")
        print(f"   Tela: {frame.shape[1]}x{frame.shape[0]}")
        print(f"   Botão: ({CHASE_BUTTON_X1},{CHASE_BUTTON_Y1}) - ({CHASE_BUTTON_X2},{CHASE_BUTTON_Y2})")
        return None, None

    button_img = frame[CHASE_BUTTON_Y1:CHASE_BUTTON_Y2, CHASE_BUTTON_X1:CHASE_BUTTON_X2]

    return button_img.copy(), frame.copy()

def analyze_colors(img, state_name):
    """Analisa cores da imagem e mostra estatísticas"""
    print(f"\n📊 Análise de cores - Estado {state_name}:")
    print(f"   Dimensões: {img.shape[1]}x{img.shape[0]} pixels ({img.shape[0] * img.shape[1]} pixels totais)")

    # Converte para HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Calcula médias
    avg_bgr = np.mean(img, axis=(0, 1))
    avg_hsv = np.mean(hsv, axis=(0, 1))

    print(f"   Média BGR: B={avg_bgr[0]:.1f} G={avg_bgr[1]:.1f} R={avg_bgr[2]:.1f}")
    print(f"   Média HSV: H={avg_hsv[0]:.1f} S={avg_hsv[1]:.1f} V={avg_hsv[2]:.1f}")

    # Verifica presença de cores específicas
    check_color_presence(hsv, "Verde", [35, 80, 80], [85, 255, 255])
    check_color_presence(hsv, "Cinza", [0, 0, 100], [180, 30, 200])
    check_color_presence(hsv, "Branco", [0, 0, 200], [180, 30, 255])
    check_color_presence(hsv, "Preto", [0, 0, 0], [180, 255, 50])

def check_color_presence(hsv, color_name, lower, upper):
    """Verifica quantos pixels de uma cor específica existem"""
    mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
    count = cv2.countNonZero(mask)
    total = hsv.shape[0] * hsv.shape[1]
    percent = (count / total) * 100

    status = ""
    if percent > 50:
        status = "✅ DOMINANTE"
    elif percent > 10:
        status = "🟡 PRESENTE"
    elif percent > 0:
        status = "⚪ TRAÇOS"
    else:
        status = "❌ AUSENTE"

    print(f"   {color_name:8s}: {count:4d}/{total} pixels ({percent:5.1f}%) {status}")

def compare_states(inactive_img, active_img):
    """Compara os dois estados e identifica diferenças"""
    # Diferença absoluta
    diff = cv2.absdiff(inactive_img, active_img)
    diff_score = np.mean(diff)

    print(f"\n📈 Diferença média entre estados: {diff_score:.2f}")

    if diff_score < 10:
        print("   ⚠️  ATENÇÃO: Diferença muito pequena! As imagens podem ser iguais.")
        print("   Verifique se você realmente mudou o estado do chase entre as capturas.")

    # Salva imagem de diferença
    cv2.imwrite("debug_chase_diff.png", diff * 5)  # Amplifica para visualização

    # Ampliada
    diff_zoomed = cv2.resize(diff * 5, None, fx=10, fy=10, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite("debug_chase_diff_zoomed.png", diff_zoomed)

    print("💾 Imagem de diferença salva: debug_chase_diff.png e debug_chase_diff_zoomed.png")

    # Converte para HSV e analisa diferenças
    hsv_inactive = cv2.cvtColor(inactive_img, cv2.COLOR_BGR2HSV)
    hsv_active = cv2.cvtColor(active_img, cv2.COLOR_BGR2HSV)

    avg_h_inactive = np.mean(hsv_inactive[:, :, 0])
    avg_h_active = np.mean(hsv_active[:, :, 0])

    print(f"\n   Hue (Matiz) médio:")
    print(f"   - Inativo: {avg_h_inactive:.1f}°")
    print(f"   - Ativo: {avg_h_active:.1f}°")
    print(f"   - Diferença: {abs(avg_h_active - avg_h_inactive):.1f}°")

def recommend_config(inactive_img, active_img):
    """Gera recomendações de configuração baseadas nas capturas"""
    hsv_active = cv2.cvtColor(active_img, cv2.COLOR_BGR2HSV)

    # Calcula range de verde no estado ativo
    h_mean = float(np.mean(hsv_active[:, :, 0]))
    s_mean = float(np.mean(hsv_active[:, :, 1]))
    v_mean = float(np.mean(hsv_active[:, :, 2]))

    h_std = float(np.std(hsv_active[:, :, 0]))
    s_std = float(np.std(hsv_active[:, :, 1]))
    v_std = float(np.std(hsv_active[:, :, 2]))

    # Define ranges com margem (garante valores válidos entre 0-180 para H e 0-255 para S/V)
    h_lower = int(max(0, min(180, h_mean - 2 * h_std)))
    h_upper = int(max(0, min(180, h_mean + 2 * h_std)))
    s_lower = int(max(0, min(255, s_mean - 2 * s_std)))
    s_upper = int(max(0, min(255, s_mean + 2 * s_std)))
    v_lower = int(max(0, min(255, v_mean - 2 * v_std)))
    v_upper = int(max(0, min(255, v_mean + 2 * v_std)))

    # Garante que upper >= lower
    if h_upper <= h_lower:
        h_upper = h_lower + 1
    if s_upper <= s_lower:
        s_upper = s_lower + 1
    if v_upper <= v_lower:
        v_upper = v_lower + 1

    print("\n🎯 Configurações sugeridas para bot_settings.json:\n")
    print('"chase_button": {')
    print('    "_comment": "Coordenadas e configuração de detecção do botão chase",')
    print(f'    "x1": {CHASE_BUTTON_X1},')
    print(f'    "y1": {CHASE_BUTTON_Y1},')
    print(f'    "x2": {CHASE_BUTTON_X2},')
    print(f'    "y2": {CHASE_BUTTON_Y2},')
    print('    "active_color_range": {')
    print('        "_comment": "Range HSV para detectar verde (chase ativo). Use tools/calibrate_chase_button.py para calibrar",')
    print(f'        "h_lower": {h_lower},')
    print(f'        "h_upper": {h_upper},')
    print(f'        "s_lower": {s_lower},')
    print(f'        "s_upper": {s_upper},')
    print(f'        "v_lower": {v_lower},')
    print(f'        "v_upper": {v_upper}')
    print('    },')
    print('    "active_threshold_percent": 10.0')
    print('}')

    # Teste as configurações
    print("\n🧪 Testando configurações sugeridas...")

    # Cria arrays com tipo correto (uint8)
    lower_bound = np.array([h_lower, s_lower, v_lower], dtype=np.uint8)
    upper_bound = np.array([h_upper, s_upper, v_upper], dtype=np.uint8)

    active_mask = cv2.inRange(hsv_active, lower_bound, upper_bound)
    active_percent = (cv2.countNonZero(active_mask) / (hsv_active.shape[0] * hsv_active.shape[1])) * 100

    hsv_inactive = cv2.cvtColor(inactive_img, cv2.COLOR_BGR2HSV)
    inactive_mask = cv2.inRange(hsv_inactive, lower_bound, upper_bound)
    inactive_percent = (cv2.countNonZero(inactive_mask) / (hsv_inactive.shape[0] * hsv_inactive.shape[1])) * 100

    print(f"   Estado ATIVO: {active_percent:.1f}% de pixels verdes detectados")
    print(f"   Estado INATIVO: {inactive_percent:.1f}% de pixels verdes detectados")

    if active_percent > 10 and inactive_percent < 5:
        print("   ✅ Configurações parecem ÓTIMAS! (>10% ativo, <5% inativo)")
    elif active_percent > 10 and inactive_percent < 10:
        print("   ✅ Configurações parecem boas (>10% ativo, <10% inativo)")
    elif active_percent > 10:
        print("   ⚠️  Atenção: Estado inativo também tem muitos pixels verdes")
        print("       Considere ajustar os ranges para ser mais restritivo")
    else:
        print("   ⚠️  Atenção: Estado ativo tem poucos pixels verdes")
        print("       Considere ajustar threshold_percent para um valor menor")

    print("\n💡 Dica: Verifique as imagens *_zoomed.png e *_fullscreen.png para confirmar")
    print("   que as coordenadas estão corretas!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Calibração cancelada pelo usuário")
    except Exception as e:
        print(f"\n\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

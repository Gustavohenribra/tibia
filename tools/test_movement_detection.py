"""
Ferramenta para testar e visualizar detecção de movimento
Mostra o anel de análise e a diferença detectada em tempo real
"""
import sys
import os
import time
import cv2
import numpy as np

# Adiciona diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.screen_capture_obs import OBSScreenCapture
from src.minimap_reader import MinimapReader

def draw_analysis_zones(minimap, center_x, center_y, inner_radius, outer_radius):
    """Desenha as zonas de análise no minimapa"""
    viz = minimap.copy()

    # Desenha círculo interno (zona ignorada - onde está a cruz)
    cv2.circle(viz, (center_x, center_y), inner_radius, (0, 0, 255), 1)
    cv2.putText(viz, "CRUZ", (center_x - 15, center_y + 3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)

    # Desenha círculo externo (zona analisada - o mapa)
    cv2.circle(viz, (center_x, center_y), outer_radius, (0, 255, 0), 1)
    cv2.putText(viz, "MAPA", (center_x + 10, center_y - outer_radius + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)

    # Desenha cruz no centro
    cv2.line(viz, (center_x - 3, center_y), (center_x + 3, center_y), (255, 255, 255), 1)
    cv2.line(viz, (center_x, center_y - 3), (center_x, center_y + 3), (255, 255, 255), 1)

    return viz

def main():
    print("=" * 70)
    print("TESTE DE DETECÇÃO DE MOVIMENTO")
    print("=" * 70)
    print()
    print("Esta ferramenta testa a detecção de movimento em tempo real.")
    print()
    print("INSTRUÇÕES:")
    print("1. Mantenha o Tibia aberto e visível")
    print("2. A ferramenta mostrará o minimapa com as zonas de análise")
    print("3. Ande no jogo e veja a detecção funcionando")
    print("4. Pressione ESC para sair")
    print()

    # Carrega configurações
    import json
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'bot_settings.json')
    with open(config_path, 'r') as f:
        settings = json.load(f)

    # Inicializa captura OBS
    print("Inicializando OBS Screen Capture...")
    capture = OBSScreenCapture()

    if not capture.is_available():
        print("❌ ERRO: OBS não está disponível!")
        return

    print("✅ OBS conectado com sucesso!")
    print()

    # Inicializa MinimapReader
    minimap_settings = settings.get("minimap", {})
    minimap_reader = MinimapReader(capture, minimap_settings)

    print("📊 Configurações do minimap:")
    print(f"   Região: {minimap_reader.minimap_x}, {minimap_reader.minimap_y}")
    print(f"   Tamanho: {minimap_reader.minimap_width}x{minimap_reader.minimap_height}")
    print(f"   Centro: ({minimap_reader.center_x}, {minimap_reader.center_y})")
    print()

    print("🎮 Iniciando monitoramento... (pressione ESC para sair)")
    print()

    # Frame anterior
    prev_frame = None
    frame_count = 0

    # Parâmetros de análise (mesmos do is_player_moving)
    inner_radius = 5
    outer_radius = 25

    while True:
        # Captura minimapa
        current_frame = minimap_reader.capture_minimap()

        if current_frame is None:
            time.sleep(0.1)
            continue

        frame_count += 1

        # Detecta movimento
        is_moving = False
        changed_pixels = 0
        change_percent = 0.0

        if prev_frame is not None:
            # Mesma lógica do is_player_moving
            height, width = current_frame.shape[:2]
            y, x = np.ogrid[:height, :width]

            dist_from_center = np.sqrt((x - minimap_reader.center_x)**2 +
                                      (y - minimap_reader.center_y)**2)

            mask = ((dist_from_center >= inner_radius) &
                   (dist_from_center <= outer_radius)).astype(np.uint8)

            prev_masked = cv2.bitwise_and(prev_frame, prev_frame, mask=mask)
            curr_masked = cv2.bitwise_and(current_frame, current_frame, mask=mask)

            diff = cv2.absdiff(prev_masked, curr_masked)
            gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            changed_pixels = np.sum(gray_diff > 25)

            analyzed_pixels = np.sum(mask)
            change_percent = (changed_pixels / analyzed_pixels * 100) if analyzed_pixels > 0 else 0

            is_moving = changed_pixels >= 30 or change_percent > 3.0

        # Visualização
        viz = draw_analysis_zones(current_frame,
                                 minimap_reader.center_x,
                                 minimap_reader.center_y,
                                 inner_radius, outer_radius)

        # Amplia para visualização
        scale = 4
        viz_large = cv2.resize(viz, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)

        # Adiciona informações de texto
        status_color = (0, 0, 255) if is_moving else (0, 255, 0)
        status_text = "MOVENDO" if is_moving else "PARADO"

        cv2.putText(viz_large, status_text, (10, 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        info_text = f"Pixels: {changed_pixels} ({change_percent:.1f}%)"
        cv2.putText(viz_large, info_text, (10, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        threshold_text = f"Threshold: 30 px ou 3%"
        cv2.putText(viz_large, threshold_text, (10, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # Mostra
        cv2.imshow("Detecção de Movimento - Minimapa", viz_large)

        # Log no console a cada 10 frames
        if frame_count % 10 == 0:
            status_emoji = "🏃" if is_moving else "⏸️"
            print(f"{status_emoji} Frame {frame_count}: {status_text:8s} | "
                  f"Mudança: {changed_pixels:4d} pixels ({change_percent:5.1f}%)")

        # Salva frame para próxima iteração
        prev_frame = current_frame.copy()

        # Aguarda tecla
        key = cv2.waitKey(100) & 0xFF
        if key == 27:  # ESC
            print("\n✅ Teste finalizado!")
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Teste cancelado pelo usuário")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"\n\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()

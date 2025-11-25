"""
Ferramenta para debugar pathfinding
Visualiza as extremidades detectadas e onde o bot está clicando
"""
import sys
import os
import cv2
import numpy as np

# Adiciona diretórios ao path
project_root = os.path.join(os.path.dirname(__file__), '..')
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_dir)

from src.screen_capture_obs import OBSScreenCapture
from src.minimap_reader import MinimapReader

def main():
    print("=" * 70)
    print("DEBUG DE PATHFINDING")
    print("=" * 70)
    print()
    print("Esta ferramenta mostra onde o bot detecta extremidades caminháveis")
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

    print("📊 Configurações:")
    print(f"   Região minimapa: {minimap_reader.minimap_x}, {minimap_reader.minimap_y}")
    print(f"   Tamanho: {minimap_reader.minimap_width}x{minimap_reader.minimap_height}")
    print(f"   Centro (cruz player): ({minimap_reader.center_x}, {minimap_reader.center_y})")
    print()

    # Captura minimapa
    print("📸 Capturando minimapa...")
    minimap = minimap_reader.capture_minimap()

    if minimap is None:
        print("❌ Falha ao capturar minimapa!")
        return

    print("✅ Minimapa capturado!")
    print()

    # Converte para HSV e cria máscaras
    print("🎨 Criando máscaras de cor...")
    hsv = cv2.cvtColor(minimap, cv2.COLOR_BGR2HSV)

    walkable_mask = minimap_reader.create_color_mask(hsv, "walkable")
    wall_mask = minimap_reader.create_color_mask(hsv, "wall")
    hole_mask = minimap_reader.create_color_mask(hsv, "hole")

    # Conta pixels
    walkable_count = np.count_nonzero(walkable_mask) if walkable_mask is not None else 0
    wall_count = np.count_nonzero(wall_mask) if wall_mask is not None else 0
    hole_count = np.count_nonzero(hole_mask) if hole_mask is not None else 0

    print(f"   🟢 Walkable (verde): {walkable_count} pixels")
    print(f"   🔴 Wall (vermelho): {wall_count} pixels")
    print(f"   🟡 Hole (amarelo): {hole_count} pixels")
    print()

    # Detecta extremidades com diferentes distâncias
    print("🎯 Detectando extremidades...")
    for min_dist in [20, 25, 30, 35, 40]:
        edges = minimap_reader.get_walkable_edges(min_distance_from_center=min_dist)
        print(f"   Distância >= {min_dist}px: {len(edges)} extremidades")

    # Usa distância padrão (30)
    edges = minimap_reader.get_walkable_edges(min_distance_from_center=30)
    print()
    print(f"✅ Usando distância 30px: {len(edges)} extremidades detectadas")
    print()

    if len(edges) == 0:
        print("⚠️  PROBLEMA: Nenhuma extremidade detectada!")
        print("   Verifique se as cores foram calibradas corretamente.")
        print("   Execute: python tools/calibrate_minimap_colors.py")
        return

    # Cria visualização
    print("🖼️  Criando visualização...")

    # Aplica erosão na máscara walkable (mesmo processo do código)
    kernel = np.ones((3, 3), np.uint8)
    eroded_walkable = cv2.erode(walkable_mask, kernel, iterations=2) if walkable_mask is not None else None

    # 1. Minimapa original
    viz_original = minimap.copy()

    # 2. Máscara colorida (ANTES da erosão)
    viz_mask = np.zeros_like(minimap)
    if walkable_mask is not None:
        viz_mask[walkable_mask > 0] = [0, 255, 0]  # Verde
    if wall_mask is not None:
        viz_mask[wall_mask > 0] = [0, 0, 255]  # Vermelho
    if hole_mask is not None:
        viz_mask[hole_mask > 0] = [0, 255, 255]  # Amarelo

    # 2b. Máscara após erosão (mostra o "centro" dos caminhos)
    viz_eroded = np.zeros_like(minimap)
    if eroded_walkable is not None:
        viz_eroded[eroded_walkable > 0] = [0, 255, 0]  # Verde (centro)
    if wall_mask is not None:
        viz_eroded[wall_mask > 0] = [0, 0, 255]  # Vermelho
    if hole_mask is not None:
        viz_eroded[hole_mask > 0] = [0, 255, 255]  # Amarelo

    # 3. Minimapa com extremidades marcadas
    viz_edges = minimap.copy()

    # Desenha cruz do player no centro
    cv2.drawMarker(viz_edges,
                   (minimap_reader.center_x, minimap_reader.center_y),
                   (255, 255, 255), cv2.MARKER_CROSS, 5, 2)

    # Desenha círculo de distância mínima
    cv2.circle(viz_edges,
              (minimap_reader.center_x, minimap_reader.center_y),
              30, (100, 100, 100), 1)

    # Desenha cada extremidade
    for i, (x, y) in enumerate(edges):
        # Calcula distância do centro
        dist = np.sqrt((x - minimap_reader.center_x)**2 +
                      (y - minimap_reader.center_y)**2)

        # Cor baseada na distância (mais longe = mais brilhante)
        intensity = min(255, int((dist / 50) * 255))
        color = (0, intensity, 255)

        # Desenha círculo
        cv2.circle(viz_edges, (x, y), 2, color, -1)

        # Numera os primeiros 10
        if i < 10:
            cv2.putText(viz_edges, str(i+1), (x+3, y+3),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

    # 4. Overlay combinado
    viz_combined = cv2.addWeighted(minimap, 0.6, viz_mask, 0.4, 0)

    # Desenha extremidades também no combined
    for x, y in edges:
        cv2.circle(viz_combined, (x, y), 2, (255, 255, 255), -1)

    # Desenha cruz
    cv2.drawMarker(viz_combined,
                   (minimap_reader.center_x, minimap_reader.center_y),
                   (255, 255, 255), cv2.MARKER_CROSS, 5, 2)

    # Amplia todas para visualização
    scale = 4
    viz_original_large = cv2.resize(viz_original, None, fx=scale, fy=scale,
                                    interpolation=cv2.INTER_NEAREST)
    viz_mask_large = cv2.resize(viz_mask, None, fx=scale, fy=scale,
                                interpolation=cv2.INTER_NEAREST)
    viz_eroded_large = cv2.resize(viz_eroded, None, fx=scale, fy=scale,
                                  interpolation=cv2.INTER_NEAREST)
    viz_edges_large = cv2.resize(viz_edges, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_NEAREST)
    viz_combined_large = cv2.resize(viz_combined, None, fx=scale, fy=scale,
                                    interpolation=cv2.INTER_NEAREST)

    # Salva imagens
    cv2.imwrite("debug_pathfinding_original.png", viz_original_large)
    cv2.imwrite("debug_pathfinding_mask.png", viz_mask_large)
    cv2.imwrite("debug_pathfinding_eroded.png", viz_eroded_large)
    cv2.imwrite("debug_pathfinding_edges.png", viz_edges_large)
    cv2.imwrite("debug_pathfinding_combined.png", viz_combined_large)

    print("💾 Imagens salvas:")
    print("   - debug_pathfinding_original.png (minimapa original)")
    print("   - debug_pathfinding_mask.png (máscaras ANTES da erosão)")
    print("   - debug_pathfinding_eroded.png (máscaras DEPOIS da erosão - centro dos caminhos)")
    print("   - debug_pathfinding_edges.png (extremidades detectadas)")
    print("   - debug_pathfinding_combined.png (visão combinada)")
    print()

    # Mostra janelas
    # print("👁️  Mostrando visualizações... (pressione qualquer tecla para fechar)")
    # print()

    # cv2.imshow("1. Minimapa Original", viz_original_large)
    # cv2.imshow("2. Máscaras (Antes Erosão)", viz_mask_large)
    # cv2.imshow("3. Centro dos Caminhos (Após Erosão)", viz_eroded_large)
    # cv2.imshow("4. Extremidades Detectadas", viz_edges_large)
    # cv2.imshow("5. Visão Combinada", viz_combined_large)

    # Lista das extremidades
    print("📋 Lista de extremidades (primeiras 10):")
    for i, (x, y) in enumerate(edges[:10]):
        dist = np.sqrt((x - minimap_reader.center_x)**2 +
                      (y - minimap_reader.center_y)**2)
        print(f"   {i+1}. ({x:3d}, {y:3d}) - distância: {dist:.1f}px do centro")

    if len(edges) > 10:
        print(f"   ... e mais {len(edges) - 10} extremidades")

    print()
    print("🔍 ANÁLISE:")
    if walkable_count == 0:
        print("   ❌ PROBLEMA: Nenhum pixel walkable detectado!")
        print("      Verifique calibração de cores (verde)")
    elif len(edges) < 5:
        print("   ⚠️  AVISO: Poucas extremidades detectadas")
        print("      Considere diminuir min_distance_from_center ou verificar calibração")
    else:
        print("   ✅ Extremidades parecem OK")

    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    print("\n✅ Debug finalizado!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelado pelo usuário")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"\n\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()

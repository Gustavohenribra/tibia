"""
DEBUG VISUAL - Mostra EXATAMENTE o que o bot está detectando
Salva imagens mostrando máscaras de cores e pontos escolhidos
"""
import sys
sys.path.insert(0, 'src')

import cv2
import numpy as np
import json
from screen_capture_obs import OBSScreenCapture
from minimap_reader import MinimapReader

print("=" * 70)
print("DEBUG VISUAL - DETECÇÃO DO MINIMAP")
print("=" * 70)
print()

# Carrega configurações
with open('config/bot_settings.json', 'r') as f:
    settings = json.load(f)

# Inicializa captura e leitor
print("Inicializando OBS...")
obs = OBSScreenCapture()
print("✅ OBS conectado")
print()

print("Inicializando MinimapReader...")
minimap_reader = MinimapReader(obs, settings['minimap'])
print("✅ MinimapReader inicializado")
print()

# Captura minimap
print("Capturando minimap...")
minimap = minimap_reader.capture_minimap()
if minimap is None:
    print("❌ Falha ao capturar minimap")
    sys.exit(1)

print(f"✅ Minimap capturado: {minimap.shape[1]}x{minimap.shape[0]}")
print()

# Converte para HSV
hsv = cv2.cvtColor(minimap, cv2.COLOR_BGR2HSV)

# Cria máscaras
print("Criando máscaras de cores...")
walkable_mask = minimap_reader.create_color_mask(hsv, "walkable")
wall_mask = minimap_reader.create_color_mask(hsv, "wall")
hole_mask = minimap_reader.create_color_mask(hsv, "hole")

if walkable_mask is not None:
    walkable_pixels = np.count_nonzero(walkable_mask)
    print(f"  🟠 WALKABLE (laranja): {walkable_pixels} pixels")
else:
    print(f"  🟠 WALKABLE: ❌ Não configurado")
    walkable_pixels = 0

if wall_mask is not None:
    wall_pixels = np.count_nonzero(wall_mask)
    print(f"  ⬛ WALL (preto): {wall_pixels} pixels")
else:
    print(f"  ⬛ WALL: ❌ Não configurado")
    wall_pixels = 0

if hole_mask is not None:
    hole_pixels = np.count_nonzero(hole_mask)
    print(f"  🟡 HOLE (amarelo): {hole_pixels} pixels")
else:
    print(f"  🟡 HOLE: ❌ Não configurado")
    hole_pixels = 0

print()

# ANÁLISE CRÍTICA
total_pixels = minimap.shape[0] * minimap.shape[1]
detected_pixels = walkable_pixels + wall_pixels + hole_pixels
undetected_pixels = total_pixels - detected_pixels

print(f"📊 ANÁLISE:")
print(f"  Total de pixels: {total_pixels}")
print(f"  Detectados: {detected_pixels} ({detected_pixels/total_pixels*100:.1f}%)")
print(f"  NÃO detectados: {undetected_pixels} ({undetected_pixels/total_pixels*100:.1f}%)")
print()

if wall_pixels == 0:
    print("🔴 PROBLEMA CRÍTICO: Nenhum pixel PRETO foi detectado!")
    print("   Isso significa que a calibração de WALL (parede) está ERRADA!")
    print("   O bot NÃO CONSEGUE VER as paredes pretas!")
    print()
elif wall_pixels < walkable_pixels * 0.1:
    print("⚠️  AVISO: Muito poucos pixels PRETOS detectados")
    print(f"   Preto: {wall_pixels} vs Laranja: {walkable_pixels}")
    print("   A calibração de WALL pode estar incorreta")
    print()

# Obtém extremidades
print("Detectando extremidades...")
edges = minimap_reader.get_walkable_edges(min_distance_from_center=30)
print(f"✅ {len(edges)} extremidades detectadas")
print()

# Cria visualizações
print("Gerando imagens de debug...")

# 1. Minimap original com centro marcado
debug_original = minimap.copy()
cv2.circle(debug_original, (minimap_reader.center_x, minimap_reader.center_y), 3, (0, 255, 0), -1)
cv2.imwrite("debug_1_minimap_original.png", debug_original)
print("  ✅ debug_1_minimap_original.png")

# 2. Máscara WALKABLE (laranja)
if walkable_mask is not None:
    debug_walkable = cv2.cvtColor(walkable_mask, cv2.COLOR_GRAY2BGR)
    cv2.circle(debug_walkable, (minimap_reader.center_x, minimap_reader.center_y), 3, (0, 255, 0), -1)
    cv2.imwrite("debug_2_mask_walkable.png", debug_walkable)
    print("  ✅ debug_2_mask_walkable.png (BRANCO = laranja detectado)")

# 3. Máscara WALL (preto)
if wall_mask is not None:
    debug_wall = cv2.cvtColor(wall_mask, cv2.COLOR_GRAY2BGR)
    cv2.circle(debug_wall, (minimap_reader.center_x, minimap_reader.center_y), 3, (0, 255, 0), -1)
    cv2.imwrite("debug_3_mask_wall.png", debug_wall)
    print("  ✅ debug_3_mask_wall.png (BRANCO = preto detectado)")

# 4. Máscara HOLE (amarelo)
if hole_mask is not None:
    debug_hole = cv2.cvtColor(hole_mask, cv2.COLOR_GRAY2BGR)
    cv2.circle(debug_hole, (minimap_reader.center_x, minimap_reader.center_y), 3, (0, 255, 0), -1)
    cv2.imwrite("debug_4_mask_hole.png", debug_hole)
    print("  ✅ debug_4_mask_hole.png (BRANCO = amarelo detectado)")

# 5. Máscara COMBINADA (colorida)
debug_combined = np.zeros_like(minimap)
if walkable_mask is not None:
    debug_combined[walkable_mask > 0] = [0, 165, 255]  # Laranja
if wall_mask is not None:
    debug_combined[wall_mask > 0] = [50, 50, 50]  # Cinza escuro (preto)
if hole_mask is not None:
    debug_combined[hole_mask > 0] = [0, 255, 255]  # Amarelo
cv2.circle(debug_combined, (minimap_reader.center_x, minimap_reader.center_y), 3, (0, 255, 0), -1)
cv2.imwrite("debug_5_mask_combined.png", debug_combined)
print("  ✅ debug_5_mask_combined.png (LARANJA=walkable, CINZA=wall, AMARELO=hole)")

# 6. Extremidades escolhidas
debug_edges = minimap.copy()
for edge in edges:
    x, y = edge
    # Marca ponto com círculo vermelho
    cv2.circle(debug_edges, (x, y), 3, (0, 0, 255), -1)
    # Área de segurança (5px) em azul
    cv2.circle(debug_edges, (x, y), 5, (255, 0, 0), 1)

# Centro em verde
cv2.circle(debug_edges, (minimap_reader.center_x, minimap_reader.center_y), 3, (0, 255, 0), -1)
cv2.imwrite("debug_6_edges_selected.png", debug_edges)
print("  ✅ debug_6_edges_selected.png (VERMELHO=pontos, AZUL=área segurança 5px)")

# 7. Overlay das máscaras no minimap original
debug_overlay = minimap.copy()
overlay_color = minimap.copy()

if walkable_mask is not None:
    overlay_color[walkable_mask > 0] = [0, 165, 255]  # Laranja
if wall_mask is not None:
    overlay_color[wall_mask > 0] = [255, 0, 0]      # Azul (OpenCV é BGR)

# Aplica transparência (blend)
cv2.addWeighted(overlay_color, 0.4, debug_overlay, 0.6, 0, debug_overlay)

cv2.circle(debug_overlay, (minimap_reader.center_x, minimap_reader.center_y), 3, (0, 255, 0), -1)
cv2.imwrite("debug_7_overlay.png", debug_overlay)
print("  ✅ debug_7_overlay.png (Máscaras sobrepostas no original)")

print()
print("=" * 70)
print("RESULTADO")
print("=" * 70)
print()

if wall_pixels == 0:
    print("🔴 PROBLEMA ENCONTRADO:")
    print()
    print("   A calibração das cores está ERRADA!")
    print("   NENHUM pixel PRETO foi detectado como WALL (parede)!")
    print()
    print("   SOLUÇÃO:")
    print("   1. Abra: debug_1_minimap_original.png")
    print("   2. Abra: debug_3_mask_wall.png")
    print("   3. Se debug_3_mask_wall.png está TODO PRETO (sem branco):")
    print("      → As paredes NÃO estão sendo detectadas!")
    print("      → Precisa recalibrar as cores em config/bot_settings.json")
    print()
    print("   Execute: python tools/calibrate_minimap_colors.py")
    print()
elif len(edges) == 0:
    print("⚠️  Nenhuma extremidade segura encontrada")
    print("   Todas foram rejeitadas (muito perto, parede ou buraco)")
else:
    print(f"✅ {len(edges)} extremidades seguras detectadas")
    print()
    print("   Verifique as imagens:")
    print("   - debug_6_edges_selected.png mostra os pontos escolhidos")
    print("   - Se algum ponto está em PRETO, o problema é:")
    print("     → Coordenadas OBS ≠ Tela Real")
    print("     → Execute: py test_coordinates.py")

print()
print("🔍 Confira as 7 imagens geradas para diagnóstico completo!")
print()

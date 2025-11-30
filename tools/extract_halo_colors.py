"""
Extrai as cores BGR exatas do aro da imagem de debug
"""

import cv2
import numpy as np

# Carrega imagem original (não zoomed)
img = cv2.imread("debug_halo_with_halo.png")
mask = cv2.imread("debug_halo_with_halo_mask.png", cv2.IMREAD_GRAYSCALE)

if img is None or mask is None:
    print("Erro ao carregar imagens")
    exit(1)

print("="*60)
print("CORES BGR DO ARO DE COMBATE")
print("="*60)

# Pega pixels onde a máscara é branca (aro detectado)
halo_pixels = img[mask > 128]

if len(halo_pixels) == 0:
    print("Nenhum pixel de aro encontrado na máscara")
    exit(1)

print(f"\nTotal de pixels do aro: {len(halo_pixels)}")

# Cores únicas e contagem
unique_colors, counts = np.unique(halo_pixels, axis=0, return_counts=True)

# Ordena por frequência
sorted_idx = np.argsort(counts)[::-1]

print(f"\nTop 15 cores BGR mais comuns no aro:")
print("-"*40)

bgr_colors = []
for i, idx in enumerate(sorted_idx[:15]):
    bgr = tuple(unique_colors[idx])
    count = counts[idx]
    percent = (count / len(halo_pixels)) * 100
    print(f"  {i+1:2}. BGR{bgr}: {count:4} pixels ({percent:5.1f}%)")
    bgr_colors.append(list(bgr))

print("\n" + "="*60)
print("CONFIGURAÇÃO SUGERIDA (copie para bot_settings.json):")
print("="*60)
print('"bgr_colors": [')
for bgr in bgr_colors[:10]:  # Top 10
    print(f'  {bgr},')
print(']')

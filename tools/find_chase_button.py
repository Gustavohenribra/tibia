"""
Ferramenta para ENCONTRAR as coordenadas do botão Chase
Captura a tela e permite clicar para marcar o botão
"""
import sys
import os
import cv2
import numpy as np

# Adiciona diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.screen_capture_obs import OBSScreenCapture

# Variáveis globais para clique do mouse
click_count = 0
points = []

def mouse_callback(event, x, y, flags, param):
    """Callback para capturar cliques do mouse"""
    global click_count, points

    if event == cv2.EVENT_LBUTTONDOWN:
        click_count += 1
        points.append((x, y))

        if click_count == 1:
            print(f"   ✅ Ponto 1 marcado: ({x}, {y}) - superior esquerdo")
            print("   Agora clique no canto INFERIOR DIREITO do botão chase...")
        elif click_count == 2:
            print(f"   ✅ Ponto 2 marcado: ({x}, {y}) - inferior direito")

def main():
    print("=" * 70)
    print("ENCONTRAR COORDENADAS DO BOTÃO CHASE")
    print("=" * 70)
    print()
    print("Esta ferramenta ajuda você a encontrar as coordenadas exatas do botão chase.")
    print()
    print("INSTRUÇÕES:")
    print("1. Uma janela abrirá mostrando a tela do Tibia")
    print("2. Clique no canto SUPERIOR ESQUERDO do botão chase")
    print("3. Clique no canto INFERIOR DIREITO do botão chase")
    print("4. As coordenadas serão exibidas para você copiar")
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

    # Captura tela
    print("📸 Capturando tela...")
    frame = capture.capture_fullscreen()

    if frame is None:
        print("❌ Falha ao capturar tela!")
        return

    print(f"✅ Tela capturada: {frame.shape[1]}x{frame.shape[0]} pixels")
    print()

    # Redimensiona para caber na tela (se necessário)
    scale = 1.0
    max_height = 900
    if frame.shape[0] > max_height:
        scale = max_height / frame.shape[0]
        new_width = int(frame.shape[1] * scale)
        new_height = int(frame.shape[0] * scale)
        display_frame = cv2.resize(frame, (new_width, new_height))
        print(f"ℹ️  Redimensionando para {new_width}x{new_height} (escala: {scale:.2f})")
    else:
        display_frame = frame.copy()

    print()
    print("🖱️  Agora clique no canto SUPERIOR ESQUERDO do botão chase...")

    # Cria janela e define callback
    window_name = "Clique no botão Chase (ESC para sair)"
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)

    # Loop de exibição
    while True:
        # Copia frame para desenhar
        display = display_frame.copy()

        # Desenha pontos já clicados
        if len(points) >= 1:
            # Converte coordenada da janela para coordenada real
            real_x1 = int(points[0][0] / scale)
            real_y1 = int(points[0][1] / scale)

            cv2.circle(display, points[0], 5, (0, 255, 0), -1)
            cv2.putText(display, f"1: ({real_x1},{real_y1})",
                       (points[0][0] + 10, points[0][1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        if len(points) >= 2:
            # Converte coordenada da janela para coordenada real
            real_x2 = int(points[1][0] / scale)
            real_y2 = int(points[1][1] / scale)

            cv2.circle(display, points[1], 5, (0, 0, 255), -1)
            cv2.putText(display, f"2: ({real_x2},{real_y2})",
                       (points[1][0] + 10, points[1][1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # Desenha retângulo
            cv2.rectangle(display, points[0], points[1], (255, 0, 0), 2)

            # Mostra dimensões
            width = abs(real_x2 - real_x1)
            height = abs(real_y2 - real_y1)
            center_x = (points[0][0] + points[1][0]) // 2
            center_y = (points[0][1] + points[1][1]) // 2
            cv2.putText(display, f"{width}x{height} px",
                       (center_x - 40, center_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # Mostra imagem
        cv2.imshow(window_name, display)

        # Aguarda tecla
        key = cv2.waitKey(1) & 0xFF

        # ESC para sair
        if key == 27:
            print("\n⚠️  Cancelado pelo usuário")
            break

        # Se já tiver 2 pontos, aguarda confirmação
        if len(points) >= 2:
            # Converte coordenadas para reais
            x1 = int(min(points[0][0], points[1][0]) / scale)
            y1 = int(min(points[0][1], points[1][1]) / scale)
            x2 = int(max(points[0][0], points[1][0]) / scale)
            y2 = int(max(points[0][1], points[1][1]) / scale)

            # Captura região selecionada
            button_img = frame[y1:y2, x1:x2]

            # Salva preview
            cv2.imwrite("debug_chase_button_found.png", button_img)

            # Amplia 10x
            zoomed = cv2.resize(button_img, None, fx=10, fy=10, interpolation=cv2.INTER_NEAREST)
            cv2.imwrite("debug_chase_button_found_zoomed.png", zoomed)

            # Salva fullscreen com retângulo
            frame_with_rect = frame.copy()
            cv2.rectangle(frame_with_rect, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(frame_with_rect, "CHASE BUTTON",
                       (x1 - 100, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.imwrite("debug_chase_button_found_fullscreen.png", frame_with_rect)

            print()
            print("=" * 70)
            print("✅ COORDENADAS ENCONTRADAS!")
            print("=" * 70)
            print()
            print("📋 Copie estas coordenadas para bot_settings.json:")
            print()
            print(f'"x1": {x1},')
            print(f'"y1": {y1},')
            print(f'"x2": {x2},')
            print(f'"y2": {y2},')
            print()
            print(f"Dimensões: {x2-x1}x{y2-y1} pixels")
            print()
            print("💾 Imagens salvas:")
            print("   - debug_chase_button_found.png (original)")
            print("   - debug_chase_button_found_zoomed.png (ampliado 10x)")
            print("   - debug_chase_button_found_fullscreen.png (tela completa com retângulo)")
            print()
            print("Pressione ESC para fechar ou R para recomeçar...")

            # Aguarda ESC ou R
            while True:
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    break
                elif key == ord('r') or key == ord('R'):  # R para recomeçar
                    print("\n🔄 Recomeçando...")
                    points.clear()
                    click_count = 0
                    print("🖱️  Clique no canto SUPERIOR ESQUERDO do botão chase...")
                    break

            if key == 27:
                break

    cv2.destroyAllWindows()
    print("\n✅ Ferramenta finalizada!")

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

"""
Ferramenta de Calibração de Cores do Minimapa
Permite selecionar cores interativamente para gerar HSV ranges precisos
"""

import cv2
import numpy as np
import json
import sys
import os

# Adiciona diretório pai ao path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from screen_capture_obs import OBSScreenCapture
from utils.logger import get_logger


class MinimapColorCalibrator:
    """Calibrador interativo de cores do minimapa"""

    def __init__(self, settings_path: str = "config/bot_settings.json"):
        """
        Inicializa calibrador

        Args:
            settings_path: Caminho para bot_settings.json
        """
        self.logger = get_logger()

        # Carrega settings
        with open(settings_path, 'r') as f:
            self.settings = json.load(f)

        # Inicializa screen capture
        self.screen_capture = OBSScreenCapture(
            camera_index=self.settings["obs_camera"]["device_index"]
        )

        # Configurações do minimapa
        minimap_config = self.settings["minimap"]
        self.minimap_x = minimap_config["region"]["x"]
        self.minimap_y = minimap_config["region"]["y"]
        self.minimap_width = minimap_config["region"]["width"]
        self.minimap_height = minimap_config["region"]["height"]

        # Armazenamento de cores selecionadas
        self.selected_colors = {
            "walkable": [],
            "wall": [],
            "hole": []
        }

        self.current_mode = "walkable"  # Modo atual de seleção
        self.minimap_img = None
        self.display_img = None

        # Fator de zoom para facilitar seleção de pixels (4x maior)
        self.zoom_factor = 4

        self.logger.info("🎨 Calibrador de Cores do Minimapa inicializado")
        self.logger.info(f"   Região: ({self.minimap_x}, {self.minimap_y}) {self.minimap_width}x{self.minimap_height}")
        self.logger.info(f"   Zoom: {self.zoom_factor}x (para facilitar seleção)")

    def capture_minimap(self) -> np.ndarray:
        """Captura região do minimapa"""
        img = self.screen_capture.capture_region(
            x=self.minimap_x,
            y=self.minimap_y,
            width=self.minimap_width,
            height=self.minimap_height
        )

        if img is None:
            self.logger.error("Falha ao capturar minimapa")
            return None

        return img

    def mouse_callback(self, event, x, y, flags, param):
        """Callback para clicks do mouse na janela OpenCV"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.minimap_img is None:
                return

            # Converte coordenadas do display ampliado para coordenadas originais
            original_x = int(x / self.zoom_factor)
            original_y = int(y / self.zoom_factor)

            # Garante que click está dentro dos limites
            if original_x < 0 or original_x >= self.minimap_width or original_y < 0 or original_y >= self.minimap_height:
                return

            # Pega cor BGR do pixel clicado (usando coordenadas originais)
            bgr_color = self.minimap_img[original_y, original_x]

            # Converte para HSV
            hsv_pixel = cv2.cvtColor(
                np.uint8([[bgr_color]]),
                cv2.COLOR_BGR2HSV
            )[0][0]

            # Adiciona à lista do modo atual
            self.selected_colors[self.current_mode].append(hsv_pixel)

            self.logger.info(
                f"✅ [{self.current_mode.upper()}] Cor selecionada em ({original_x}, {original_y}): "
                f"BGR={bgr_color} → HSV={hsv_pixel}"
            )

            # Atualiza display
            self.update_display()

    def update_display(self):
        """Atualiza imagem de display com marcadores"""
        if self.minimap_img is None:
            return

        # Copia imagem original
        self.display_img = self.minimap_img.copy()

        # Desenha marcadores para cada cor selecionada
        colors_bgr = {
            "walkable": (0, 255, 0),      # Verde
            "wall": (0, 0, 255),          # Vermelho
            "hole": (0, 255, 255)         # Amarelo
        }

        for mode, hsv_colors in self.selected_colors.items():
            if not hsv_colors:
                continue

            bgr_color = colors_bgr[mode]

            # Marca cada pixel selecionado com círculo
            for hsv in hsv_colors:
                # Encontra pixel correspondente (busca aproximada)
                hsv_img = cv2.cvtColor(self.minimap_img, cv2.COLOR_BGR2HSV)

                # Cria máscara para cor similar (tolerância pequena)
                lower = np.array([max(0, hsv[0]-2), max(0, hsv[1]-20), max(0, hsv[2]-20)])
                upper = np.array([min(180, hsv[0]+2), min(255, hsv[1]+20), min(255, hsv[2]+20)])
                mask = cv2.inRange(hsv_img, lower, upper)

                # Encontra contornos
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Desenha contornos
                cv2.drawContours(self.display_img, contours, -1, bgr_color, 1)

    def calculate_hsv_range(self, hsv_colors: list) -> dict:
        """
        Calcula range HSV a partir de múltiplas amostras

        Args:
            hsv_colors: Lista de cores HSV selecionadas

        Returns:
            Dict com hsv_lower e hsv_upper
        """
        if not hsv_colors:
            return None

        # Converte para numpy array
        colors_array = np.array(hsv_colors)

        # Calcula mínimo e máximo para cada canal
        h_values = colors_array[:, 0]
        s_values = colors_array[:, 1]
        v_values = colors_array[:, 2]

        # Range com margem de segurança
        h_margin = 10
        s_margin = 30
        v_margin = 30

        hsv_lower = [
            int(max(0, h_values.min() - h_margin)),
            int(max(0, s_values.min() - s_margin)),
            int(max(0, v_values.min() - v_margin))
        ]

        hsv_upper = [
            int(min(180, h_values.max() + h_margin)),
            int(min(255, s_values.max() + s_margin)),
            int(min(255, v_values.max() + v_margin))
        ]

        return {
            "hsv_lower": hsv_lower,
            "hsv_upper": hsv_upper
        }

    def generate_masks(self):
        """Gera e exibe máscaras para cada tipo de terreno"""
        if self.minimap_img is None:
            return

        hsv_img = cv2.cvtColor(self.minimap_img, cv2.COLOR_BGR2HSV)

        masks = {}
        for mode, hsv_colors in self.selected_colors.items():
            if not hsv_colors:
                continue

            hsv_range = self.calculate_hsv_range(hsv_colors)
            if hsv_range is None:
                continue

            lower = np.array(hsv_range["hsv_lower"])
            upper = np.array(hsv_range["hsv_upper"])

            mask = cv2.inRange(hsv_img, lower, upper)
            masks[mode] = mask

            # Salva máscara
            filename = f"debug_mask_{mode}.png"
            cv2.imwrite(filename, mask)
            self.logger.info(f"💾 Máscara '{mode}' salva em {filename}")

        # Cria visualização combinada
        if masks:
            combined = np.zeros_like(self.minimap_img)

            if "walkable" in masks:
                combined[masks["walkable"] > 0] = [0, 255, 0]  # Verde

            if "wall" in masks:
                combined[masks["wall"] > 0] = [0, 0, 255]  # Vermelho

            if "hole" in masks:
                combined[masks["hole"] > 0] = [0, 255, 255]  # Amarelo

            cv2.imwrite("debug_mask_combined.png", combined)
            self.logger.info("💾 Máscara combinada salva em debug_mask_combined.png")

            # Exibe em janela
            cv2.imshow("Máscaras Combinadas", combined)

    def save_config(self):
        """Salva configuração HSV em formato JSON"""
        config = {
            "minimap": {
                "colors": {}
            }
        }

        for mode, hsv_colors in self.selected_colors.items():
            if not hsv_colors:
                self.logger.warning(f"⚠️  Nenhuma cor selecionada para '{mode}'")
                continue

            hsv_range = self.calculate_hsv_range(hsv_colors)

            if hsv_range:
                config["minimap"]["colors"][mode] = {
                    "name": mode,
                    "hsv_lower": hsv_range["hsv_lower"],
                    "hsv_upper": hsv_range["hsv_upper"]
                }

                self.logger.info(
                    f"📋 [{mode.upper()}] HSV range: "
                    f"lower={hsv_range['hsv_lower']}, upper={hsv_range['hsv_upper']}"
                )

        # Salva em arquivo
        output_file = "calibrated_colors.json"
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)

        self.logger.info(f"✅ Configuração salva em {output_file}")
        self.logger.info("   Copie os valores de 'colors' para bot_settings.json > minimap > colors")

    def run(self):
        """Loop principal de calibração"""
        self.logger.info("\n" + "="*60)
        self.logger.info("🎨 FERRAMENTA DE CALIBRAÇÃO DE CORES DO MINIMAPA")
        self.logger.info("="*60)
        self.logger.info("\nInstruções:")
        self.logger.info("  1️⃣  Pressione '1' = Modo WALKABLE (chão caminhável - verde)")
        self.logger.info("  2️⃣  Pressione '2' = Modo WALL (parede - vermelho)")
        self.logger.info("  3️⃣  Pressione '3' = Modo HOLE (buraco/escada - amarelo)")
        self.logger.info("  🖱️  Click nos pixels para selecionar cores")
        self.logger.info("  🔄 Pressione 'r' = Atualizar captura do minimapa")
        self.logger.info("  👁️  Pressione 'm' = Gerar e visualizar máscaras")
        self.logger.info("  💾 Pressione 's' = Salvar configuração")
        self.logger.info("  ❌ Pressione 'q' ou ESC = Sair")
        self.logger.info("="*60 + "\n")

        # Cria janela
        cv2.namedWindow("Calibração de Minimapa")
        cv2.setMouseCallback("Calibração de Minimapa", self.mouse_callback)

        # Captura inicial
        self.minimap_img = self.capture_minimap()
        if self.minimap_img is None:
            self.logger.error("❌ Falha ao capturar minimapa. Verifique se OBS está rodando.")
            return

        self.update_display()

        while True:
            # Exibe imagem
            if self.display_img is not None:
                # Adiciona texto indicando modo atual
                display_with_text = self.display_img.copy()

                mode_text = f"Modo: {self.current_mode.upper()}"
                color_map = {
                    "walkable": (0, 255, 0),
                    "wall": (0, 0, 255),
                    "hole": (0, 255, 255)
                }
                text_color = color_map[self.current_mode]

                cv2.putText(
                    display_with_text,
                    mode_text,
                    (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    text_color,
                    2
                )

                # Contador de seleções
                count_text = f"Selecionadas: {len(self.selected_colors[self.current_mode])}"
                cv2.putText(
                    display_with_text,
                    count_text,
                    (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 255),
                    1
                )

                # Amplia imagem para facilitar visualização
                zoomed_img = cv2.resize(
                    display_with_text,
                    None,
                    fx=self.zoom_factor,
                    fy=self.zoom_factor,
                    interpolation=cv2.INTER_NEAREST  # Nearest neighbor para manter pixels nítidos
                )

                cv2.imshow("Calibração de Minimapa", zoomed_img)

            # Aguarda tecla
            key = cv2.waitKey(100) & 0xFF

            if key == ord('q') or key == 27:  # 'q' ou ESC
                self.logger.info("👋 Encerrando calibrador...")
                break

            elif key == ord('1'):
                self.current_mode = "walkable"
                self.logger.info("🟢 Modo: WALKABLE (chão caminhável)")

            elif key == ord('2'):
                self.current_mode = "wall"
                self.logger.info("🔴 Modo: WALL (parede)")

            elif key == ord('3'):
                self.current_mode = "hole"
                self.logger.info("🟡 Modo: HOLE (buraco/escada)")

            elif key == ord('r'):
                self.logger.info("🔄 Atualizando captura...")
                self.minimap_img = self.capture_minimap()
                if self.minimap_img is not None:
                    self.update_display()
                    self.logger.info("✅ Captura atualizada")

            elif key == ord('m'):
                self.logger.info("👁️  Gerando máscaras...")
                self.generate_masks()

            elif key == ord('s'):
                self.logger.info("💾 Salvando configuração...")
                self.save_config()
                self.generate_masks()

        cv2.destroyAllWindows()


def main():
    """Função principal"""
    calibrator = MinimapColorCalibrator()
    calibrator.run()


if __name__ == "__main__":
    main()

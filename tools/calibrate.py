"""
Ferramenta de Calibração Visual
Clique em dois pontos (canto superior esquerdo → canto inferior direito)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import cv2
import json
import numpy as np
from screen_capture_obs import OBSScreenCapture


class VisualCalibrator:
    """Calibrador visual interativo"""

    def __init__(self):
        self.screen_capture = OBSScreenCapture(camera_index=5)
        self.screenshot = None
        self.screenshot_original = None  # Screenshot original
        self.display_scale = 1.0  # Escala de exibição
        self.regions = {}
        self.current_region = None
        self.points = []
        self.temp_screenshot = None

    def mouse_callback(self, event, x, y, flags, param):
        """Callback para clicks do mouse"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # Converte coordenadas de display para originais
            x_original = int(x / self.display_scale)
            y_original = int(y / self.display_scale)

            self.points.append((x_original, y_original))

            # Desenha ponto na imagem de display
            cv2.circle(self.temp_screenshot, (x, y), 5, (0, 255, 0), -1)
            cv2.imshow('Calibração', self.temp_screenshot)

            # Se completou os 2 pontos
            if len(self.points) == 2:
                self.finalize_region()

    def finalize_region(self):
        """Finaliza região após 2 pontos"""
        p1, p2 = self.points

        # Garante que p1 é canto superior esquerdo (coordenadas originais)
        x1 = min(p1[0], p2[0])
        y1 = min(p1[1], p2[1])
        x2 = max(p1[0], p2[0])
        y2 = max(p1[1], p2[1])

        # Calcula width e height
        width = x2 - x1
        height = y2 - y1

        # Salva região (coordenadas originais)
        self.regions[self.current_region] = {
            "x": x1,
            "y": y1,
            "width": width,
            "height": height,
            "_points": {
                "top_left": {"x": x1, "y": y1},
                "bottom_right": {"x": x2, "y": y2}
            }
        }

        # Desenha retângulo final (coordenadas de display)
        x1_display = int(x1 * self.display_scale)
        y1_display = int(y1 * self.display_scale)
        x2_display = int(x2 * self.display_scale)
        y2_display = int(y2 * self.display_scale)

        cv2.rectangle(self.temp_screenshot, (x1_display, y1_display), (x2_display, y2_display), (0, 255, 0), 2)
        cv2.putText(self.temp_screenshot, self.current_region, (x1_display, y1_display-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.imshow('Calibração', self.temp_screenshot)
        cv2.waitKey(1000)

        print(f"[OK] {self.current_region}: ({x1}, {y1}) -> ({x2}, {y2}) | {width}x{height}")

    def calibrate_region(self, region_name: str, description: str):
        """Calibra uma região"""
        self.current_region = region_name
        self.points = []
        self.temp_screenshot = self.screenshot.copy()

        print(f"\n[{region_name.upper()}]")
        print(f"   {description}")
        print(f"   Clique em 2 pontos:")
        print(f"   1. Canto SUPERIOR ESQUERDO")
        print(f"   2. Canto INFERIOR DIREITO")
        print()

        # Cria janela com tamanho fixo (1:1 pixel, sem distorção)
        cv2.namedWindow('Calibração', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('Calibração', self.temp_screenshot)
        cv2.setMouseCallback('Calibração', self.mouse_callback)

        # Aguarda 2 clicks
        while len(self.points) < 2:
            key = cv2.waitKey(1)
            if key == 27:  # ESC para cancelar
                return False

        return True

    def run(self):
        """Executa calibração"""
        print("=" * 60)
        print("        CALIBRACAO VISUAL DE REGIOES")
        print("=" * 60)
        print()

        # Captura screenshot
        print("Capturando screenshot do OBS...")
        self.screenshot_original = self.screen_capture.capture_fullscreen()

        if self.screenshot_original is None:
            print("[ERRO] Falha ao capturar screenshot")
            print("       Verifique se OBS Virtual Camera esta ativa")
            return

        h_orig, w_orig = self.screenshot_original.shape[:2]
        print(f"[OK] Screenshot capturado: {w_orig}x{h_orig}")

        # Mantém resolução nativa (não redimensiona)
        self.screenshot = self.screenshot_original.copy()
        self.display_scale = 1.0  # Sem redimensionamento
        print(f"[OK] Usando resolucao nativa para maxima precisao")

        print()

        # Calibra cada região
        regions_to_calibrate = [
            ("hp_bar", "Região onde aparece seu HP (ex: 450/650)"),
            ("mana_bar", "Região onde aparece seu Mana (ex: 1200/1850)"),
            ("target_hp", "Região onde aparece HP do target/monstro (opcional - ESC para pular)"),
            ("minimap", "MINIMAP COMPLETO - Clique nos cantos do minimapa (quadrado com o mapa)")
        ]

        for region_name, description in regions_to_calibrate:
            success = self.calibrate_region(region_name, description)
            if not success and region_name == "target_hp":
                print("[SKIP] Target HP pulado")
                continue
            elif not success:
                print("[ERRO] Calibracao cancelada")
                return

        cv2.destroyAllWindows()

        # Se calibrou minimap, calibra o centro (posição do player)
        if "minimap" in self.regions:
            self.calibrate_minimap_center()

        # Salva configuração
        self.save_config()

        # Testa OCR
        self.test_ocr()

    def calibrate_minimap_center(self):
        """Calibra o centro do minimap (posição do player)"""
        print("\n" + "=" * 60)
        print("CALIBRAÇÃO DO CENTRO DO MINIMAP")
        print("=" * 60)
        print()
        print("Agora vamos marcar onde está o CENTRO do minimap")
        print("(onde aparece o seu personagem - geralmente uma cruz branca)")
        print()
        print("Clique UMA VEZ no CENTRO do minimap")
        print()

        minimap_region = self.regions["minimap"]

        # Cria imagem temporária com o minimap destacado
        temp_img = self.screenshot.copy()
        x1 = int(minimap_region["x"] * self.display_scale)
        y1 = int(minimap_region["y"] * self.display_scale)
        x2 = int((minimap_region["x"] + minimap_region["width"]) * self.display_scale)
        y2 = int((minimap_region["y"] + minimap_region["height"]) * self.display_scale)

        cv2.rectangle(temp_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(temp_img, "Clique no CENTRO (cruz)", (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        self.temp_screenshot = temp_img
        self.points = []
        self.current_region = "minimap_center"

        cv2.namedWindow('Calibração', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('Calibração', self.temp_screenshot)
        cv2.setMouseCallback('Calibração', self.mouse_callback_single_point)

        # Aguarda 1 click
        while len(self.points) < 1:
            key = cv2.waitKey(1)
            if key == 27:  # ESC
                return

        center_point = self.points[0]

        # Calcula posição relativa ao minimap
        center_x = center_point[0] - minimap_region["x"]
        center_y = center_point[1] - minimap_region["y"]

        # Salva no dicionário de regiões (será usado no save_config)
        self.minimap_center = {
            "x": center_x,
            "y": center_y
        }

        print(f"[OK] Centro do minimap: ({center_x}, {center_y}) relativo ao minimap")
        cv2.waitKey(1000)
        cv2.destroyAllWindows()

    def mouse_callback_single_point(self, event, x, y, flags, param):
        """Callback para 1 único click"""
        if event == cv2.EVENT_LBUTTONDOWN and len(self.points) == 0:
            # Converte para coordenadas originais
            x_original = int(x / self.display_scale)
            y_original = int(y / self.display_scale)

            self.points.append((x_original, y_original))

            # Desenha ponto
            cv2.circle(self.temp_screenshot, (x, y), 5, (0, 0, 255), -1)
            cv2.imshow('Calibração', self.temp_screenshot)

    def save_config(self):
        """Salva configuração em JSON"""
        config_path = "config/bot_settings.json"

        print("\nSalvando configuracao...")

        try:
            # Carrega config existente
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}

            # Atualiza screen_regions (HP, Mana, Target)
            screen_regions = {}
            for key, value in self.regions.items():
                if key != "minimap":  # Minimap vai para seção separada
                    screen_regions[key] = value

            config["screen_regions"] = screen_regions

            # Atualiza configuração do minimap (seção separada)
            if "minimap" in self.regions:
                if "minimap" not in config:
                    config["minimap"] = {}

                config["minimap"]["region"] = {
                    "x": self.regions["minimap"]["x"],
                    "y": self.regions["minimap"]["y"],
                    "width": self.regions["minimap"]["width"],
                    "height": self.regions["minimap"]["height"]
                }

                # Centro do minimap (player)
                if hasattr(self, 'minimap_center'):
                    config["minimap"]["player_center"] = self.minimap_center

            # Salva
            os.makedirs("config", exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print(f"[OK] Configuracao salva: {config_path}")

        except Exception as e:
            print(f"[ERRO] Erro ao salvar: {e}")

    def test_ocr(self):
        """Testa OCR nas regiões calibradas"""
        print("\nTestando OCR...")

        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
            from ocr_reader import OCRReader

            ocr = OCRReader()

            # Testa HP (usa screenshot original)
            if "hp_bar" in self.regions:
                region = self.regions["hp_bar"]
                img = self.screenshot_original[
                    region["y"]:region["y"]+region["height"],
                    region["x"]:region["x"]+region["width"]
                ]
                result = ocr.read_hp(img)
                if result:
                    print(f"[OK] HP: {result[0]}/{result[1]}")
                else:
                    print("[WARN] HP: Nao foi possivel ler")

            # Testa Mana (usa screenshot original)
            if "mana_bar" in self.regions:
                region = self.regions["mana_bar"]
                img = self.screenshot_original[
                    region["y"]:region["y"]+region["height"],
                    region["x"]:region["x"]+region["width"]
                ]
                result = ocr.read_mana(img)
                if result:
                    print(f"[OK] Mana: {result[0]}/{result[1]}")
                else:
                    print("[WARN] Mana: Nao foi possivel ler")

        except Exception as e:
            print(f"[WARN] Erro ao testar OCR: {e}")

        print("\n[OK] Calibracao completa!")
        print("\nProximo passo:")
        print("  py run_bot.py")


if __name__ == "__main__":
    calibrator = VisualCalibrator()
    calibrator.run()

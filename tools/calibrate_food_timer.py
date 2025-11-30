"""
Ferramenta de Calibracao do Food Timer
Permite definir a regiao do timer de comida na tela
"""

import cv2
import numpy as np
import json
import sys
import os
import pytesseract

# Adiciona diretorio pai ao path para importar modulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from screen_capture_obs import OBSScreenCapture
from utils.logger import get_logger

# Configura Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class FoodTimerCalibrator:
    """Calibrador interativo do food timer"""

    def __init__(self, settings_path: str = "config/bot_settings.json"):
        """
        Inicializa calibrador

        Args:
            settings_path: Caminho para bot_settings.json
        """
        self.logger = get_logger()
        self.settings_path = settings_path

        # Carrega settings
        with open(settings_path, 'r') as f:
            self.settings = json.load(f)

        # Inicializa screen capture
        self.screen_capture = OBSScreenCapture(
            camera_index=self.settings["obs_camera"]["device_index"]
        )

        # Pontos selecionados
        self.point1 = None  # Top-left
        self.point2 = None  # Bottom-right

        # Imagem da tela
        self.fullscreen = None
        self.display_img = None

        # Fator de escala para exibicao (tela grande demais)
        self.scale_factor = 0.6

        self.logger.info("Food Timer Calibrator inicializado")

    def capture_screen(self) -> np.ndarray:
        """Captura tela completa"""
        img = self.screen_capture.capture_fullscreen()
        if img is None:
            self.logger.error("Falha ao capturar tela")
            return None
        return img

    def mouse_callback(self, event, x, y, flags, param):
        """Callback para clicks do mouse"""
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.fullscreen is None:
                return

            # Converte coordenadas da janela escalada para coordenadas reais
            real_x = int(x / self.scale_factor)
            real_y = int(y / self.scale_factor)

            if self.point1 is None:
                self.point1 = (real_x, real_y)
                self.logger.info(f"Ponto 1 (top-left): ({real_x}, {real_y})")
                self.logger.info("Agora clique no canto INFERIOR-DIREITO do timer")
            elif self.point2 is None:
                self.point2 = (real_x, real_y)
                self.logger.info(f"Ponto 2 (bottom-right): ({real_x}, {real_y})")

                # Calcula regiao
                x1, y1 = self.point1
                x2, y2 = self.point2

                # Garante que x1 < x2 e y1 < y2
                if x1 > x2:
                    x1, x2 = x2, x1
                if y1 > y2:
                    y1, y2 = y2, y1

                self.point1 = (x1, y1)
                self.point2 = (x2, y2)

                width = x2 - x1
                height = y2 - y1

                self.logger.info(f"Regiao selecionada: x={x1}, y={y1}, width={width}, height={height}")
                self.logger.info("Pressione 't' para testar OCR ou 's' para salvar")

            self.update_display()

    def update_display(self):
        """Atualiza imagem com marcadores"""
        if self.fullscreen is None:
            return

        self.display_img = self.fullscreen.copy()

        # Desenha pontos selecionados
        if self.point1 is not None:
            cv2.circle(self.display_img, self.point1, 5, (0, 255, 0), -1)
            cv2.putText(self.display_img, "1", (self.point1[0] + 10, self.point1[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        if self.point2 is not None:
            cv2.circle(self.display_img, self.point2, 5, (0, 0, 255), -1)
            cv2.putText(self.display_img, "2", (self.point2[0] + 10, self.point2[1]),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Desenha retangulo da regiao
            cv2.rectangle(self.display_img, self.point1, self.point2, (255, 255, 0), 2)

    def preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Preprocessa imagem para OCR do timer MM:SS"""
        # Converte para HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Detecta pixels brancos (texto)
        # Baixa saturacao + alta luminosidade = branco
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 50, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # Amplia imagem
        scale = 4
        resized = cv2.resize(mask, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Operacoes morfologicas
        kernel = np.ones((2, 2), np.uint8)
        resized = cv2.morphologyEx(resized, cv2.MORPH_CLOSE, kernel)
        resized = cv2.morphologyEx(resized, cv2.MORPH_OPEN, kernel)

        # Inverte (Tesseract prefere texto preto em fundo branco)
        inverted = cv2.bitwise_not(resized)

        # Adiciona padding
        padding = 10
        padded = cv2.copyMakeBorder(inverted, padding, padding, padding, padding,
                                    cv2.BORDER_CONSTANT, value=255)

        return padded

    def read_food_timer(self, image: np.ndarray) -> str:
        """Le o food timer usando OCR"""
        # Preprocessa
        processed = self.preprocess_for_ocr(image)

        # Salva debug
        cv2.imwrite("debug_food_timer_processed.png", processed)

        # OCR com whitelist para numeros e ":"
        config = "--psm 7 -c tessedit_char_whitelist=0123456789:"
        text = pytesseract.image_to_string(processed, config=config).strip()

        return text

    def test_ocr(self):
        """Testa OCR na regiao selecionada"""
        if self.point1 is None or self.point2 is None:
            self.logger.error("Selecione os 2 pontos primeiro!")
            return

        x1, y1 = self.point1
        x2, y2 = self.point2
        width = x2 - x1
        height = y2 - y1

        # Captura regiao
        region = self.screen_capture.capture_region(x=x1, y=y1, width=width, height=height)

        if region is None:
            self.logger.error("Falha ao capturar regiao")
            return

        # Salva imagem original
        cv2.imwrite("debug_food_timer_region.png", region)
        self.logger.info("Imagem original salva em debug_food_timer_region.png")

        # Le timer
        timer_text = self.read_food_timer(region)

        self.logger.info(f"[OCR] Texto detectado: '{timer_text}'")

        # Valida formato
        import re
        match = re.match(r'(\d{1,2}):(\d{2})', timer_text)
        if match:
            minutes = match.group(1)
            seconds = match.group(2)
            self.logger.info(f"[OK] Timer valido: {minutes}:{seconds}")

            if timer_text == "00:00" or timer_text == "0:00":
                self.logger.info("[FOOD] Timer zerado! Hora de comer!")
        else:
            self.logger.warning(f"[AVISO] Formato invalido. Esperado MM:SS, obtido: '{timer_text}'")
            self.logger.info("Tente ajustar a regiao ou verificar se o timer esta visivel")

        # Mostra preview da regiao
        preview = cv2.resize(region, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
        cv2.imshow("Food Timer Preview", preview)

    def save_config(self):
        """Salva configuracao no bot_settings.json"""
        if self.point1 is None or self.point2 is None:
            self.logger.error("Selecione os 2 pontos primeiro!")
            return

        x1, y1 = self.point1
        x2, y2 = self.point2
        width = x2 - x1
        height = y2 - y1

        # Atualiza settings
        if "screen_regions" not in self.settings:
            self.settings["screen_regions"] = {}

        self.settings["screen_regions"]["food_timer"] = {
            "x": x1,
            "y": y1,
            "width": width,
            "height": height,
            "_points": {
                "top_left": {"x": x1, "y": y1},
                "bottom_right": {"x": x2, "y": y2}
            }
        }

        # Salva
        with open(self.settings_path, 'w') as f:
            json.dump(self.settings, f, indent=2)

        self.logger.info(f"Configuracao salva em {self.settings_path}")
        self.logger.info(f"  food_timer: x={x1}, y={y1}, width={width}, height={height}")

    def run(self):
        """Loop principal de calibracao"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("CALIBRACAO DO FOOD TIMER")
        self.logger.info("=" * 60)
        self.logger.info("\nInstrucoes:")
        self.logger.info("  1. Clique no canto SUPERIOR-ESQUERDO do timer")
        self.logger.info("  2. Clique no canto INFERIOR-DIREITO do timer")
        self.logger.info("  't' = Testar OCR na regiao selecionada")
        self.logger.info("  'r' = Resetar pontos e recapturar tela")
        self.logger.info("  's' = Salvar configuracao")
        self.logger.info("  'q' ou ESC = Sair")
        self.logger.info("=" * 60 + "\n")

        # Cria janela
        cv2.namedWindow("Calibracao Food Timer")
        cv2.setMouseCallback("Calibracao Food Timer", self.mouse_callback)

        # Captura inicial
        self.fullscreen = self.capture_screen()
        if self.fullscreen is None:
            self.logger.error("Falha ao capturar tela. Verifique se OBS esta rodando.")
            return

        self.update_display()
        self.logger.info("Clique no canto SUPERIOR-ESQUERDO do food timer")

        while True:
            if self.display_img is not None:
                # Escala para caber na tela
                h, w = self.display_img.shape[:2]
                scaled = cv2.resize(self.display_img,
                                   (int(w * self.scale_factor), int(h * self.scale_factor)))

                # Adiciona instrucoes na tela
                if self.point1 is None:
                    text = "Clique no canto SUPERIOR-ESQUERDO"
                elif self.point2 is None:
                    text = "Clique no canto INFERIOR-DIREITO"
                else:
                    text = "Pressione 't' para testar, 's' para salvar"

                cv2.putText(scaled, text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                cv2.imshow("Calibracao Food Timer", scaled)

            key = cv2.waitKey(100) & 0xFF

            if key == ord('q') or key == 27:
                self.logger.info("Encerrando calibrador...")
                break

            elif key == ord('r'):
                self.logger.info("Resetando pontos e recapturando...")
                self.point1 = None
                self.point2 = None
                self.fullscreen = self.capture_screen()
                if self.fullscreen is not None:
                    self.update_display()
                    self.logger.info("Clique no canto SUPERIOR-ESQUERDO do food timer")

            elif key == ord('t'):
                self.test_ocr()

            elif key == ord('s'):
                self.save_config()

        cv2.destroyAllWindows()


def main():
    """Funcao principal"""
    calibrator = FoodTimerCalibrator()
    calibrator.run()


if __name__ == "__main__":
    main()

"""
Ferramenta de calibração para slots de poções
Permite definir a região onde fica a quantidade de cada poção
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import cv2
import json
import numpy as np
from screen_capture_obs import OBSScreenCapture

def load_settings():
    """Carrega settings atuais"""
    settings_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'bot_settings.json')
    with open(settings_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_settings(settings):
    """Salva settings"""
    settings_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'bot_settings.json')
    with open(settings_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

class PotionSlotCalibrator:
    def __init__(self):
        self.settings = load_settings()
        device_index = self.settings["obs_camera"]["device_index"]
        self.capture = OBSScreenCapture(camera_index=device_index)

        self.current_frame = None
        self.drawing = False
        self.start_point = None
        self.current_rect = None
        self.slots = {}  # {"1": {"x": ..., "y": ..., "width": ..., "height": ...}}
        self.current_hotkey = None

        # Carrega slots existentes
        if "potion_slots" in self.settings:
            self.slots = self.settings["potion_slots"].copy()

    def mouse_callback(self, event, x, y, flags, param):
        """Callback do mouse para desenhar retângulos"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_point = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.current_rect = (self.start_point, (x, y))

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            if self.start_point and self.current_hotkey:
                x1, y1 = self.start_point
                x2, y2 = x, y

                # Normaliza (garante x1 < x2, y1 < y2)
                if x1 > x2:
                    x1, x2 = x2, x1
                if y1 > y2:
                    y1, y2 = y2, y1

                self.slots[self.current_hotkey] = {
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1,
                    "_description": f"Slot da poção na tecla {self.current_hotkey}"
                }
                print(f"\n[OK] Slot para tecla '{self.current_hotkey}' definido: x={x1}, y={y1}, {x2-x1}x{y2-y1}")

            self.current_rect = None
            self.start_point = None

    def run(self):
        """Executa calibração interativa"""
        print("=" * 60)
        print("  CALIBRAÇÃO DE SLOTS DE POÇÃO")
        print("=" * 60)
        print()
        print("Instruções:")
        print("1. Pressione a TECLA da poção (1, 2, 3, etc)")
        print("2. Desenhe um RETÂNGULO no slot onde aparece a QUANTIDADE")
        print("   (O número pequeno no canto inferior direito do item)")
        print("3. Repita para cada poção que deseja monitorar")
        print()
        print("Teclas:")
        print("  1-9    = Selecionar slot da poção")
        print("  S      = Salvar e sair")
        print("  R      = Resetar todos os slots")
        print("  ESC    = Sair sem salvar")
        print("=" * 60)

        cv2.namedWindow("Calibrar Slots de Poção", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("Calibrar Slots de Poção", self.mouse_callback)

        while True:
            # Captura frame
            frame = self.capture.capture_fullscreen()
            if frame is None:
                continue

            self.current_frame = frame.copy()
            display = frame.copy()

            # Desenha slots já definidos
            for hotkey, slot in self.slots.items():
                x, y = slot["x"], slot["y"]
                w, h = slot["width"], slot["height"]
                cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(display, f"[{hotkey}]", (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Desenha retângulo sendo desenhado
            if self.current_rect:
                cv2.rectangle(display, self.current_rect[0], self.current_rect[1],
                             (0, 255, 255), 2)

            # Status
            status = f"Tecla selecionada: {self.current_hotkey or 'Nenhuma'}"
            status += f" | Slots definidos: {len(self.slots)}"
            cv2.putText(display, status, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Instrução
            if self.current_hotkey:
                cv2.putText(display, f"Desenhe o retangulo do slot [{self.current_hotkey}]",
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            else:
                cv2.putText(display, "Pressione 1-9 para selecionar a tecla da pocao",
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

            cv2.imshow("Calibrar Slots de Poção", display)

            key = cv2.waitKey(1) & 0xFF

            # Teclas 1-9
            if ord('1') <= key <= ord('9'):
                self.current_hotkey = chr(key)
                print(f"\n[*] Tecla selecionada: {self.current_hotkey}")
                print(f"    Desenhe o retângulo ao redor do NÚMERO de quantidade")

            # Salvar
            elif key == ord('s') or key == ord('S'):
                self.save_slots()
                break

            # Resetar
            elif key == ord('r') or key == ord('R'):
                self.slots = {}
                print("\n[!] Todos os slots resetados")

            # ESC = sair
            elif key == 27:
                print("\n[!] Cancelado - nada foi salvo")
                break

        cv2.destroyAllWindows()

    def save_slots(self):
        """Salva slots no settings"""
        if not self.slots:
            print("\n[!] Nenhum slot definido!")
            return

        self.settings["potion_slots"] = self.slots
        save_settings(self.settings)

        print("\n" + "=" * 60)
        print("  SLOTS SALVOS COM SUCESSO!")
        print("=" * 60)
        for hotkey, slot in self.slots.items():
            print(f"  Tecla [{hotkey}]: x={slot['x']}, y={slot['y']}, "
                  f"{slot['width']}x{slot['height']}")
        print("=" * 60)


if __name__ == "__main__":
    calibrator = PotionSlotCalibrator()
    calibrator.run()

"""
Monitor de Poções
Verifica quantidade de poções antes de usar para evitar spam
"""

import os
import json
import time
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class PotionSlot:
    """Representa um slot de poção"""
    hotkey: str
    x: int
    y: int
    width: int
    height: int
    last_quantity: int = -1  # -1 = nunca lido
    last_check_time: float = 0.0
    is_empty: bool = False
    empty_since: float = 0.0  # Quando ficou vazio


class PotionMonitor:
    """
    Monitora quantidade de poções em slots configurados
    Evita spam quando poção acaba
    """

    def __init__(self, screen_capture, ocr_reader, settings_path: str = "config/bot_settings.json"):
        """
        Inicializa monitor de poções

        Args:
            screen_capture: Instância do OBSScreenCapture
            ocr_reader: Instância do OCRReader
            settings_path: Caminho para configurações
        """
        self.screen_capture = screen_capture
        self.ocr_reader = ocr_reader
        self.slots: Dict[str, PotionSlot] = {}

        # Carrega configurações
        self._load_config(settings_path)

        # Configurações de comportamento
        self.check_interval = 0.5  # Segundos entre verificações do mesmo slot
        self.empty_block_duration = 60.0  # Segundos para bloquear slot vazio
        self.min_quantity_warning = 10  # Avisa quando quantidade < este valor

        print(f"[PotionMonitor] Inicializado com {len(self.slots)} slots configurados")

    def _load_config(self, settings_path: str):
        """Carrega configuração de slots do JSON"""
        try:
            # Resolve caminho relativo
            if not os.path.isabs(settings_path):
                settings_path = os.path.join(os.path.dirname(__file__), '..', settings_path)

            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            potion_slots = settings.get("potion_slots", {})

            for hotkey, slot_data in potion_slots.items():
                if hotkey.startswith("_"):  # Ignora comentários
                    continue

                self.slots[hotkey] = PotionSlot(
                    hotkey=hotkey,
                    x=slot_data["x"],
                    y=slot_data["y"],
                    width=slot_data["width"],
                    height=slot_data["height"]
                )
                print(f"[PotionMonitor] Slot [{hotkey}] configurado: {slot_data['x']},{slot_data['y']} {slot_data['width']}x{slot_data['height']}")

        except FileNotFoundError:
            print(f"[PotionMonitor] Arquivo de configuração não encontrado: {settings_path}")
        except KeyError as e:
            print(f"[PotionMonitor] Configuração 'potion_slots' não encontrada ou incompleta: {e}")
        except Exception as e:
            print(f"[PotionMonitor] Erro ao carregar configuração: {e}")

    def check_slot(self, hotkey: str) -> int:
        """
        Verifica quantidade no slot de uma tecla específica

        Args:
            hotkey: Tecla do slot (ex: "1", "2")

        Returns:
            Quantidade de itens (0 se vazio ou não configurado)
        """
        if hotkey not in self.slots:
            return -1  # Slot não configurado - não bloqueia

        slot = self.slots[hotkey]
        current_time = time.time()

        # Respeita intervalo mínimo entre verificações
        if current_time - slot.last_check_time < self.check_interval:
            return slot.last_quantity

        # Captura região do slot
        slot_img = self.screen_capture.capture_region(
            x=slot.x,
            y=slot.y,
            width=slot.width,
            height=slot.height
        )

        if slot_img is None:
            return slot.last_quantity  # Mantém último valor

        # Verifica se há item no slot
        has_item = self.ocr_reader.has_item_in_slot(slot_img)

        if not has_item:
            # Slot vazio
            quantity = 0
        else:
            # Lê quantidade via OCR
            quantity = self.ocr_reader.read_item_quantity(slot_img)

        # Atualiza estado do slot
        slot.last_quantity = quantity
        slot.last_check_time = current_time

        # Detecta quando slot ficou vazio
        if quantity == 0 and not slot.is_empty:
            slot.is_empty = True
            slot.empty_since = current_time
            print(f"[PotionMonitor] ⚠️ Slot [{hotkey}] ficou VAZIO!")

        elif quantity > 0 and slot.is_empty:
            slot.is_empty = False
            slot.empty_since = 0.0
            print(f"[PotionMonitor] ✅ Slot [{hotkey}] reabastecido: {quantity} itens")

        return quantity

    def can_use_potion(self, hotkey: str) -> bool:
        """
        Verifica se pode usar poção na tecla especificada

        Args:
            hotkey: Tecla da poção

        Returns:
            True se pode usar (tem poção), False se não pode (vazio)
        """
        if hotkey not in self.slots:
            return True  # Slot não configurado - permite uso

        slot = self.slots[hotkey]
        current_time = time.time()

        # Se slot está marcado como vazio, verifica se ainda está bloqueado
        if slot.is_empty:
            time_empty = current_time - slot.empty_since

            # Permite tentar novamente após X segundos (caso tenha reabastecido)
            if time_empty >= self.empty_block_duration:
                # Força nova verificação
                quantity = self.check_slot(hotkey)
                return quantity > 0

            return False  # Ainda bloqueado

        # Verifica quantidade atual
        quantity = self.check_slot(hotkey)

        return quantity > 0 or quantity == -1  # -1 = não conseguiu ler, permite

    def get_quantity(self, hotkey: str) -> int:
        """
        Retorna quantidade atual no slot

        Args:
            hotkey: Tecla do slot

        Returns:
            Quantidade (-1 se não configurado)
        """
        if hotkey not in self.slots:
            return -1

        return self.check_slot(hotkey)

    def get_all_quantities(self) -> Dict[str, int]:
        """
        Retorna quantidade de todos os slots configurados

        Returns:
            Dict com {hotkey: quantidade}
        """
        result = {}
        for hotkey in self.slots:
            result[hotkey] = self.check_slot(hotkey)
        return result

    def get_status_string(self) -> str:
        """
        Retorna string de status para log

        Returns:
            String formatada com status dos slots
        """
        parts = []
        for hotkey, slot in self.slots.items():
            if slot.is_empty:
                parts.append(f"[{hotkey}]: VAZIO")
            elif slot.last_quantity > 0:
                parts.append(f"[{hotkey}]: {slot.last_quantity}")
            else:
                parts.append(f"[{hotkey}]: ?")

        return " | ".join(parts) if parts else "Nenhum slot configurado"

    def reset_slot(self, hotkey: str):
        """
        Reseta estado de um slot (ex: após reabastecer)

        Args:
            hotkey: Tecla do slot
        """
        if hotkey in self.slots:
            slot = self.slots[hotkey]
            slot.is_empty = False
            slot.empty_since = 0.0
            slot.last_quantity = -1
            print(f"[PotionMonitor] Slot [{hotkey}] resetado")

    def reset_all_slots(self):
        """Reseta todos os slots"""
        for hotkey in self.slots:
            self.reset_slot(hotkey)

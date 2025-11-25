"""
Key Sender usando keybd_event (método legado)
Alternativa para quando SendInput é bloqueado
"""

import time
import random
import ctypes

# Virtual Key Codes
VK_CODES = {
    # Function keys
    'F1': 0x70, 'F2': 0x71, 'F3': 0x72, 'F4': 0x73,
    'F5': 0x74, 'F6': 0x75, 'F7': 0x76, 'F8': 0x77,
    'F9': 0x78, 'F10': 0x79, 'F11': 0x7A, 'F12': 0x7B,
    # Numbers
    '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35,
    '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39, '0': 0x30,
    # Modifiers
    'CTRL': 0xA2, 'CONTROL': 0xA2, 'LCTRL': 0xA2, 'RCTRL': 0xA3,
    'ALT': 0xA4, 'LALT': 0xA4, 'RALT': 0xA5,
    'SHIFT': 0xA0, 'LSHIFT': 0xA0, 'RSHIFT': 0xA1,
    # Common keys
    'SPACE': 0x20, 'ENTER': 0x0D, 'ESC': 0x1B, 'TAB': 0x09,
    'BACKSPACE': 0x08, 'DELETE': 0x2E, 'INSERT': 0x2D,
    # Arrow keys
    'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,
    'ARROWUP': 0x26, 'ARROWDOWN': 0x28, 'ARROWLEFT': 0x25, 'ARROWRIGHT': 0x27,
    # Letters (A-Z)
    'A': 0x41, 'B': 0x42, 'C': 0x43, 'D': 0x44, 'E': 0x45, 'F': 0x46,
    'G': 0x47, 'H': 0x48, 'I': 0x49, 'J': 0x4A, 'K': 0x4B, 'L': 0x4C,
    'M': 0x4D, 'N': 0x4E, 'O': 0x4F, 'P': 0x50, 'Q': 0x51, 'R': 0x52,
    'S': 0x53, 'T': 0x54, 'U': 0x55, 'V': 0x56, 'W': 0x57, 'X': 0x58,
    'Y': 0x59, 'Z': 0x5A,
}

# Constantes
KEYEVENTF_KEYUP = 0x0002


class KeySenderLegacy:
    """Envia teclas usando keybd_event (API legado do Windows)"""

    def __init__(self,
                 press_duration_min_ms: int = 30,
                 press_duration_max_ms: int = 80,
                 delay_between_keys_ms: int = 10,
                 debug: bool = False):
        """
        Inicializa KeySender

        Args:
            press_duration_min_ms: Duração mínima do press (ms)
            press_duration_max_ms: Duração máxima do press (ms)
            delay_between_keys_ms: Delay entre teclas (ms)
            debug: Ativa logging detalhado
        """
        self.press_duration_min = press_duration_min_ms / 1000.0
        self.press_duration_max = press_duration_max_ms / 1000.0
        self.delay_between = delay_between_keys_ms / 1000.0
        self.debug = debug

        self.user32 = ctypes.windll.user32
        self.keys_sent = 0
        self.keys_failed = 0

    def press_key(self, key: str) -> bool:
        """
        Pressiona e solta uma tecla usando keybd_event
        Suporta combinações: 'ctrl+space', 'alt+f4', 'shift+1', etc.

        Args:
            key: Tecla (ex: 'F1', 'F9', '1') ou combinação (ex: 'ctrl+space', 'alt+f4')

        Returns:
            True (keybd_event não retorna status)
        """
        # Detecta se é uma combinação de teclas (ex: ctrl+space)
        if '+' in key:
            return self._press_key_combination(key)

        # Tecla simples (código original)
        return self._press_single_key(key)

    def _press_single_key(self, key: str) -> bool:
        """Pressiona uma única tecla (sem modificadores)"""
        # Obtém virtual key code
        vk_code = VK_CODES.get(key.upper())
        if vk_code is None:
            if self.debug:
                print(f"[KeySenderLegacy] ❌ Tecla desconhecida: {key}")
            raise ValueError(f"Tecla desconhecida: {key}")

        # Duração randomizada do press
        press_duration = random.uniform(self.press_duration_min, self.press_duration_max)

        if self.debug:
            print(f"[KeySenderLegacy] Enviando tecla '{key}' (VK=0x{vk_code:02X}) via keybd_event")

        try:
            # Key DOWN
            self.user32.keybd_event(vk_code, 0, 0, 0)
            if self.debug:
                print(f"[KeySenderLegacy] ✅ VK=0x{vk_code:02X} DOWN")

            # Hold
            time.sleep(press_duration)

            # Key UP
            self.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
            if self.debug:
                print(f"[KeySenderLegacy] ✅ VK=0x{vk_code:02X} UP")

            # Delay após tecla
            time.sleep(self.delay_between)

            self.keys_sent += 1
            if self.debug:
                print(f"[KeySenderLegacy] ✅ SUCESSO - Tecla '{key}' (Total: {self.keys_sent})\n")

            return True

        except Exception as e:
            self.keys_failed += 1
            if self.debug:
                print(f"[KeySenderLegacy] ❌ ERRO - {e}\n")
            return False

    def _press_key_combination(self, combination: str) -> bool:
        """
        Pressiona uma combinação de teclas (ex: 'ctrl+space', 'alt+f4')

        Args:
            combination: String com combinação (ex: 'ctrl+space', 'ctrl+shift+s')

        Returns:
            True se sucesso, False se falhou
        """
        # Separa modificadores e tecla principal
        parts = [p.strip().upper() for p in combination.split('+')]

        if len(parts) < 2:
            if self.debug:
                print(f"[KeySenderLegacy] ❌ Combinação inválida: {combination}")
            return False

        # Última parte é a tecla principal, resto são modificadores
        modifiers = parts[:-1]
        main_key = parts[-1]

        # Valida todas as teclas
        modifier_codes = []
        for mod in modifiers:
            vk = VK_CODES.get(mod)
            if vk is None:
                if self.debug:
                    print(f"[KeySenderLegacy] ❌ Modificador desconhecido: {mod}")
                raise ValueError(f"Modificador desconhecido: {mod}")
            modifier_codes.append((mod, vk))

        main_vk = VK_CODES.get(main_key)
        if main_vk is None:
            if self.debug:
                print(f"[KeySenderLegacy] ❌ Tecla principal desconhecida: {main_key}")
            raise ValueError(f"Tecla principal desconhecida: {main_key}")

        press_duration = random.uniform(self.press_duration_min, self.press_duration_max)

        if self.debug:
            print(f"[KeySenderLegacy] Enviando combinação '{combination}' via keybd_event")

        try:
            # 1. Pressiona todos os modificadores (DOWN)
            for mod_name, mod_vk in modifier_codes:
                self.user32.keybd_event(mod_vk, 0, 0, 0)
                if self.debug:
                    print(f"[KeySenderLegacy] ✅ {mod_name} DOWN (VK=0x{mod_vk:02X})")
                time.sleep(0.01)

            # 2. Pressiona tecla principal (DOWN)
            self.user32.keybd_event(main_vk, 0, 0, 0)
            if self.debug:
                print(f"[KeySenderLegacy] ✅ {main_key} DOWN (VK=0x{main_vk:02X})")

            # Hold
            time.sleep(press_duration)

            # 3. Solta tecla principal (UP)
            self.user32.keybd_event(main_vk, 0, KEYEVENTF_KEYUP, 0)
            if self.debug:
                print(f"[KeySenderLegacy] ✅ {main_key} UP (VK=0x{main_vk:02X})")

            time.sleep(0.01)

            # 4. Solta todos os modificadores (UP) em ordem reversa
            for mod_name, mod_vk in reversed(modifier_codes):
                self.user32.keybd_event(mod_vk, 0, KEYEVENTF_KEYUP, 0)
                if self.debug:
                    print(f"[KeySenderLegacy] ✅ {mod_name} UP (VK=0x{mod_vk:02X})")
                time.sleep(0.01)

            # Delay após combinação
            time.sleep(self.delay_between)

            self.keys_sent += 1
            if self.debug:
                print(f"[KeySenderLegacy] ✅ SUCESSO - Combinação '{combination}' (Total: {self.keys_sent})\n")

            return True

        except Exception as e:
            self.keys_failed += 1
            if self.debug:
                print(f"[KeySenderLegacy] ❌ ERRO - {e}\n")
            return False

    def press_keys(self, keys: list[str]):
        """Pressiona múltiplas teclas em sequência"""
        for key in keys:
            self.press_key(key)

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso"""
        return {
            "keys_sent": self.keys_sent,
            "keys_failed": self.keys_failed,
            "success_rate": (self.keys_sent / (self.keys_sent + self.keys_failed) * 100) if (self.keys_sent + self.keys_failed) > 0 else 0
        }

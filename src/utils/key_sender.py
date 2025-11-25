"""
Sistema de Envio de Teclas Humanizado
Usa SendInput API (não detectável) com delays e duração variáveis
"""

import time
import random
import ctypes
from ctypes import wintypes

# Constantes Win32
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

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

# Extended keys (necessitam flag KEYEVENTF_EXTENDEDKEY)
EXTENDED_KEYS = {
    'UP', 'DOWN', 'LEFT', 'RIGHT',
    'ARROWUP', 'ARROWDOWN', 'ARROWLEFT', 'ARROWRIGHT',
    'DELETE', 'INSERT', 'HOME', 'END',
    'PAGEUP', 'PAGEDOWN', 'RCTRL', 'RALT'
}


# Estruturas Win32
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


class KeySender:
    """Envia teclas de forma humanizada usando SendInput API"""

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

    def _send_input(self, vk_code: int, is_keyup: bool = False, is_extended_key: bool = False) -> bool:
        """Envia input usando SendInput API

        Args:
            vk_code: Virtual key code
            is_keyup: True se é key up
            is_extended_key: True para teclas estendidas (setas, etc)

        Returns:
            True se sucesso, False se falhou
        """
        ki = KEYBDINPUT()
        ki.wVk = vk_code
        ki.wScan = 0
        ki.dwFlags = 0

        # Adiciona flag de extended key se necessário
        if is_extended_key:
            ki.dwFlags |= KEYEVENTF_EXTENDEDKEY

        # Adiciona flag de key up se necessário
        if is_keyup:
            ki.dwFlags |= KEYEVENTF_KEYUP

        ki.time = 0
        ki.dwExtraInfo = None

        input_obj = INPUT()
        input_obj.type = INPUT_KEYBOARD
        input_obj.union.ki = ki

        # SendInput retorna o número de eventos inseridos com sucesso
        result = self.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(INPUT))

        if self.debug:
            action = "UP" if is_keyup else "DOWN"
            ext_flag = " [EXTENDED]" if is_extended_key else ""
            status = "✅" if result == 1 else "❌"
            print(f"[KeySender] {status} VK=0x{vk_code:02X} {action}{ext_flag} (result={result})")

        return result == 1

    def press_key(self, key: str) -> bool:
        """
        Pressiona e solta uma tecla de forma humanizada
        Suporta combinações: 'ctrl+space', 'alt+f4', 'shift+1', etc.

        Args:
            key: Tecla (ex: 'F1', 'F9', '1') ou combinação (ex: 'ctrl+space', 'alt+f4')

        Returns:
            True se sucesso, False se falhou
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
                print(f"[KeySender] ❌ Tecla desconhecida: {key}")
            raise ValueError(f"Tecla desconhecida: {key}")

        # Verifica se é extended key
        is_extended = key.upper() in EXTENDED_KEYS

        # Duração randomizada do press
        press_duration = random.uniform(self.press_duration_min, self.press_duration_max)

        if self.debug:
            ext_flag = " [EXTENDED]" if is_extended else ""
            print(f"[KeySender] Enviando tecla '{key}' (VK=0x{vk_code:02X}){ext_flag}")

        # Key DOWN
        down_ok = self._send_input(vk_code, is_keyup=False, is_extended_key=is_extended)

        # Hold
        time.sleep(press_duration)

        # Key UP
        up_ok = self._send_input(vk_code, is_keyup=True, is_extended_key=is_extended)

        # Delay após tecla
        time.sleep(self.delay_between)

        success = down_ok and up_ok
        if success:
            self.keys_sent += 1
        else:
            self.keys_failed += 1

        if self.debug:
            status = "✅ SUCESSO" if success else "❌ FALHOU"
            print(f"[KeySender] {status} - Tecla '{key}' (Total: {self.keys_sent} ok, {self.keys_failed} falhas)\n")

        return success

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
                print(f"[KeySender] ❌ Combinação inválida: {combination}")
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
                    print(f"[KeySender] ❌ Modificador desconhecido: {mod}")
                raise ValueError(f"Modificador desconhecido: {mod}")
            modifier_codes.append((mod, vk))

        main_vk = VK_CODES.get(main_key)
        if main_vk is None:
            if self.debug:
                print(f"[KeySender] ❌ Tecla principal desconhecida: {main_key}")
            raise ValueError(f"Tecla principal desconhecida: {main_key}")

        # Verifica se tecla principal é extended
        main_is_extended = main_key in EXTENDED_KEYS

        press_duration = random.uniform(self.press_duration_min, self.press_duration_max)

        if self.debug:
            print(f"[KeySender] Enviando combinação '{combination}'")

        all_success = True

        # 1. Pressiona todos os modificadores (DOWN)
        for mod_name, mod_vk in modifier_codes:
            mod_is_extended = mod_name in EXTENDED_KEYS
            result = self._send_input(mod_vk, is_keyup=False, is_extended_key=mod_is_extended)
            if self.debug:
                status = "✅" if result else "❌"
                print(f"[KeySender] {status} {mod_name} DOWN (VK=0x{mod_vk:02X})")
            all_success = all_success and result
            time.sleep(0.01)

        # 2. Pressiona tecla principal (DOWN)
        result_main_down = self._send_input(main_vk, is_keyup=False, is_extended_key=main_is_extended)
        if self.debug:
            status = "✅" if result_main_down else "❌"
            print(f"[KeySender] {status} {main_key} DOWN (VK=0x{main_vk:02X})")
        all_success = all_success and result_main_down

        # Hold
        time.sleep(press_duration)

        # 3. Solta tecla principal (UP)
        result_main_up = self._send_input(main_vk, is_keyup=True, is_extended_key=main_is_extended)
        if self.debug:
            status = "✅" if result_main_up else "❌"
            print(f"[KeySender] {status} {main_key} UP (VK=0x{main_vk:02X})")
        all_success = all_success and result_main_up

        time.sleep(0.01)

        # 4. Solta todos os modificadores (UP) em ordem reversa
        for mod_name, mod_vk in reversed(modifier_codes):
            mod_is_extended = mod_name in EXTENDED_KEYS
            result = self._send_input(mod_vk, is_keyup=True, is_extended_key=mod_is_extended)
            if self.debug:
                status = "✅" if result else "❌"
                print(f"[KeySender] {status} {mod_name} UP (VK=0x{mod_vk:02X})")
            all_success = all_success and result
            time.sleep(0.01)

        # Delay após combinação
        time.sleep(self.delay_between)

        if all_success:
            self.keys_sent += 1
        else:
            self.keys_failed += 1

        if self.debug:
            status = "✅ SUCESSO" if all_success else "❌ FALHOU"
            print(f"[KeySender] {status} - Combinação '{combination}' (Total: {self.keys_sent} ok, {self.keys_failed} falhas)\n")

        return all_success

    def press_keys(self, keys: list[str]):
        """
        Pressiona múltiplas teclas em sequência

        Args:
            keys: Lista de teclas
        """
        for key in keys:
            self.press_key(key)

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso"""
        return {
            "keys_sent": self.keys_sent,
            "keys_failed": self.keys_failed,
            "success_rate": (self.keys_sent / (self.keys_sent + self.keys_failed) * 100) if (self.keys_sent + self.keys_failed) > 0 else 0
        }


# Singleton
_key_sender_instance = None


def get_key_sender(method: str = "SendInput", **kwargs):
    """
    Retorna instância singleton do KeySender

    Args:
        method: Método de envio de teclas:
            - "SendInput": API moderna (pode ser bloqueado por jogos)
            - "keybd_event": API legada (mais compatível)
            - "PostMessage": Envia direto para janela do jogo (RECOMENDADO para Tibia)
            - "PyAutoGUI": Simula teclado físico (último recurso, requer foco)
        **kwargs: Argumentos para o KeySender

    Returns:
        KeySender, KeySenderLegacy, KeySenderPostMessage ou KeySenderPyAutoGUI
    """
    global _key_sender_instance
    if _key_sender_instance is None:
        method_lower = method.lower()

        if method_lower == "sendinput":
            _key_sender_instance = KeySender(**kwargs)
        elif method_lower == "keybd_event":
            from .key_sender_legacy import KeySenderLegacy
            _key_sender_instance = KeySenderLegacy(**kwargs)
        elif method_lower == "postmessage":
            from .key_sender_postmessage import KeySenderPostMessage
            _key_sender_instance = KeySenderPostMessage(**kwargs)
        elif method_lower == "pyautogui":
            from .key_sender_pyautogui import KeySenderPyAutoGUI
            _key_sender_instance = KeySenderPyAutoGUI(**kwargs)
        else:
            raise ValueError(f"Método desconhecido: {method}. Use 'SendInput', 'keybd_event', 'PostMessage' ou 'PyAutoGUI'")

    return _key_sender_instance

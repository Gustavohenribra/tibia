"""
Key Sender usando pyautogui
Simula pressionamento físico de teclas (último recurso)
IMPORTANTE: Requer que a janela do jogo esteja em foco
"""

import time
import random

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("⚠️  pyautogui não instalado. Execute: pip install pyautogui")


# Mapeamento de teclas
KEY_MAPPING = {
    # Function keys
    'F1': 'f1', 'F2': 'f2', 'F3': 'f3', 'F4': 'f4',
    'F5': 'f5', 'F6': 'f6', 'F7': 'f7', 'F8': 'f8',
    'F9': 'f9', 'F10': 'f10', 'F11': 'f11', 'F12': 'f12',
    # Numbers
    '1': '1', '2': '2', '3': '3', '4': '4', '5': '5',
    '6': '6', '7': '7', '8': '8', '9': '9', '0': '0',
    # Modifiers
    'CTRL': 'ctrl', 'CONTROL': 'ctrl', 'LCTRL': 'ctrlleft', 'RCTRL': 'ctrlright',
    'ALT': 'alt', 'LALT': 'altleft', 'RALT': 'altright',
    'SHIFT': 'shift', 'LSHIFT': 'shiftleft', 'RSHIFT': 'shiftright',
    # Common keys
    'SPACE': 'space', 'ENTER': 'enter', 'ESC': 'esc', 'TAB': 'tab',
    'BACKSPACE': 'backspace', 'DELETE': 'delete', 'INSERT': 'insert',
    # Arrow keys
    'UP': 'up', 'DOWN': 'down', 'LEFT': 'left', 'RIGHT': 'right',
    'ARROWUP': 'up', 'ARROWDOWN': 'down', 'ARROWLEFT': 'left', 'ARROWRIGHT': 'right',
    # Letters (for K and Q)
    'K': 'k', 'Q': 'q',
}


class KeySenderPyAutoGUI:
    """Envia teclas usando pyautogui (simula teclado físico)"""

    def __init__(self,
                 press_duration_min_ms: int = 30,
                 press_duration_max_ms: int = 80,
                 delay_between_keys_ms: int = 10,
                 debug: bool = False):
        """
        Inicializa KeySender com pyautogui

        Args:
            press_duration_min_ms: Duração mínima do press (ms)
            press_duration_max_ms: Duração máxima do press (ms)
            delay_between_keys_ms: Delay entre teclas (ms)
            debug: Ativa logging detalhado
        """
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("pyautogui não está instalado. Execute: pip install pyautogui")

        self.press_duration_min = press_duration_min_ms / 1000.0
        self.press_duration_max = press_duration_max_ms / 1000.0
        self.delay_between = delay_between_keys_ms / 1000.0
        self.debug = debug

        self.keys_sent = 0
        self.keys_failed = 0

        # Desabilita failsafe (mover mouse para canto não para)
        pyautogui.FAILSAFE = False

        if self.debug:
            print("[PyAutoGUI] ✅ Inicializado (simula teclado físico)")
            print("[PyAutoGUI] ⚠️  IMPORTANTE: A janela do jogo deve estar em FOCO!")

    def press_key(self, key: str) -> bool:
        """
        Pressiona e solta uma tecla usando pyautogui
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
        # Obtém mapeamento de tecla
        pyautogui_key = KEY_MAPPING.get(key.upper())

        if pyautogui_key is None:
            if self.debug:
                print(f"[PyAutoGUI] ❌ Tecla desconhecida: {key}")
            raise ValueError(f"Tecla desconhecida: {key}")

        # Duração randomizada do press
        press_duration = random.uniform(self.press_duration_min, self.press_duration_max)

        if self.debug:
            print(f"[PyAutoGUI] Enviando tecla '{key}' (duration={press_duration:.3f}s)")

        try:
            # Pressiona tecla
            pyautogui.keyDown(pyautogui_key)
            if self.debug:
                print(f"[PyAutoGUI] ✅ {key} DOWN")

            # Hold
            time.sleep(press_duration)

            # Solta tecla
            pyautogui.keyUp(pyautogui_key)
            if self.debug:
                print(f"[PyAutoGUI] ✅ {key} UP")

            # Delay após tecla
            time.sleep(self.delay_between)

            self.keys_sent += 1
            if self.debug:
                print(f"[PyAutoGUI] ✅ SUCESSO - Tecla '{key}' (Total: {self.keys_sent})\n")

            return True

        except Exception as e:
            self.keys_failed += 1
            if self.debug:
                print(f"[PyAutoGUI] ❌ ERRO - {e}\n")
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
                print(f"[PyAutoGUI] ❌ Combinação inválida: {combination}")
            return False

        # Última parte é a tecla principal, resto são modificadores
        modifiers = parts[:-1]
        main_key = parts[-1]

        # Valida e mapeia todas as teclas
        modifier_keys = []
        for mod in modifiers:
            mapped = KEY_MAPPING.get(mod)
            if mapped is None:
                if self.debug:
                    print(f"[PyAutoGUI] ❌ Modificador desconhecido: {mod}")
                raise ValueError(f"Modificador desconhecido: {mod}")
            modifier_keys.append((mod, mapped))

        main_mapped = KEY_MAPPING.get(main_key)
        if main_mapped is None:
            if self.debug:
                print(f"[PyAutoGUI] ❌ Tecla principal desconhecida: {main_key}")
            raise ValueError(f"Tecla principal desconhecida: {main_key}")

        press_duration = random.uniform(self.press_duration_min, self.press_duration_max)

        if self.debug:
            print(f"[PyAutoGUI] Enviando combinação '{combination}' (duration={press_duration:.3f}s)")

        try:
            # 1. Pressiona todos os modificadores (DOWN)
            for mod_name, mod_key in modifier_keys:
                pyautogui.keyDown(mod_key)
                if self.debug:
                    print(f"[PyAutoGUI] ✅ {mod_name} DOWN")
                time.sleep(0.01)

            # 2. Pressiona tecla principal (DOWN)
            pyautogui.keyDown(main_mapped)
            if self.debug:
                print(f"[PyAutoGUI] ✅ {main_key} DOWN")

            # Hold
            time.sleep(press_duration)

            # 3. Solta tecla principal (UP)
            pyautogui.keyUp(main_mapped)
            if self.debug:
                print(f"[PyAutoGUI] ✅ {main_key} UP")

            time.sleep(0.01)

            # 4. Solta todos os modificadores (UP) em ordem reversa
            for mod_name, mod_key in reversed(modifier_keys):
                pyautogui.keyUp(mod_key)
                if self.debug:
                    print(f"[PyAutoGUI] ✅ {mod_name} UP")
                time.sleep(0.01)

            # Delay após combinação
            time.sleep(self.delay_between)

            self.keys_sent += 1
            if self.debug:
                print(f"[PyAutoGUI] ✅ SUCESSO - Combinação '{combination}' (Total: {self.keys_sent})\n")

            return True

        except Exception as e:
            self.keys_failed += 1
            if self.debug:
                print(f"[PyAutoGUI] ❌ ERRO - {e}\n")
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

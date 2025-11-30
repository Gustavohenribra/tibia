"""
Key Sender usando PostMessage/SendMessage
Envia mensagens diretamente para a janela do jogo (mais confiável)
"""

import time
import random
import ctypes
from ctypes import wintypes

# Constantes de mensagens Windows
WM_ACTIVATE = 0x0006
WA_ACTIVE = 1
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102

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

# Scan codes para teclas
SCAN_CODES = {
    # Function keys
    'F1': 0x3B, 'F2': 0x3C, 'F3': 0x3D, 'F4': 0x3E,
    'F5': 0x3F, 'F6': 0x40, 'F7': 0x41, 'F8': 0x42,
    'F9': 0x43, 'F10': 0x44, 'F11': 0x57, 'F12': 0x58,
    # Numbers
    '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
    '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B,
    # Modifiers
    'CTRL': 0x1D, 'CONTROL': 0x1D, 'LCTRL': 0x1D, 'RCTRL': 0x1D,
    'ALT': 0x38, 'LALT': 0x38, 'RALT': 0x38,
    'SHIFT': 0x2A, 'LSHIFT': 0x2A, 'RSHIFT': 0x36,
    # Common keys
    'SPACE': 0x39, 'ENTER': 0x1C, 'ESC': 0x01, 'TAB': 0x0F,
    'BACKSPACE': 0x0E, 'DELETE': 0x53, 'INSERT': 0x52,
    # Arrow keys
    'UP': 0x48, 'DOWN': 0x50, 'LEFT': 0x4B, 'RIGHT': 0x4D,
    'ARROWUP': 0x48, 'ARROWDOWN': 0x50, 'ARROWLEFT': 0x4B, 'ARROWRIGHT': 0x4D,
    # Letters (A-Z scan codes)
    'A': 0x1E, 'B': 0x30, 'C': 0x2E, 'D': 0x20, 'E': 0x12, 'F': 0x21,
    'G': 0x22, 'H': 0x23, 'I': 0x17, 'J': 0x24, 'K': 0x25, 'L': 0x26,
    'M': 0x32, 'N': 0x31, 'O': 0x18, 'P': 0x19, 'Q': 0x10, 'R': 0x13,
    'S': 0x1F, 'T': 0x14, 'U': 0x16, 'V': 0x2F, 'W': 0x11, 'X': 0x2D,
    'Y': 0x15, 'Z': 0x2C,
}

# Extended keys (necessitam bit 24 no lParam)
EXTENDED_KEYS = {
    'UP', 'DOWN', 'LEFT', 'RIGHT',
    'ARROWUP', 'ARROWDOWN', 'ARROWLEFT', 'ARROWRIGHT',
    'DELETE', 'INSERT', 'HOME', 'END',
    'PAGEUP', 'PAGEDOWN', 'RCTRL', 'RALT'
}


class KeySenderPostMessage:
    """Envia teclas usando PostMessage diretamente para a janela do Tibia"""

    def __init__(self,
                 press_duration_min_ms: int = 30,
                 press_duration_max_ms: int = 80,
                 delay_between_keys_ms: int = 10,
                 debug: bool = False,
                 window_title: str = "Tibia"):
        """
        Inicializa KeySender com PostMessage

        Args:
            press_duration_min_ms: Duração mínima do press (ms)
            press_duration_max_ms: Duração máxima do press (ms)
            delay_between_keys_ms: Delay entre teclas (ms)
            debug: Ativa logging detalhado
            window_title: Título da janela do jogo (padrão: "Tibia")
        """
        self.press_duration_min = press_duration_min_ms / 1000.0
        self.press_duration_max = press_duration_max_ms / 1000.0
        self.delay_between = delay_between_keys_ms / 1000.0
        self.debug = debug
        self.window_title = window_title

        self.user32 = ctypes.windll.user32
        self.keys_sent = 0
        self.keys_failed = 0

        # Controle de reconexão automática
        self._consecutive_failures = 0
        self._max_consecutive_failures = 2  # Reconecta após 2 falhas seguidas

        # Encontra janela do Tibia
        self.hwnd = None
        self._find_window()

    def _get_process_name(self, pid: int) -> str:
        """Obtém o nome do processo pelo PID"""
        try:
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                try:
                    # Tenta obter nome do executável
                    buffer = ctypes.create_unicode_buffer(260)
                    size = wintypes.DWORD(260)
                    kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size))
                    full_path = buffer.value
                    # Extrai apenas o nome do arquivo
                    if full_path:
                        return full_path.split('\\')[-1].lower()
                finally:
                    kernel32.CloseHandle(handle)
        except:
            pass
        return ""

    def _find_window(self):
        """Encontra a janela do Tibia (verifica processo para evitar falsos positivos)"""
        self.hwnd = None

        # Lista de processos válidos do Tibia
        valid_processes = ['tibia.exe', 'client.exe']

        # Lista de classes de janela a IGNORAR (não são o jogo)
        invalid_classes = ['chrome_widgetwin_1', 'mozillawindowclass', 'operawindowclass']

        enum_windows_proc = ctypes.WINFUNCTYPE(
            wintypes.BOOL,
            wintypes.HWND,
            wintypes.LPARAM
        )

        candidates = []  # Lista de candidatos (hwnd, title, is_exact_match, is_valid_process)

        def callback(hwnd, lParam):
            # Apenas janelas visíveis
            if not self.user32.IsWindowVisible(hwnd):
                return True

            length = self.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buffer = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buffer, length + 1)
                title = buffer.value

                # Verifica se título contém "Tibia"
                if self.window_title.lower() in title.lower():
                    # Obtém classe da janela
                    class_buffer = ctypes.create_unicode_buffer(256)
                    self.user32.GetClassNameW(hwnd, class_buffer, 256)
                    class_name = class_buffer.value.lower()

                    # IGNORA janelas de navegadores/editores
                    if class_name in invalid_classes:
                        return True

                    # Obtém PID e nome do processo
                    pid = wintypes.DWORD()
                    self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    process_name = self._get_process_name(pid.value)

                    is_exact = (title.lower() == self.window_title.lower())
                    is_valid_process = (process_name in valid_processes)

                    candidates.append((hwnd, title, is_exact, is_valid_process, class_name, process_name))
            return True

        self.user32.EnumWindows(enum_windows_proc(callback), 0)

        # Prioriza: 1) Processo válido + título exato, 2) Processo válido, 3) Título exato, 4) Qualquer
        candidates.sort(key=lambda x: (not x[3], not x[2]))  # is_valid_process DESC, is_exact DESC

        if candidates:
            best = candidates[0]
            self.hwnd = best[0]

            if self.debug:
                print(f"[PostMessage] 🔍 {len(candidates)} janela(s) candidata(s) encontrada(s)")
                for i, (h, t, exact, valid_proc, cls, proc) in enumerate(candidates):
                    marker = "→" if h == self.hwnd else " "
                    proc_status = "✅" if valid_proc else "⚠️"
                    print(f"    {marker} [{i+1}] {proc_status} '{t}' (classe={cls}, processo={proc})")

        if self.debug:
            if self.hwnd:
                length = self.user32.GetWindowTextLengthW(self.hwnd)
                buffer = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(self.hwnd, buffer, length + 1)
                title = buffer.value
                
                class_buffer = ctypes.create_unicode_buffer(256)
                self.user32.GetClassNameW(self.hwnd, class_buffer, 256)
                class_name = class_buffer.value

                pid = wintypes.DWORD()
                self.user32.GetWindowThreadProcessId(self.hwnd, ctypes.byref(pid))

                print(f"[PostMessage] ✅ Janela encontrada (HWND={self.hwnd}):")
                print(f"    Título: '{title}'")
                print(f"    Classe: '{class_name}'")
                print(f"    PID: {pid.value}")
            else:
                print(f"[PostMessage] ⚠️  Janela '{self.window_title}' NÃO encontrada. Teclas podem falhar.")

    def is_hwnd_valid(self) -> bool:
        """
        Verifica se o handle da janela ainda é válido.
        Usa a API IsWindow() do Windows para verificar.

        Returns:
            True se o handle é válido, False caso contrário
        """
        if not self.hwnd:
            return False
        return self.user32.IsWindow(self.hwnd) != 0

    def _reconnect_window(self) -> bool:
        """
        Tenta reconectar à janela do Tibia.

        Returns:
            True se reconectou com sucesso, False caso contrário
        """
        old_hwnd = self.hwnd
        self._find_window()

        if self.hwnd:
            if old_hwnd != self.hwnd:
                print(f"[PostMessage] 🔄 RECONEXÃO: HWND antigo={old_hwnd} -> novo={self.hwnd}")
            return True
        else:
            print(f"[PostMessage] ❌ RECONEXÃO FALHOU: Janela '{self.window_title}' não encontrada!")
            return False

    def _make_lparam(self, scan_code: int, is_keyup: bool = False, is_extended_key: bool = False) -> int:
        """
        Cria lParam para mensagem de teclado

        Args:
            scan_code: Scan code da tecla
            is_keyup: True se é key up, False se é key down
            is_extended_key: True para teclas estendidas (setas, Delete, Insert, etc)

        Returns:
            lParam formatado para WM_KEYDOWN/WM_KEYUP

        Estrutura do lParam (32 bits):
            bits 0-15: repeat count (normalmente 1)
            bits 16-23: scan code
            bit 24: extended key flag (1 se é extended key) ← CRÍTICO PARA SETAS
            bits 25-29: reserved
            bit 30: previous key state
            bit 31: transition state (1 se é key up)
        """
        repeat_count = 1
        flags = 0

        # Bit 24: Extended key flag (necessário para setas funcionarem!)
        if is_extended_key:
            flags |= (1 << 24)  # 0x01000000

        if is_keyup:
            flags |= (1 << 30)  # Previous key state
            flags |= (1 << 31)  # Transition state

        lparam = repeat_count | (scan_code << 16) | flags
        return lparam

    def press_key(self, key: str) -> bool:
        """
        Pressiona e solta uma tecla usando PostMessage
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
        # Obtém virtual key code e scan code
        vk_code = VK_CODES.get(key.upper())
        scan_code = SCAN_CODES.get(key.upper(), 0)

        if vk_code is None:
            if self.debug:
                print(f"[PostMessage] ❌ Tecla desconhecida: {key}")
            raise ValueError(f"Tecla desconhecida: {key}")

        # Verifica se é extended key (setas, delete, insert, etc)
        is_extended = key.upper() in EXTENDED_KEYS

        # VALIDAÇÃO DE HWND: Verifica se handle ainda é válido (não apenas se existe)
        if not self.is_hwnd_valid():
            if self.debug:
                print(f"[PostMessage] ⚠️ HWND inválido detectado, tentando reconectar...")
            if not self._reconnect_window():
                self.keys_failed += 1
                return False

        # Duração randomizada do press
        press_duration = random.uniform(self.press_duration_min, self.press_duration_max)

        if self.debug:
            ext_flag = " [EXTENDED]" if is_extended else ""
            print(f"[PostMessage] Enviando tecla '{key}' (VK=0x{vk_code:02X}, SC=0x{scan_code:02X}){ext_flag} para HWND={self.hwnd}")

        try:
            # Key DOWN (com extended flag se necessário)
            lparam_down = self._make_lparam(scan_code, is_keyup=False, is_extended_key=is_extended)
            result_down = self.user32.PostMessageW(self.hwnd, WM_KEYDOWN, vk_code, lparam_down)

            if self.debug:
                status = "✅" if result_down else "❌"
                print(f"[PostMessage] {status} WM_KEYDOWN (VK=0x{vk_code:02X}, lParam=0x{lparam_down:08X}) result={result_down}")

            # Hold
            time.sleep(press_duration)

            # Key UP (com extended flag se necessário)
            lparam_up = self._make_lparam(scan_code, is_keyup=True, is_extended_key=is_extended)
            result_up = self.user32.PostMessageW(self.hwnd, WM_KEYUP, vk_code, lparam_up)

            if self.debug:
                status = "✅" if result_up else "❌"
                print(f"[PostMessage] {status} WM_KEYUP (VK=0x{vk_code:02X}) result={result_up}")

            # Delay após tecla
            time.sleep(self.delay_between)

            success = result_down and result_up
            if success:
                self.keys_sent += 1
                self._consecutive_failures = 0  # Reset contador de falhas
            else:
                self.keys_failed += 1
                self._consecutive_failures += 1
                # AUTO-RECUPERAÇÃO: Se falhou múltiplas vezes seguidas, tenta reconectar
                if self._consecutive_failures >= self._max_consecutive_failures:
                    print(f"[PostMessage] ⚠️ {self._consecutive_failures} falhas consecutivas detectadas, tentando reconectar...")
                    self._reconnect_window()
                    self._consecutive_failures = 0

            if self.debug:
                status = "✅ SUCESSO" if success else "❌ FALHOU"
                print(f"[PostMessage] {status} - Tecla '{key}' (Total: {self.keys_sent} ok, {self.keys_failed} falhas)\n")

            return success

        except Exception as e:
            self.keys_failed += 1
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._max_consecutive_failures:
                print(f"[PostMessage] ⚠️ {self._consecutive_failures} falhas consecutivas (exceção), tentando reconectar...")
                self._reconnect_window()
                self._consecutive_failures = 0
            if self.debug:
                print(f"[PostMessage] ❌ ERRO - {e}\n")
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
                print(f"[PostMessage] ❌ Combinação inválida: {combination}")
            return False

        # Última parte é a tecla principal, resto são modificadores
        modifiers = parts[:-1]
        main_key = parts[-1]

        # Valida todas as teclas
        modifier_codes = []
        modifier_scans = []
        for mod in modifiers:
            vk = VK_CODES.get(mod)
            sc = SCAN_CODES.get(mod, 0)
            if vk is None:
                if self.debug:
                    print(f"[PostMessage] ❌ Modificador desconhecido: {mod}")
                raise ValueError(f"Modificador desconhecido: {mod}")
            modifier_codes.append((mod, vk, sc))
            modifier_scans.append(sc)

        main_vk = VK_CODES.get(main_key)
        main_sc = SCAN_CODES.get(main_key, 0)
        if main_vk is None:
            if self.debug:
                print(f"[PostMessage] ❌ Tecla principal desconhecida: {main_key}")
            raise ValueError(f"Tecla principal desconhecida: {main_key}")

        # Verifica se tecla principal é extended
        main_is_extended = main_key in EXTENDED_KEYS

        # VALIDAÇÃO DE HWND: Verifica se handle ainda é válido (não apenas se existe)
        if not self.is_hwnd_valid():
            if self.debug:
                print(f"[PostMessage] ⚠️ HWND inválido detectado, tentando reconectar...")
            if not self._reconnect_window():
                self.keys_failed += 1
                return False

        press_duration = random.uniform(self.press_duration_min, self.press_duration_max)

        if self.debug:
            print(f"[PostMessage] Enviando combinação '{combination}' para HWND={self.hwnd}")

        try:
            all_success = True

            # 1. Pressiona todos os modificadores (DOWN)
            for mod_name, mod_vk, mod_sc in modifier_codes:
                # Verifica se modificador é extended (ex: RCTRL, RALT)
                mod_is_extended = mod_name in EXTENDED_KEYS
                lparam = self._make_lparam(mod_sc, is_keyup=False, is_extended_key=mod_is_extended)
                result = self.user32.PostMessageW(self.hwnd, WM_KEYDOWN, mod_vk, lparam)
                if self.debug:
                    status = "✅" if result else "❌"
                    print(f"[PostMessage] {status} {mod_name} DOWN (VK=0x{mod_vk:02X})")
                all_success = all_success and result
                time.sleep(0.01)  # Pequeno delay entre modificadores

            # 2. Pressiona tecla principal (DOWN)
            lparam_main_down = self._make_lparam(main_sc, is_keyup=False, is_extended_key=main_is_extended)
            result_main_down = self.user32.PostMessageW(self.hwnd, WM_KEYDOWN, main_vk, lparam_main_down)
            if self.debug:
                status = "✅" if result_main_down else "❌"
                print(f"[PostMessage] {status} {main_key} DOWN (VK=0x{main_vk:02X})")
            all_success = all_success and result_main_down

            # Hold
            time.sleep(press_duration)

            # 3. Solta tecla principal (UP)
            lparam_main_up = self._make_lparam(main_sc, is_keyup=True, is_extended_key=main_is_extended)
            result_main_up = self.user32.PostMessageW(self.hwnd, WM_KEYUP, main_vk, lparam_main_up)
            if self.debug:
                status = "✅" if result_main_up else "❌"
                print(f"[PostMessage] {status} {main_key} UP (VK=0x{main_vk:02X})")
            all_success = all_success and result_main_up

            time.sleep(0.01)

            # 4. Solta todos os modificadores (UP) em ordem reversa
            for mod_name, mod_vk, mod_sc in reversed(modifier_codes):
                mod_is_extended = mod_name in EXTENDED_KEYS
                lparam = self._make_lparam(mod_sc, is_keyup=True, is_extended_key=mod_is_extended)
                result = self.user32.PostMessageW(self.hwnd, WM_KEYUP, mod_vk, lparam)
                if self.debug:
                    status = "✅" if result else "❌"
                    print(f"[PostMessage] {status} {mod_name} UP (VK=0x{mod_vk:02X})")
                all_success = all_success and result
                time.sleep(0.01)

            # Delay após combinação
            time.sleep(self.delay_between)

            if all_success:
                self.keys_sent += 1
                self._consecutive_failures = 0  # Reset contador de falhas
            else:
                self.keys_failed += 1
                self._consecutive_failures += 1
                # AUTO-RECUPERAÇÃO: Se falhou múltiplas vezes seguidas, tenta reconectar
                if self._consecutive_failures >= self._max_consecutive_failures:
                    print(f"[PostMessage] ⚠️ {self._consecutive_failures} falhas consecutivas detectadas, tentando reconectar...")
                    self._reconnect_window()
                    self._consecutive_failures = 0

            if self.debug:
                status = "✅ SUCESSO" if all_success else "❌ FALHOU"
                print(f"[PostMessage] {status} - Combinação '{combination}' (Total: {self.keys_sent} ok, {self.keys_failed} falhas)\n")

            return all_success

        except Exception as e:
            self.keys_failed += 1
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._max_consecutive_failures:
                print(f"[PostMessage] ⚠️ {self._consecutive_failures} falhas consecutivas (exceção), tentando reconectar...")
                self._reconnect_window()
                self._consecutive_failures = 0
            if self.debug:
                print(f"[PostMessage] ❌ ERRO - {e}\n")
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

    def refresh_window(self):
        """Recarrega handle da janela (útil se o jogo foi reiniciado)"""
        self._find_window()

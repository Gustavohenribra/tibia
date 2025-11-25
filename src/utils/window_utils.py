"""
Utilitários para detectar posição de janelas
"""
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple


class RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long)
    ]


def find_window_by_title(title_contains: str) -> Optional[int]:
    """
    Encontra janela que contém o texto no título

    Args:
        title_contains: Texto que deve estar no título

    Returns:
        Handle da janela (HWND) ou None se não encontrado
    """
    user32 = ctypes.windll.user32

    # Callback para enumerar janelas
    windows = []

    def enum_callback(hwnd, lParam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value

                if title_contains.lower() in title.lower():
                    windows.append((hwnd, title))
        return True

    # Tipo de função callback
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    callback = EnumWindowsProc(enum_callback)

    # Enumera todas as janelas
    user32.EnumWindows(callback, 0)

    if windows:
        # Retorna a primeira janela encontrada
        return windows[0][0]

    return None


def get_window_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """
    Obtém retângulo da janela (posição e tamanho)

    Args:
        hwnd: Handle da janela

    Returns:
        Tupla (left, top, right, bottom) ou None se falhar
    """
    user32 = ctypes.windll.user32
    rect = RECT()

    result = user32.GetWindowRect(hwnd, ctypes.byref(rect))

    if result:
        return (rect.left, rect.top, rect.right, rect.bottom)

    return None


def get_client_rect(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """
    Obtém retângulo da área cliente da janela (sem bordas)

    Args:
        hwnd: Handle da janela

    Returns:
        Tupla (left, top, right, bottom) ou None se falhar
    """
    user32 = ctypes.windll.user32
    rect = RECT()

    result = user32.GetClientRect(hwnd, ctypes.byref(rect))

    if result:
        return (rect.left, rect.top, rect.right, rect.bottom)

    return None


def get_window_offset(hwnd: int) -> Optional[Tuple[int, int]]:
    """
    Calcula offset entre área cliente e janela (tamanho das bordas)

    Args:
        hwnd: Handle da janela

    Returns:
        Tupla (offset_x, offset_y) - quanto adicionar às coordenadas da captura
    """
    user32 = ctypes.windll.user32

    # Posição da janela na tela
    window_rect = get_window_rect(hwnd)
    if not window_rect:
        return None

    # Converte ponto (0,0) da área cliente para coordenadas da tela
    point = wintypes.POINT(0, 0)
    result = user32.ClientToScreen(hwnd, ctypes.byref(point))

    if not result:
        return None

    # O offset é a diferença entre a posição da área cliente e a janela
    offset_x = point.x - window_rect[0]
    offset_y = point.y - window_rect[1]

    return (offset_x, offset_y)


def detect_tibia_window_offset() -> Optional[Tuple[int, int, int, int]]:
    """
    Detecta automaticamente a posição e offset da janela do Tibia

    Returns:
        Tupla (window_x, window_y, offset_x, offset_y) ou None se não encontrado
        - window_x, window_y: Posição da janela na tela
        - offset_x, offset_y: Offset das bordas (quanto adicionar às coordenadas)
    """
    # Tenta encontrar janela do Tibia
    hwnd = find_window_by_title("Tibia")

    if not hwnd:
        return None

    # Pega posição da janela
    window_rect = get_window_rect(hwnd)
    if not window_rect:
        return None

    # Pega offset das bordas
    offset = get_window_offset(hwnd)
    if not offset:
        return None

    return (window_rect[0], window_rect[1], offset[0], offset[1])


# Teste
if __name__ == "__main__":
    print("Procurando janela do Tibia...")
    result = detect_tibia_window_offset()

    if result:
        win_x, win_y, off_x, off_y = result
        print(f"✅ Janela do Tibia encontrada!")
        print(f"   Posição: X={win_x}, Y={win_y}")
        print(f"   Offset bordas: X={off_x}, Y={off_y}")
        print()
        print(f"   Para clicks, adicionar: ({off_x}, {off_y}) às coordenadas OBS")
    else:
        print("❌ Janela do Tibia não encontrada")
        print("   Certifique-se que o Tibia está aberto")

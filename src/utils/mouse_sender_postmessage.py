"""
Mouse Sender usando PostMessage/SendMessage
Envia mensagens de mouse diretamente para a janela do jogo (funciona em segundo plano)
"""

import time
import random
import ctypes
import sys
import os
from ctypes import wintypes
from typing import Tuple, Optional

# Adiciona src ao path para imports funcionarem quando executado diretamente
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.logger import get_logger


# Constantes de mensagens Windows
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208

# Flags para wParam (estado dos botões)
MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002
MK_MBUTTON = 0x0010
MK_SHIFT = 0x0004
MK_CONTROL = 0x0008

# Mapeamento de botões
BUTTON_MESSAGES = {
    'left': (WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON),
    'right': (WM_RBUTTONDOWN, WM_RBUTTONUP, MK_RBUTTON),
    'middle': (WM_MBUTTONDOWN, WM_MBUTTONUP, MK_MBUTTON),
}


class RECT(ctypes.Structure):
    """Estrutura RECT do Windows"""
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long)
    ]


class POINT(ctypes.Structure):
    """Estrutura POINT do Windows"""
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long)
    ]


class MouseSenderPostMessage:
    """Envia clicks do mouse usando PostMessage diretamente para a janela do Tibia"""

    def __init__(self,
                 click_duration_min_ms: int = 50,
                 click_duration_max_ms: int = 100,
                 position_variance_px: int = 2,
                 delay_between_clicks_ms: int = 100,
                 obs_resolution: Tuple[int, int] = None,
                 debug: bool = False,
                 window_title: str = "Tibia"):
        """
        Inicializa MouseSender com PostMessage

        Args:
            click_duration_min_ms: Duração mínima do click (ms)
            click_duration_max_ms: Duração máxima do click (ms)
            position_variance_px: Variação aleatória da posição (pixels)
            delay_between_clicks_ms: Delay entre clicks (ms)
            obs_resolution: Tupla (width, height) da captura OBS. Se None, assume mesma da tela
            debug: Ativa logging detalhado
            window_title: Título da janela do jogo (padrão: "Tibia")
        """
        self.logger = get_logger()
        self.click_duration_min = click_duration_min_ms / 1000.0
        self.click_duration_max = click_duration_max_ms / 1000.0
        self.position_variance = position_variance_px
        self.delay_between = delay_between_clicks_ms / 1000.0
        self.debug = debug
        self.window_title = window_title

        self.user32 = ctypes.windll.user32
        self.clicks_sent = 0
        self.clicks_failed = 0

        # Configuração de escala OBS → Client Area (será calculado em _find_window)
        if obs_resolution is not None:
            self.obs_width, self.obs_height = obs_resolution
        else:
            # Se não especificado, assume 1920x1080 como base padrão ou usa a tela
            self.obs_width = 1920
            self.obs_height = 1080
        
        self.scale_x = 1.0
        self.scale_y = 1.0

        # Encontra janela do Tibia e obtém posição
        self.hwnd = None
        self.window_x = 0
        self.window_y = 0
        self.client_x = 0
        self.client_y = 0
        self._find_window()

        if self.debug:
            self.logger.info("🖱️  MouseSenderPostMessage inicializado")
            self.logger.info(f"   Duração: {click_duration_min_ms}-{click_duration_max_ms}ms")
            self.logger.info(f"   Variação de posição: ±{position_variance_px}px")
            self.logger.info(f"   Janela: '{window_title}' (HWND={self.hwnd})")

    def _find_window(self):
        """Encontra a janela do Tibia, obtém sua posição e recalcula escalas"""
        # Tenta encontrar janela exata
        self.hwnd = self.user32.FindWindowW(None, self.window_title)

        if not self.hwnd:
            # Tenta encontrar janela que contenha "Tibia" no título
            enum_windows_proc = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HWND,
                wintypes.LPARAM
            )

            def callback(hwnd, lParam):
                if self.user32.IsWindowVisible(hwnd):
                    length = self.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        self.user32.GetWindowTextW(hwnd, buffer, length + 1)
                        title = buffer.value
                        if self.window_title.lower() in title.lower():
                            self.hwnd = hwnd
                            return False  # Para a enumeração
                return True

            self.user32.EnumWindows(enum_windows_proc(callback), 0)

        # Obtém posição da janela e recalcula escala
        self.client_x = 0
        self.client_y = 0
        
        if self.hwnd:
            # 1. Posição da Janela
            rect = RECT()
            result = self.user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
            if result:
                self.window_x = rect.left
                self.window_y = rect.top
                
                # 2. Posição da Área Cliente (Global)
                pt = POINT(0, 0)
                self.user32.ClientToScreen(self.hwnd, ctypes.byref(pt))
                self.client_x = pt.x
                self.client_y = pt.y

                # 3. Dimensões da Área Cliente (para escala)
                client_rect = RECT()
                self.user32.GetClientRect(self.hwnd, ctypes.byref(client_rect))
                client_w = client_rect.right - client_rect.left
                client_h = client_rect.bottom - client_rect.top

                # 4. Calcula Escala (Client Dimensions / OBS Dimensions)
                if self.obs_width > 0 and self.obs_height > 0:
                    self.scale_x = client_w / self.obs_width
                    self.scale_y = client_h / self.obs_height
                
                if self.debug:
                    length = self.user32.GetWindowTextLengthW(self.hwnd)
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    self.user32.GetWindowTextW(self.hwnd, buffer, length + 1)
                    title = buffer.value
                    
                    self.logger.info(f"[PostMessage] ✅ Janela encontrada (HWND={self.hwnd}):")
                    self.logger.info(f"    Título: '{title}'")
                    self.logger.info(f"    Window Pos: ({self.window_x}, {self.window_y})")
                    self.logger.info(f"    Client Pos: ({self.client_x}, {self.client_y})")
                    self.logger.info(f"    Client Size: {client_w}x{client_h}")
                    self.logger.info(f"    OBS Size:    {self.obs_width}x{self.obs_height}")
                    self.logger.info(f"    Escala:      X={self.scale_x:.4f}, Y={self.scale_y:.4f}")
        else:
            if self.debug:
                self.logger.warning(f"[PostMessage] ⚠️  Janela '{self.window_title}' NÃO encontrada. Clicks podem falhar.")

    def _obs_to_screen(self, obs_x: int, obs_y: int) -> Tuple[int, int]:
        """
        Converte coordenadas OBS para coordenadas da tela real

        Args:
            obs_x: Coordenada X na captura OBS
            obs_y: Coordenada Y na captura OBS

        Returns:
            Tuple (screen_x, screen_y) em pixels da tela real
        """
        screen_x = int(obs_x * self.scale_x)
        screen_y = int(obs_y * self.scale_y)
        return (screen_x, screen_y)

    def _screen_to_window(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        Converte coordenadas da tela para coordenadas relativas à janela
        
        Args:
            screen_x: Coordenada X em pixels da tela
            screen_y: Coordenada Y em pixels da tela
            
        Returns:
            Tuple (window_x, window_y) relativas ao canto superior esquerdo da área cliente
        """
        # PostMessage espera coordenadas relativas à ÁREA CLIENTE (não à janela com bordas)
        # self.client_x/y são as coordenadas de tela do canto superior esquerdo da área cliente
        window_x = screen_x - self.client_x
        window_y = screen_y - self.client_y
        return (window_x, window_y)

    def _make_lparam(self, x: int, y: int) -> int:
        """
        Cria lParam para mensagem de mouse

        Args:
            x: Coordenada X relativa à janela
            y: Coordenada Y relativa à janela

        Returns:
            lParam formatado para mensagens de mouse

        Estrutura do lParam (32 bits):
            bits 0-15: coordenada X (LOWORD)
            bits 16-31: coordenada Y (HIWORD)
        """
        # Garante que valores são válidos (limita a 16 bits com sinal)
        x = max(-32768, min(32767, x))
        y = max(-32768, min(32767, y))

        # Converte para unsigned 16-bit se necessário
        if x < 0:
            x = x & 0xFFFF
        if y < 0:
            y = y & 0xFFFF

        lparam = (y << 16) | (x & 0xFFFF)
        return lparam

    def _add_position_variance(self, x: int, y: int) -> Tuple[int, int]:
        """
        Adiciona variação aleatória à posição

        Args:
            x: Coordenada X original
            y: Coordenada Y original

        Returns:
            Tuple (x_varied, y_varied)
        """
        if self.position_variance <= 0:
            return (x, y)

        # Variação gaussiana (mais natural)
        variance_x = random.gauss(0, self.position_variance / 2)
        variance_y = random.gauss(0, self.position_variance / 2)

        # Limita variação máxima
        variance_x = max(-self.position_variance, min(self.position_variance, variance_x))
        variance_y = max(-self.position_variance, min(self.position_variance, variance_y))

        new_x = int(x + variance_x)
        new_y = int(y + variance_y)

        return (new_x, new_y)

    def click_at(self, x: int, y: int, button: str = 'left') -> bool:
        """
        Clica em uma posição absoluta da tela com humanização

        Args:
            x: Coordenada X (pixels, coordenadas OBS se configurado)
            y: Coordenada Y (pixels, coordenadas OBS se configurado)
            button: Botão do mouse ('left', 'right', 'middle')

        Returns:
            True se sucesso, False se falhou
        """
        try:
            if button not in BUTTON_MESSAGES:
                raise ValueError(f"Botão desconhecido: {button}. Use 'left', 'right' ou 'middle'")

            # Verifica se janela existe
            if not self.hwnd:
                self._find_window()
                if not self.hwnd:
                    if self.debug:
                        self.logger.warning(f"[PostMessage] ❌ Janela '{self.window_title}' não encontrada!")
                    self.clicks_failed += 1
                    return False

            # PASSO 1: Converte OBS → Tela Real (se necessário)
            screen_x, screen_y = self._obs_to_screen(x, y)

            # PASSO 2: Adiciona variação de posição
            varied_x, varied_y = self._add_position_variance(screen_x, screen_y)

            # PASSO 3: Converte para coordenadas relativas à janela
            window_x, window_y = self._screen_to_window(varied_x, varied_y)

            # PASSO 4: Cria lParam
            lparam = self._make_lparam(window_x, window_y)

            # Duração aleatória
            duration = random.uniform(self.click_duration_min, self.click_duration_max)

            # Obtém mensagens do botão
            msg_down, msg_up, mk_button = BUTTON_MESSAGES[button]

            if self.debug:
                obs_str = f"OBS({x},{y}) → " if self.scale_x != 1.0 else ""
                offset_str = f" (offset: {varied_x-screen_x:+d}, {varied_y-screen_y:+d})" if (varied_x != screen_x or varied_y != screen_y) else ""
                self.logger.debug(
                    f"🖱️  Click {button} em {obs_str}Tela({screen_x},{screen_y}){offset_str} "
                    f"→ Window({window_x},{window_y}) [duração: {duration*1000:.0f}ms]"
                )

            # 1. Move o mouse para a posição (mais realista)
            result_move = self.user32.PostMessageW(self.hwnd, WM_MOUSEMOVE, 0, lparam)
            if self.debug:
                status = "✅" if result_move else "❌"
                self.logger.debug(f"[PostMessage] {status} WM_MOUSEMOVE (x={window_x}, y={window_y}) result={result_move}")

            # Pequeno delay após movimento
            time.sleep(0.01)

            # 2. Pressiona botão (DOWN)
            result_down = self.user32.PostMessageW(self.hwnd, msg_down, mk_button, lparam)
            if self.debug:
                status = "✅" if result_down else "❌"
                self.logger.debug(f"[PostMessage] {status} BUTTON_DOWN result={result_down}")

            # 3. Hold (duração do click)
            time.sleep(duration)

            # 4. Solta botão (UP)
            result_up = self.user32.PostMessageW(self.hwnd, msg_up, 0, lparam)
            if self.debug:
                status = "✅" if result_up else "❌"
                self.logger.debug(f"[PostMessage] {status} BUTTON_UP result={result_up}")

            # Delay após click
            time.sleep(self.delay_between)

            success = result_move and result_down and result_up
            if success:
                self.clicks_sent += 1
                if self.debug:
                    self.logger.debug(f"✅ Click executado com sucesso")
            else:
                self.clicks_failed += 1
                if self.debug:
                    self.logger.warning(f"⚠️ Click parcialmente falhou (move={result_move}, down={result_down}, up={result_up})")

            return success

        except Exception as e:
            self.logger.error(f"❌ Erro ao clicar em ({x}, {y}): {e}")
            self.clicks_failed += 1
            return False

    def click_minimap(self,
                      minimap_x: int,
                      minimap_y: int,
                      minimap_region_x: int,
                      minimap_region_y: int,
                      button: str = 'left') -> bool:
        """
        Clica em posição relativa ao minimapa

        Args:
            minimap_x: Coordenada X relativa ao minimapa (0 = esquerda do minimapa)
            minimap_y: Coordenada Y relativa ao minimapa (0 = topo do minimapa)
            minimap_region_x: Coordenada X absoluta do canto superior esquerdo do minimapa
            minimap_region_y: Coordenada Y absoluta do canto superior esquerdo do minimapa
            button: Botão do mouse ('left', 'right', 'middle')

        Returns:
            True se sucesso, False se falhou
        """
        # Converte coordenada relativa → absoluta
        absolute_x = minimap_region_x + minimap_x
        absolute_y = minimap_region_y + minimap_y

        if self.debug:
            self.logger.debug(
                f"🗺️  Click no minimapa: relativo ({minimap_x}, {minimap_y}) "
                f"→ absoluto ({absolute_x}, {absolute_y})"
            )

        return self.click_at(absolute_x, absolute_y, button)

    def double_click_at(self, x: int, y: int, button: str = 'left') -> bool:
        """
        Double click em posição absoluta

        Args:
            x: Coordenada X
            y: Coordenada Y
            button: Botão do mouse

        Returns:
            True se sucesso
        """
        try:
            # Primeiro click
            success1 = self.click_at(x, y, button)

            # Intervalo entre clicks (50-100ms)
            time.sleep(random.uniform(0.05, 0.1))

            # Segundo click (mesma posição, com variação própria)
            success2 = self.click_at(x, y, button)

            return success1 and success2

        except Exception as e:
            self.logger.error(f"❌ Erro ao double-clicar em ({x}, {y}): {e}")
            return False

    def move_to(self, x: int, y: int, duration_ms: int = 200) -> bool:
        """
        Move o mouse para uma posição (sem clicar)

        NOTA: PostMessage NÃO move o cursor visível!
        Esta função envia WM_MOUSEMOVE mas o cursor real não se move.

        Args:
            x: Coordenada X em pixels (coordenadas OBS se configurado)
            y: Coordenada Y em pixels (coordenadas OBS se configurado)
            duration_ms: Duração do movimento (ignorado no PostMessage)

        Returns:
            True se sucesso
        """
        try:
            if not self.hwnd:
                self._find_window()
                if not self.hwnd:
                    return False

            # Converte OBS → Tela → Window
            screen_x, screen_y = self._obs_to_screen(x, y)
            varied_x, varied_y = self._add_position_variance(screen_x, screen_y)
            window_x, window_y = self._screen_to_window(varied_x, varied_y)

            # Cria lParam
            lparam = self._make_lparam(window_x, window_y)

            # Envia WM_MOUSEMOVE
            result = self.user32.PostMessageW(self.hwnd, WM_MOUSEMOVE, 0, lparam)

            if self.debug:
                status = "✅" if result else "❌"
                self.logger.debug(f"🖱️  {status} Move para Window({window_x}, {window_y})")

            return result

        except Exception as e:
            self.logger.error(f"❌ Erro ao mover mouse para ({x}, {y}): {e}")
            return False

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso"""
        total = self.clicks_sent + self.clicks_failed
        success_rate = (self.clicks_sent / total * 100) if total > 0 else 0

        return {
            "clicks_sent": self.clicks_sent,
            "clicks_failed": self.clicks_failed,
            "success_rate": success_rate
        }

    def refresh_window(self):
        """Recarrega handle e posição da janela (útil se o jogo foi reiniciado ou movido)"""
        self._find_window()


# Teste
if __name__ == "__main__":
    print("=" * 60)
    print("TESTE: MouseSenderPostMessage")
    print("=" * 60)
    print()
    print("IMPORTANTE: Certifique-se que o Tibia esta aberto!")
    print()

    mouse = MouseSenderPostMessage(debug=True)

    if not mouse.hwnd:
        print()
        print("[ERRO] Janela do Tibia NAO encontrada!")
        print("       Verifique se o Tibia esta aberto")
        print("       Titulo da janela deve conter: 'Tibia'")
    else:
        print()
        print("[OK] Janela do Tibia encontrada!")
        print(f"     HWND: {mouse.hwnd}")
        print(f"     Posicao: ({mouse.window_x}, {mouse.window_y})")
        print()
        print("Testando click em 3 segundos...")
        print("NOTA: O cursor NAO vai mover - isso e normal no PostMessage")
        print()

        for i in range(3, 0, -1):
            print(f"  {i}...")
            time.sleep(1)

        # Click no centro da tela (coordenadas OBS)
        test_x = 960  # Centro horizontal (1920/2)
        test_y = 540  # Centro vertical (1080/2)
        print()
        print(f"[TESTE] Clicando em OBS({test_x}, {test_y})...")
        success = mouse.click_at(test_x, test_y)

        print()
        if success:
            print("[OK] Click enviado com sucesso!")
        else:
            print("[ERRO] Falha ao enviar click")

        print()
        print("Estatisticas:")
        stats = mouse.get_stats()
        print(f"  Clicks enviados: {stats['clicks_sent']}")
        print(f"  Clicks falhos: {stats['clicks_failed']}")
        print(f"  Taxa de sucesso: {stats['success_rate']:.1f}%")

"""
Sistema de Envio de Clicks do Mouse Humanizado
Usa SendInput API nativa do Windows (não detectável) com posição e duração variáveis
"""

import time
import random
import ctypes
from ctypes import wintypes
from typing import Tuple
from utils.logger import get_logger


# Constantes Win32
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000

# Mapeamento de botões
BUTTON_EVENTS = {
    'left': (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    'right': (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    'middle': (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


# Estruturas Win32
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


class MouseSender:
    """Envia clicks do mouse de forma humanizada usando SendInput API"""

    def __init__(self,
                 click_duration_min_ms: int = 50,
                 click_duration_max_ms: int = 100,
                 position_variance_px: int = 2,
                 delay_between_clicks_ms: int = 100,
                 obs_resolution: Tuple[int, int] = None,
                 debug: bool = False):
        """
        Inicializa MouseSender

        Args:
            click_duration_min_ms: Duração mínima do click (ms)
            click_duration_max_ms: Duração máxima do click (ms)
            position_variance_px: Variação aleatória da posição (pixels)
            delay_between_clicks_ms: Delay entre clicks (ms)
            obs_resolution: Tupla (width, height) da captura OBS. Se None, assume mesma da tela
            debug: Ativa logging detalhado
        """
        self.logger = get_logger()
        self.click_duration_min = click_duration_min_ms / 1000.0
        self.click_duration_max = click_duration_max_ms / 1000.0
        self.position_variance = position_variance_px
        self.delay_between = delay_between_clicks_ms / 1000.0
        self.debug = debug

        # Estatísticas
        self.clicks_sent = 0
        self.clicks_failed = 0

        # Acesso às APIs Win32
        self.user32 = ctypes.windll.user32

        # Obtém dimensões da tela REAL para cálculos absolutos
        self.screen_width = self.user32.GetSystemMetrics(0)
        self.screen_height = self.user32.GetSystemMetrics(1)

        # Configuração de escala OBS → Tela Real
        if obs_resolution is not None:
            self.obs_width, self.obs_height = obs_resolution
            self.scale_x = self.screen_width / self.obs_width
            self.scale_y = self.screen_height / self.obs_height
            self.logger.info("🎥 Conversão OBS → Tela Real ATIVADA")
            self.logger.info(f"   OBS: {self.obs_width}x{self.obs_height}")
            self.logger.info(f"   Tela Real: {self.screen_width}x{self.screen_height}")
            self.logger.info(f"   Escala: X={self.scale_x:.4f}, Y={self.scale_y:.4f}")
        else:
            self.obs_width = self.screen_width
            self.obs_height = self.screen_height
            self.scale_x = 1.0
            self.scale_y = 1.0

        # Sem offset (Tibia em fullscreen)
        self.window_offset_x = 0
        self.window_offset_y = 0

        if self.debug:
            self.logger.info("🖱️  MouseSender inicializado (SendInput nativo)")
            self.logger.info(f"   Duração: {click_duration_min_ms}-{click_duration_max_ms}ms")
            self.logger.info(f"   Variação de posição: ±{position_variance_px}px")
            self.logger.info(f"   Resolução Tela: {self.screen_width}x{self.screen_height}")

    def _obs_to_screen(self, obs_x: int, obs_y: int) -> Tuple[int, int]:
        """
        Converte coordenadas OBS para coordenadas da tela real
        Aplica escala (Tibia em fullscreen, sem offset)

        Args:
            obs_x: Coordenada X na captura OBS
            obs_y: Coordenada Y na captura OBS

        Returns:
            Tuple (screen_x, screen_y) em pixels da tela real
        """
        # Aplica escala (normalmente 1.0 se resoluções iguais)
        screen_x = int(obs_x * self.scale_x)
        screen_y = int(obs_y * self.scale_y)

        return (screen_x, screen_y)

    def _screen_to_absolute(self, x: int, y: int) -> Tuple[int, int]:
        """
        Converte coordenadas de tela (pixels) para coordenadas absolutas do SendInput
        SendInput usa escala 0-65535 independente da resolução

        Args:
            x: Coordenada X em pixels
            y: Coordenada Y em pixels

        Returns:
            Tuple (abs_x, abs_y) em escala 0-65535
        """
        abs_x = int((x * 65535) / self.screen_width)
        abs_y = int((y * 65535) / self.screen_height)
        return (abs_x, abs_y)

    def _send_mouse_input(self, abs_x: int, abs_y: int, flags: int) -> bool:
        """
        Envia input de mouse usando SendInput API

        Args:
            abs_x: Coordenada X absoluta (0-65535)
            abs_y: Coordenada Y absoluta (0-65535)
            flags: Flags de evento do mouse (MOUSEEVENTF_*)

        Returns:
            True se sucesso, False se falhou
        """
        mi = MOUSEINPUT()
        mi.dx = abs_x
        mi.dy = abs_y
        mi.mouseData = 0
        mi.dwFlags = flags
        mi.time = 0
        mi.dwExtraInfo = None

        input_obj = INPUT()
        input_obj.type = INPUT_MOUSE
        input_obj.union.mi = mi

        # SendInput retorna o número de eventos inseridos com sucesso
        result = self.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(INPUT))

        if self.debug:
            flag_names = []
            if flags & MOUSEEVENTF_ABSOLUTE:
                flag_names.append("ABSOLUTE")
            if flags & MOUSEEVENTF_MOVE:
                flag_names.append("MOVE")
            if flags & MOUSEEVENTF_LEFTDOWN:
                flag_names.append("LDOWN")
            if flags & MOUSEEVENTF_LEFTUP:
                flag_names.append("LUP")
            if flags & MOUSEEVENTF_RIGHTDOWN:
                flag_names.append("RDOWN")
            if flags & MOUSEEVENTF_RIGHTUP:
                flag_names.append("RUP")
            if flags & MOUSEEVENTF_MIDDLEDOWN:
                flag_names.append("MDOWN")
            if flags & MOUSEEVENTF_MIDDLEUP:
                flag_names.append("MUP")

            status = "✅" if result == 1 else "❌"
            self.logger.debug(
                f"[MouseSender] {status} pos=({abs_x}, {abs_y}) "
                f"flags={' | '.join(flag_names)} (result={result})"
            )

        return result == 1

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

        # Variação gaussiana (mais natural que uniforme)
        variance_x = random.gauss(0, self.position_variance / 2)
        variance_y = random.gauss(0, self.position_variance / 2)

        # Limita variação máxima
        variance_x = max(-self.position_variance, min(self.position_variance, variance_x))
        variance_y = max(-self.position_variance, min(self.position_variance, variance_y))

        new_x = int(x + variance_x)
        new_y = int(y + variance_y)

        return (new_x, new_y)

    def move_to(self, x: int, y: int, duration_ms: int = 200) -> bool:
        """
        Move o mouse para uma posição (sem clicar)

        Args:
            x: Coordenada X em pixels (coordenadas OBS se configurado)
            y: Coordenada Y em pixels (coordenadas OBS se configurado)
            duration_ms: Duração do movimento (ms)

        Returns:
            True se sucesso
        """
        try:
            # PASSO 1: Converte OBS → Tela Real (se necessário)
            screen_x, screen_y = self._obs_to_screen(x, y)

            # PASSO 2: Adiciona variação
            varied_x, varied_y = self._add_position_variance(screen_x, screen_y)

            # PASSO 3: Converte para coordenadas absolutas SendInput
            abs_x, abs_y = self._screen_to_absolute(varied_x, varied_y)

            if self.debug:
                offset_str = f" (offset: {varied_x-x:+d}, {varied_y-y:+d})" if (varied_x != x or varied_y != y) else ""
                self.logger.debug(f"🖱️  Movendo mouse para ({varied_x}, {varied_y}){offset_str}")

            # Move para a posição
            flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
            result = self._send_mouse_input(abs_x, abs_y, flags)

            # Simula tempo de movimento (opcional, pode remover se quiser instantâneo)
            if duration_ms > 0:
                time.sleep(duration_ms / 1000.0)

            return result

        except Exception as e:
            self.logger.error(f"❌ Erro ao mover mouse para ({x}, {y}): {e}")
            return False

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
            if button not in BUTTON_EVENTS:
                raise ValueError(f"Botão desconhecido: {button}. Use 'left', 'right' ou 'middle'")

            # PASSO 1: Converte OBS → Tela Real (se necessário)
            screen_x, screen_y = self._obs_to_screen(x, y)

            # PASSO 2: Adiciona variação de posição
            varied_x, varied_y = self._add_position_variance(screen_x, screen_y)

            # PASSO 3: Converte para coordenadas absolutas SendInput
            abs_x, abs_y = self._screen_to_absolute(varied_x, varied_y)

            # Duração aleatória
            duration = random.uniform(self.click_duration_min, self.click_duration_max)

            if self.debug:
                obs_str = f"OBS({x},{y}) → " if self.scale_x != 1.0 else ""
                offset_str = f" (offset: {varied_x-screen_x:+d}, {varied_y-screen_y:+d})" if (varied_x != screen_x or varied_y != screen_y) else ""
                self.logger.debug(
                    f"🖱️  Click {button} em {obs_str}Tela({screen_x},{screen_y}){offset_str} "
                    f"[duração: {duration*1000:.0f}ms]"
                )

            # 1. Move o mouse para a posição (MUITO IMPORTANTE - parece mais humano)
            flags_move = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
            move_ok = self._send_mouse_input(abs_x, abs_y, flags_move)

            # Pequeno delay após movimento
            time.sleep(0.01)

            # 2. Pressiona botão (DOWN)
            down_flag, up_flag = BUTTON_EVENTS[button]
            flags_down = down_flag | MOUSEEVENTF_ABSOLUTE
            down_ok = self._send_mouse_input(abs_x, abs_y, flags_down)

            # 3. Hold (duração do click)
            time.sleep(duration)

            # 4. Solta botão (UP)
            flags_up = up_flag | MOUSEEVENTF_ABSOLUTE
            up_ok = self._send_mouse_input(abs_x, abs_y, flags_up)

            # Delay após click
            time.sleep(self.delay_between)

            success = move_ok and down_ok and up_ok
            if success:
                self.clicks_sent += 1
                if self.debug:
                    self.logger.debug(f"✅ Click executado com sucesso")
            else:
                self.clicks_failed += 1
                if self.debug:
                    self.logger.warning(f"⚠️ Click parcialmente falhou (move={move_ok}, down={down_ok}, up={up_ok})")

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

    def get_position(self) -> Tuple[int, int]:
        """
        Obtém posição atual do mouse

        Returns:
            Tuple (x, y)
        """
        point = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return (point.x, point.y)

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso"""
        total = self.clicks_sent + self.clicks_failed
        success_rate = (self.clicks_sent / total * 100) if total > 0 else 0

        return {
            "clicks_sent": self.clicks_sent,
            "clicks_failed": self.clicks_failed,
            "success_rate": success_rate
        }


# Singleton
_mouse_sender_instance = None


def get_mouse_sender(method: str = "SendInput", **kwargs):
    """
    Retorna instância singleton do MouseSender

    Args:
        method: Método de envio de clicks:
            - "SendInput": API moderna, move cursor visível (REQUER FOCO)
            - "PostMessage": Envia direto para janela, NÃO move cursor (FUNCIONA EM SEGUNDO PLANO)
        **kwargs: Argumentos para o MouseSender

    Returns:
        MouseSender ou MouseSenderPostMessage
    """
    global _mouse_sender_instance
    if _mouse_sender_instance is None:
        method_lower = method.lower()

        if method_lower == "sendinput":
            _mouse_sender_instance = MouseSender(**kwargs)
        elif method_lower == "postmessage":
            from .mouse_sender_postmessage import MouseSenderPostMessage
            _mouse_sender_instance = MouseSenderPostMessage(**kwargs)
        else:
            raise ValueError(f"Método desconhecido: {method}. Use 'SendInput' ou 'PostMessage'")

    return _mouse_sender_instance


# Teste
if __name__ == "__main__":
    print("🖱️  Testando MouseSender com SendInput nativo...")
    print("Mova o mouse para o local desejado e pressione ENTER")
    input()

    mouse = MouseSender(debug=True)

    print(f"Posição atual: {mouse.get_position()}")
    print("Clicando em 2 segundos...")
    time.sleep(2)

    pos = mouse.get_position()
    mouse.click_at(pos[0], pos[1])

    print(f"Estatísticas: {mouse.get_stats()}")

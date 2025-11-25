"""
Captura de Tela via OBS Virtual Camera
Otimizado para baixa latência e precisão
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class OBSScreenCapture:
    """Captura tela via OBS Virtual Camera (índice 5)"""

    def __init__(self, camera_index: int = 5):
        """
        Inicializa captura via OBS

        Args:
            camera_index: Índice da câmera OBS (padrão: 5)
        """
        self.camera_index = camera_index
        self.cap = None
        self._initialize()

    def _initialize(self):
        """Inicializa conexão com OBS Virtual Camera"""
        try:
            # CAP_DSHOW permite configurar resolução alta no Windows
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

            if not self.cap.isOpened():
                raise RuntimeError(f"Falha ao abrir OBS Virtual Camera (índice {self.camera_index})")

            # Configura resolução alta (1920x1080)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            # Buffer mínimo para menor latência
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Testa captura
            ret, frame = self.cap.read()
            if not ret or frame is None:
                raise RuntimeError("OBS Virtual Camera não retorna frames")

            h, w = frame.shape[:2]
            print(f"[OK] OBS Virtual Camera conectado: {w}x{h}")

        except Exception as e:
            print(f"[ERRO] Erro ao inicializar OBS: {e}")
            print("       Verifique se OBS está rodando com Virtual Camera ativa")
            raise

    def is_available(self) -> bool:
        """Verifica se OBS está disponível"""
        return self.cap is not None and self.cap.isOpened()

    def capture_fullscreen(self) -> Optional[np.ndarray]:
        """
        Captura frame completo

        Returns:
            Frame como numpy array (BGR) ou None
        """
        if not self.is_available():
            return None

        try:
            ret, frame = self.cap.read()
            return frame if ret else None

        except Exception as e:
            print(f"[ERRO] Erro ao capturar frame: {e}")
            return None

    def capture_region(self, x: int, y: int, width: int, height: int) -> Optional[np.ndarray]:
        """
        Captura região específica

        Args:
            x, y: Coordenadas
            width, height: Dimensões

        Returns:
            Região como numpy array (BGR) ou None
        """
        full = self.capture_fullscreen()
        if full is None:
            return None

        # Valida limites
        h, w = full.shape[:2]
        if x < 0 or y < 0 or x + width > w or y + height > h:
            return None

        # Recorta região
        return full[y:y+height, x:x+width]

    def get_resolution(self) -> Optional[Tuple[int, int]]:
        """Retorna resolução (width, height)"""
        frame = self.capture_fullscreen()
        if frame is None:
            return None

        h, w = frame.shape[:2]
        return (w, h)

    def __del__(self):
        """Cleanup"""
        if self.cap is not None:
            self.cap.release()

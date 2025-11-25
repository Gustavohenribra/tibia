"""
OCR Reader Otimizado para Tibia
Pré-processamento avançado para precisão 99%+
"""

import cv2
import numpy as np
import pytesseract
import re
import os
from typing import Optional, Tuple
from dataclasses import dataclass

# Configura caminho do Tesseract (caminho padrão Windows)
if os.name == 'nt':  # Windows
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path


@dataclass
class Stats:
    """Estatísticas do personagem e combate"""
    hp_current: int
    hp_max: int
    mana_current: int
    mana_max: int
    hp_percent: float
    mana_percent: float
    has_creatures_nearby: bool = False  # Criaturas na Battle List (sem aro)
    in_active_combat: bool = False      # Criatura selecionada (com aro vermelho)


class OCRReader:
    """Leitor OCR otimizado para HP/Mana"""

    def __init__(self,
                 tesseract_config: str = "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789/",
                 resize_scale: float = 5.0,
                 threshold_min: int = 160,
                 threshold_max: int = 255,
                 debug: bool = False):
        """
        Inicializa OCR Reader

        Args:
            tesseract_config: Configuração do Tesseract (PSM 7 = linha única)
            resize_scale: Escala de resize (4x para máxima precisão)
            threshold_min: Threshold mínimo para binarização
            threshold_max: Threshold máximo
            debug: Se True, salva imagens processadas para debug
        """
        self.config = tesseract_config
        self.resize_scale = resize_scale
        self.threshold_min = threshold_min
        self.threshold_max = threshold_max
        self.debug = debug

        # Cache (evita reprocessar mesma imagem)
        self._last_hp_image = None
        self._last_hp_result = None
        self._last_mana_image = None
        self._last_mana_result = None

    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        """
        Aplica sharpening para melhorar definição dos caracteres

        Args:
            image: Imagem de entrada

        Returns:
            Imagem com sharpening aplicado
        """
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        return cv2.filter2D(image, -1, kernel)

    def _preprocess_hp(self, image: np.ndarray, name: str = "") -> np.ndarray:
        """
        Pré-processamento ESPECÍFICO para HP (otimizado para fundo verde)

        Args:
            image: Imagem BGR
            name: Nome para debug (salva imagem processada)

        Returns:
            Imagem processada (texto preto em fundo branco)
        """
        # 0. CROP vertical - Remove primeiros pixels superiores (área da textura da barra)
        #    As linhas de ruído aparecem nos primeiros 20-25% da altura
        crop_top = int(image.shape[0] * 0.25)  # Remove 25% superior
        cropped_image = image[crop_top:, :]  # Mantém de crop_top até o final

        # 1. SHARPENING para melhorar definição
        sharpened = self._sharpen(cropped_image)

        # 2. Detecção de BRANCO RGB PURO
        #    Pixels brancos verdadeiros: B, G e R TODOS muito altos
        #    Pixels esverdeados da barra: G alto, mas B e R mais baixos
        b, g, r = cv2.split(sharpened)

        # Cada canal deve ser > 220 para ser considerado branco puro
        _, mask_b = cv2.threshold(b, 220, 255, cv2.THRESH_BINARY)
        _, mask_g = cv2.threshold(g, 220, 255, cv2.THRESH_BINARY)
        _, mask_r = cv2.threshold(r, 220, 255, cv2.THRESH_BINARY)

        # BRANCO = B AND G AND R todos altos
        mask_temp = cv2.bitwise_and(mask_b, mask_g)
        mask = cv2.bitwise_and(mask_temp, mask_r)

        # 4. Resize 6x (maior que mana para compensar possível perda de qualidade)
        h, w = mask.shape
        new_w = int(w * 6.0)  # 6x scale
        new_h = int(h * 6.0)
        resized = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        # 5. Morfologia moderada
        # Primeiro: REMOVE ruído pequeno
        kernel_open = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(resized, cv2.MORPH_OPEN, kernel_open, iterations=2)

        # Segundo: fecha buracos nos números
        kernel_close = np.ones((3,3), np.uint8)
        closed = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_close)

        # Terceiro: limpeza final
        kernel_open_final = np.ones((2,2), np.uint8)
        final_clean = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_open_final)

        # 6. INVERTE cores
        inverted = cv2.bitwise_not(final_clean)

        # 7. CROP AUTOMÁTICO
        coords = cv2.findNonZero(cv2.bitwise_not(inverted))
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            margin = 10
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(inverted.shape[1] - x, w + 2*margin)
            h = min(inverted.shape[0] - y, h + 2*margin)
            cropped = inverted[y:y+h, x:x+w]
        else:
            cropped = inverted

        # 8. Padding generoso
        padded = cv2.copyMakeBorder(cropped, 15, 15, 15, 15,
                                    cv2.BORDER_CONSTANT, value=255)

        # Debug
        if self.debug and name:
            cv2.imwrite(f"debug_{name}.png", padded)

        return padded

    def _preprocess(self, image: np.ndarray, name: str = "") -> np.ndarray:
        """
        Pré-processamento GENÉRICO para números brancos em fundo colorido (usado para Mana)

        Args:
            image: Imagem BGR
            name: Nome para debug (salva imagem processada)

        Returns:
            Imagem processada (texto preto em fundo branco)
        """
        # 1. Converte BGR para HSV para detecção de cor BRANCA
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # 2. BRANCO = Baixa saturação + Alta luminosidade
        #    Isso elimina verde (alta saturação) e azul (alta saturação)
        #    Mantém apenas pixels brancos puros

        # Máscara 1: Saturação BAIXA (< 50 = pouca cor = branco/cinza)
        _, mask_low_sat = cv2.threshold(s, 50, 255, cv2.THRESH_BINARY_INV)

        # Máscara 2: Luminosidade ALTA (> 200 = claro)
        _, mask_high_val = cv2.threshold(v, 200, 255, cv2.THRESH_BINARY)

        # 3. Combina: Baixa saturação AND Alta luminosidade = BRANCO PURO
        mask = cv2.bitwise_and(mask_low_sat, mask_high_val)

        # 4. Resize 4x ANTES de processar (melhor qualidade)
        h, w = mask.shape
        new_w = int(w * self.resize_scale)
        new_h = int(h * self.resize_scale)
        resized = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        # 5. Fecha pequenos buracos nos números (kernel maior = mais preenchimento)
        kernel_close = np.ones((3,3), np.uint8)
        closed = cv2.morphologyEx(resized, cv2.MORPH_CLOSE, kernel_close)

        # 6. Remove ruído pequeno (pontos isolados)
        kernel_open = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_open)

        # 7. INVERTE cores (Tesseract espera texto PRETO em fundo BRANCO)
        inverted = cv2.bitwise_not(cleaned)

        # 8. CROP AUTOMÁTICO - Remove áreas vazias (laterais pretas)
        #    Encontra bounding box do conteúdo (pixels pretos = números)
        coords = cv2.findNonZero(cv2.bitwise_not(inverted))
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            # Adiciona margem pequena
            margin = 5
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(inverted.shape[1] - x, w + 2*margin)
            h = min(inverted.shape[0] - y, h + 2*margin)
            cropped = inverted[y:y+h, x:x+w]
        else:
            cropped = inverted

        # 9. Padding (Tesseract funciona melhor com bordas)
        padded = cv2.copyMakeBorder(cropped, 10, 10, 10, 10,
                                    cv2.BORDER_CONSTANT, value=255)

        # Debug: Salva imagem processada
        if self.debug and name:
            cv2.imwrite(f"debug_{name}.png", padded)

        return padded

    def _ocr(self, image: np.ndarray) -> str:
        """
        Executa OCR na imagem com múltiplas tentativas

        Args:
            image: Imagem pré-processada

        Returns:
            Texto extraído
        """
        try:
            # Tenta com PSM 7 (linha única) - padrão
            text = pytesseract.image_to_string(image, config=self.config)
            if self.debug:
                print(f"[DEBUG] OCR PSM 7 retornou: '{text.strip()}'")

            # Se não funcionou, tenta com PSM 13 (linha única raw)
            if not text.strip() or '/' not in text:
                config_psm13 = "--psm 13 --oem 3 -c tessedit_char_whitelist=0123456789/"
                text = pytesseract.image_to_string(image, config=config_psm13)
                if self.debug:
                    print(f"[DEBUG] OCR PSM 13 retornou: '{text.strip()}'")

            # Se ainda não funcionou, tenta com PSM 8 (palavra única)
            if not text.strip() or '/' not in text:
                config_psm8 = "--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789/"
                text = pytesseract.image_to_string(image, config=config_psm8)
                if self.debug:
                    print(f"[DEBUG] OCR PSM 8 retornou: '{text.strip()}'")

            return text.strip()
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Erro OCR: {e}")
            return ""

    def _parse_hp_mana(self, text: str) -> Optional[Tuple[int, int]]:
        """
        Parse texto HP/Mana (formato: "450/650")

        Args:
            text: Texto OCR

        Returns:
            Tupla (current, max) ou None
        """
        # Regex para formato número/número
        match = re.search(r'(\d+)\s*/\s*(\d+)', text)
        if match:
            current = int(match.group(1))
            maximum = int(match.group(2))

            # Validação de sanidade
            if 0 <= current <= maximum and maximum <= 100000:
                return (current, maximum)

        return None

    def read_hp(self, image: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Lê HP da imagem (usa pré-processamento específico otimizado para fundo verde)

        Args:
            image: Região do HP

        Returns:
            Tupla (current, max) ou None
        """
        # Cache check
        if self._last_hp_image is not None and np.array_equal(image, self._last_hp_image):
            return self._last_hp_result

        # Pré-processa com método ESPECÍFICO para HP
        processed = self._preprocess_hp(image, name="hp")

        # OCR
        text = self._ocr(processed)

        # Parse
        result = self._parse_hp_mana(text)

        # Cache
        self._last_hp_image = image.copy()
        self._last_hp_result = result

        return result

    def read_mana(self, image: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Lê Mana da imagem

        Args:
            image: Região do Mana

        Returns:
            Tupla (current, max) ou None
        """
        # Cache check
        if self._last_mana_image is not None and np.array_equal(image, self._last_mana_image):
            return self._last_mana_result

        # Pré-processa com debug
        processed = self._preprocess(image, name="mana")

        # OCR
        text = self._ocr(processed)

        # Parse
        result = self._parse_hp_mana(text)

        # Cache
        self._last_mana_image = image.copy()
        self._last_mana_result = result

        return result

    def detect_creatures_nearby(self, battle_list_image: np.ndarray) -> bool:
        """
        Detecta se há criaturas próximas (na Battle List, sem aro vermelho)

        Analisa APENAS:
        - Barra VERDE de HP do monstro
        - Texto BRANCO do nome

        IGNORA vermelho (aro de combate)

        Args:
            battle_list_image: Região da Battle List

        Returns:
            True se há criaturas listadas (sem estarem selecionadas)
        """
        if battle_list_image is None or battle_list_image.size == 0:
            return False

        # Converte para HSV
        hsv = cv2.cvtColor(battle_list_image, cv2.COLOR_BGR2HSV)
        total_pixels = battle_list_image.shape[0] * battle_list_image.shape[1]

        # Detecta VERDE (barra HP do monstro)
        green_mask = cv2.inRange(hsv, np.array([35, 80, 80]), np.array([85, 255, 255]))
        green_pixels = cv2.countNonZero(green_mask)

        # Detecta BRANCO (nome da criatura)
        h, s, v = cv2.split(hsv)
        _, white_sat = cv2.threshold(s, 30, 255, cv2.THRESH_BINARY_INV)
        _, white_val = cv2.threshold(v, 200, 255, cv2.THRESH_BINARY)
        white_mask = cv2.bitwise_and(white_sat, white_val)
        white_pixels = cv2.countNonZero(white_mask)

        # Combina verde + branco (sem vermelho!)
        combined = cv2.bitwise_or(green_mask, white_mask)
        detected_pixels = cv2.countNonZero(combined)
        detection_percent = (detected_pixels / total_pixels) * 100

        # Threshold: > 2% = há criaturas na lista
        return detection_percent > 2.0

    def detect_active_combat(self, battle_list_image: np.ndarray) -> bool:
        """
        Detecta se está em combate ATIVO (criatura selecionada com aro)

        Analisa TODOS os tons do aro:
        - Vermelho (H: 0-10, 170-180)
        - Laranja avermelhado (H: 10-20)
        - Laranja (H: 20-30)

        Args:
            battle_list_image: Região da Battle List

        Returns:
            True se há aro (combate ativo)
        """
        if battle_list_image is None or battle_list_image.size == 0:
            return False

        # Converte para HSV
        hsv = cv2.cvtColor(battle_list_image, cv2.COLOR_BGR2HSV)
        total_pixels = battle_list_image.shape[0] * battle_list_image.shape[1]

        # Detecta ARO de combate (vermelho/laranja/laranja escuro)
        # Range expandido para cobrir todos os tons do aro
        # Saturação e Value reduzidos para pegar variações de luminosidade

        # Vermelho puro (0-10)
        red_mask1 = cv2.inRange(hsv, np.array([0, 60, 80]), np.array([10, 255, 255]))

        # Laranja avermelhado + Laranja (10-30)
        orange_mask = cv2.inRange(hsv, np.array([10, 60, 80]), np.array([30, 255, 255]))

        # Vermelho escuro (wrap around 170-180)
        red_mask2 = cv2.inRange(hsv, np.array([170, 60, 80]), np.array([180, 255, 255]))

        # Combina todos os tons avermelhados/alaranjados
        combat_mask = cv2.bitwise_or(red_mask1, orange_mask)
        combat_mask = cv2.bitwise_or(combat_mask, red_mask2)

        combat_pixels = cv2.countNonZero(combat_mask)
        combat_percent = (combat_pixels / total_pixels) * 100

        # Threshold: > 1% de pixels do aro = em combate
        return combat_percent > 1.0

    def read_stats(self, hp_image: np.ndarray, mana_image: np.ndarray,
                   battle_list_image: Optional[np.ndarray] = None) -> Optional[Stats]:
        """
        Lê HP, Mana e detecta estado de combate

        Args:
            hp_image: Região do HP
            mana_image: Região do Mana
            battle_list_image: Região da Battle List (opcional)

        Returns:
            Stats object ou None
        """
        hp_data = self.read_hp(hp_image)
        mana_data = self.read_mana(mana_image)

        if hp_data is None or mana_data is None:
            return None

        hp_current, hp_max = hp_data
        mana_current, mana_max = mana_data

        hp_percent = (hp_current / hp_max * 100) if hp_max > 0 else 0
        mana_percent = (mana_current / mana_max * 100) if mana_max > 0 else 0

        # Detecta estado de combate (dual)
        has_creatures_nearby = False
        in_active_combat = False

        if battle_list_image is not None:
            has_creatures_nearby = self.detect_creatures_nearby(battle_list_image)
            in_active_combat = self.detect_active_combat(battle_list_image)

        return Stats(
            hp_current=hp_current,
            hp_max=hp_max,
            mana_current=mana_current,
            mana_max=mana_max,
            hp_percent=hp_percent,
            mana_percent=mana_percent,
            has_creatures_nearby=has_creatures_nearby,
            in_active_combat=in_active_combat
        )

"""
OCR Reader Otimizado para Tibia
Pre-processamento avancado para precisao 99%+
"""

import cv2
import numpy as np
import pytesseract
import re
import os
import json
from typing import Optional, Tuple, Dict, Any
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
            tesseract_config: Configuracao do Tesseract (PSM 7 = linha unica)
            resize_scale: Escala de resize (4x para maxima precisao)
            threshold_min: Threshold minimo para binarizacao
            threshold_max: Threshold maximo
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

        # Carrega configuracoes de deteccao do aro de combate
        self._halo_config = self._load_halo_config()

    def _load_halo_config(self) -> Dict[str, Any]:
        """Carrega configuracoes de deteccao do aro de combate do bot_settings.json"""
        default_config = {
            "enabled": True,
            "border_thickness": 4,
            "border_density_threshold": 5.0,
            "ratio_threshold": 1.5,
            "hsv_ranges": {
                "red1": {"h_lower": 0, "h_upper": 10, "s_lower": 100, "s_upper": 255, "v_lower": 100, "v_upper": 255},
                "orange": {"h_lower": 10, "h_upper": 25, "s_lower": 100, "s_upper": 255, "v_lower": 100, "v_upper": 255},
                "red2": {"h_lower": 170, "h_upper": 180, "s_lower": 100, "s_upper": 255, "v_lower": 100, "v_upper": 255}
            }
        }

        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'bot_settings.json')
            with open(config_path, 'r') as f:
                settings = json.load(f)
                halo_config = settings.get("combat", {}).get("combat_halo_detection", {})
                if halo_config:
                    # Merge com defaults
                    for key in default_config:
                        if key not in halo_config:
                            halo_config[key] = default_config[key]
                    return halo_config
        except Exception:
            pass

        return default_config

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
        Detecta se esta em combate ATIVO (criatura selecionada com aro)

        O aro de combate do Tibia forma um RETANGULO PERFEITO ao redor do
        slot da criatura selecionada. Esta funcao detecta esse padrao usando
        deteccao de CONTORNOS com cores BGR EXATAS (sem HSV).

        Args:
            battle_list_image: Regiao da Battle List

        Returns:
            True se ha aro de combate (contorno retangular) detectado
        """
        if battle_list_image is None or battle_list_image.size == 0:
            return False

        # Carrega configuracoes
        cfg = self._halo_config

        # Cria mascara usando cores BGR exatas (sem conversao HSV)
        bgr_colors = cfg.get("bgr_colors", [
            [0, 0, 255],    # Vermelho puro
            [0, 0, 200],    # Vermelho escuro
            [0, 50, 255],   # Vermelho-laranja
            [0, 100, 255],  # Laranja
            [0, 128, 255],  # Laranja claro
            [0, 165, 255]   # Laranja amarelado
        ])
        tolerance = cfg.get("color_tolerance", 30)

        # Cria mascara combinando todas as cores BGR
        combat_mask = np.zeros(battle_list_image.shape[:2], dtype=np.uint8)

        for bgr in bgr_colors:
            lower = np.array([max(0, c - tolerance) for c in bgr], dtype=np.uint8)
            upper = np.array([min(255, c + tolerance) for c in bgr], dtype=np.uint8)
            color_mask = cv2.inRange(battle_list_image, lower, upper)
            combat_mask = cv2.bitwise_or(combat_mask, color_mask)

        # === DETECCAO DE CONTORNO RETANGULAR ===
        # O aro forma um retangulo/quadrado grande na mascara
        # Sem aro: apenas pixels esparsos das sprites (contornos pequenos)

        # Encontra contornos na mascara
        contours, _ = cv2.findContours(combat_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Parametros do aro esperado
        min_contour_area = cfg.get("min_contour_area", 350)  # Area minima do contorno

        for contour in contours:
            area = cv2.contourArea(contour)

            # Aro detectado se houver um contorno grande o suficiente
            # (area >= 350 pixels indica o quadrado do aro)
            if area >= min_contour_area:
                if self.debug:
                    x, y, cw, ch = cv2.boundingRect(contour)
                    aspect_ratio = cw / ch if ch > 0 else 0
                    print(f"[HALO] Aro detectado: area={area:.0f} ratio={aspect_ratio:.2f}")
                return True

        return False

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

    def _preprocess_food_timer(self, image: np.ndarray, name: str = "") -> np.ndarray:
        """
        Pre-processamento especifico para o food timer (formato MM:SS)

        Args:
            image: Imagem BGR do food timer
            name: Nome para debug

        Returns:
            Imagem processada para OCR
        """
        # Converte para HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Detecta BRANCO = baixa saturacao + alta luminosidade
        _, mask_low_sat = cv2.threshold(s, 50, 255, cv2.THRESH_BINARY_INV)
        _, mask_high_val = cv2.threshold(v, 180, 255, cv2.THRESH_BINARY)

        # Combina mascaras
        mask = cv2.bitwise_and(mask_low_sat, mask_high_val)

        # Resize 4x
        scale = 4
        h, w = mask.shape
        resized = cv2.resize(mask, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

        # Morfologia
        kernel = np.ones((2, 2), np.uint8)
        resized = cv2.morphologyEx(resized, cv2.MORPH_CLOSE, kernel)
        resized = cv2.morphologyEx(resized, cv2.MORPH_OPEN, kernel)

        # Inverte
        inverted = cv2.bitwise_not(resized)

        # Auto crop
        coords = cv2.findNonZero(cv2.bitwise_not(inverted))
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            margin = 5
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(inverted.shape[1] - x, w + 2*margin)
            h = min(inverted.shape[0] - y, h + 2*margin)
            cropped = inverted[y:y+h, x:x+w]
        else:
            cropped = inverted

        # Padding
        padded = cv2.copyMakeBorder(cropped, 10, 10, 10, 10,
                                    cv2.BORDER_CONSTANT, value=255)

        if self.debug and name:
            cv2.imwrite(f"debug_{name}.png", padded)

        return padded

    def read_food_timer(self, image: np.ndarray) -> Optional[str]:
        """
        Le o food timer no formato MM:SS

        Args:
            image: Imagem da regiao do food timer

        Returns:
            String no formato "MM:SS" (ex: "05:30") ou None se falhar
        """
        if image is None or image.size == 0:
            return None

        # Preprocessa
        processed = self._preprocess_food_timer(image, name="food_timer")

        # OCR com whitelist para numeros e ":"
        config = "--psm 7 -c tessedit_char_whitelist=0123456789:"

        try:
            text = pytesseract.image_to_string(processed, config=config).strip()

            if self.debug:
                print(f"[DEBUG] Food timer OCR: '{text}'")

            # Valida formato MM:SS ou M:SS
            match = re.match(r'^(\d{1,2}):(\d{2})$', text)
            if match:
                minutes = match.group(1)
                seconds = match.group(2)
                return f"{minutes}:{seconds}"

            # Tenta com PSM 8 se falhar
            config_psm8 = "--psm 8 -c tessedit_char_whitelist=0123456789:"
            text = pytesseract.image_to_string(processed, config=config_psm8).strip()

            match = re.match(r'^(\d{1,2}):(\d{2})$', text)
            if match:
                minutes = match.group(1)
                seconds = match.group(2)
                return f"{minutes}:{seconds}"

        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Erro food timer OCR: {e}")

        return None

    def is_food_timer_empty(self, timer: Optional[str]) -> bool:
        """
        Verifica se o food timer esta zerado (00:00 ou 0:00)

        Args:
            timer: String do timer no formato MM:SS

        Returns:
            True se timer zerado, False caso contrario
        """
        if timer is None:
            return False
        return timer in ("00:00", "0:00")

    def _preprocess_item_quantity(self, image: np.ndarray, name: str = "") -> np.ndarray:
        """
        Pre-processamento para quantidade de item (numero pequeno no canto do slot)
        Os numeros sao BRANCOS ou AMARELOS em fundo escuro

        Args:
            image: Imagem BGR do slot/quantidade
            name: Nome para debug

        Returns:
            Imagem processada para OCR
        """
        # Converte para HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Detecta BRANCO (baixa saturacao + alta luminosidade)
        _, mask_low_sat = cv2.threshold(s, 60, 255, cv2.THRESH_BINARY_INV)
        _, mask_high_val = cv2.threshold(v, 150, 255, cv2.THRESH_BINARY)
        white_mask = cv2.bitwise_and(mask_low_sat, mask_high_val)

        # Detecta AMARELO (numeros amarelos quando quantidade baixa)
        yellow_lower = np.array([20, 100, 150])
        yellow_upper = np.array([40, 255, 255])
        yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)

        # Combina branco + amarelo
        mask = cv2.bitwise_or(white_mask, yellow_mask)

        # Resize 5x para melhor leitura
        scale = 5
        h, w = mask.shape
        resized = cv2.resize(mask, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)

        # Morfologia - fecha buracos e remove ruido
        kernel = np.ones((2, 2), np.uint8)
        resized = cv2.morphologyEx(resized, cv2.MORPH_CLOSE, kernel, iterations=2)
        resized = cv2.morphologyEx(resized, cv2.MORPH_OPEN, kernel)

        # Inverte (texto preto em fundo branco)
        inverted = cv2.bitwise_not(resized)

        # Auto crop
        coords = cv2.findNonZero(cv2.bitwise_not(inverted))
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            margin = 8
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(inverted.shape[1] - x, w + 2*margin)
            h = min(inverted.shape[0] - y, h + 2*margin)
            cropped = inverted[y:y+h, x:x+w]
        else:
            cropped = inverted

        # Padding generoso
        padded = cv2.copyMakeBorder(cropped, 15, 15, 15, 15,
                                    cv2.BORDER_CONSTANT, value=255)

        if self.debug and name:
            cv2.imwrite(f"debug_{name}.png", padded)

        return padded

    def read_item_quantity(self, image: np.ndarray) -> int:
        """
        Le a quantidade de um item no slot

        Args:
            image: Imagem da regiao onde aparece a quantidade (canto inferior direito do slot)

        Returns:
            Quantidade do item (0 se nao conseguir ler ou slot vazio)
        """
        if image is None or image.size == 0:
            return 0

        # Verifica se a imagem e muito escura (slot vazio)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        if mean_brightness < 30:  # Muito escuro = sem item
            return 0

        # Preprocessa
        processed = self._preprocess_item_quantity(image, name="item_qty")

        # OCR apenas numeros
        config = "--psm 7 -c tessedit_char_whitelist=0123456789"

        try:
            text = pytesseract.image_to_string(processed, config=config).strip()

            if self.debug:
                print(f"[DEBUG] Item quantity OCR: '{text}'")

            # Tenta extrair numero
            numbers = re.findall(r'\d+', text)
            if numbers:
                qty = int(numbers[0])
                # Sanidade: quantidade maxima razoavel
                if 0 < qty <= 10000:
                    return qty

            # Tenta com PSM 8 (palavra unica)
            config_psm8 = "--psm 8 -c tessedit_char_whitelist=0123456789"
            text = pytesseract.image_to_string(processed, config=config_psm8).strip()

            numbers = re.findall(r'\d+', text)
            if numbers:
                qty = int(numbers[0])
                if 0 < qty <= 10000:
                    return qty

            # Tenta com PSM 10 (caractere unico - para 1 digito)
            config_psm10 = "--psm 10 -c tessedit_char_whitelist=0123456789"
            text = pytesseract.image_to_string(processed, config=config_psm10).strip()

            numbers = re.findall(r'\d+', text)
            if numbers:
                qty = int(numbers[0])
                if 0 < qty <= 10000:
                    return qty

        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Erro item quantity OCR: {e}")

        return 0

    def has_item_in_slot(self, image: np.ndarray) -> bool:
        """
        Verifica se ha um item no slot (baseado em conteudo visual)

        Args:
            image: Imagem do slot completo

        Returns:
            True se ha item visivel no slot
        """
        if image is None or image.size == 0:
            return False

        # Converte para grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Calcula variancia - slot vazio tem pouca variacao
        variance = np.var(gray)

        # Calcula brilho medio
        mean_brightness = np.mean(gray)

        # Slot com item: maior variancia (detalhes do sprite) e brilho moderado
        # Slot vazio: baixa variancia (uniforme) e escuro
        has_item = variance > 100 and mean_brightness > 20

        if self.debug:
            print(f"[DEBUG] Slot check: variance={variance:.1f}, brightness={mean_brightness:.1f}, has_item={has_item}")

        return has_item

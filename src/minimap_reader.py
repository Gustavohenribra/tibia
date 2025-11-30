"""
Sistema de Leitura de Minimapa
Detecta cores no minimapa para navegação inteligente (evita paredes, buracos)
"""

import cv2
import numpy as np
import time
from typing import List, Tuple, Optional
from utils.logger import get_logger


class MinimapReader:
    """Lê e analisa o minimapa do Tibia para navegação segura"""

    def __init__(self, screen_capture, settings: dict):
        """
        Inicializa leitor de minimapa

        Args:
            screen_capture: Instância do OBSScreenCapture
            settings: Configurações do minimapa do bot_settings.json
        """
        self.logger = get_logger()
        self.screen_capture = screen_capture
        self.settings = settings

        # Região do minimapa na tela
        self.minimap_x = settings["region"]["x"]
        self.minimap_y = settings["region"]["y"]
        self.minimap_width = settings["region"]["width"]
        self.minimap_height = settings["region"]["height"]

        # Centro do minimapa (posição do player)
        self.center_x = settings["player_center"]["x"]
        self.center_y = settings["player_center"]["y"]

        # Distância de verificação (em pixels)
        self.check_distance = settings.get("check_distance_pixels", 15)
        self.safety_margin = settings.get("safety_margin_pixels", 3)

        # Cores configuráveis (BGR exatas com tolerância)
        self.colors = settings.get("colors", {})
        self.color_tolerance = settings.get("color_tolerance", 3)  # ±3 por padrão

        # Cache
        self.last_minimap = None
        self.last_safe_directions = []

        # Debug
        self.debug = settings.get("debug", False)

        self.logger.info(f"🗺️  MinimapReader inicializado")
        self.logger.info(f"   Região: ({self.minimap_x}, {self.minimap_y}) {self.minimap_width}x{self.minimap_height}")
        self.logger.info(f"   Centro (player): ({self.center_x}, {self.center_y})")

    def capture_minimap(self) -> Optional[np.ndarray]:
        """
        Captura região do minimapa

        Returns:
            Imagem do minimapa em formato numpy array (BGR), ou None se falhar
        """
        try:
            minimap_img = self.screen_capture.capture_region(
                x=self.minimap_x,
                y=self.minimap_y,
                width=self.minimap_width,
                height=self.minimap_height
            )

            if minimap_img is None:
                self.logger.warning("Falha ao capturar minimapa")
                return None

            self.last_minimap = minimap_img
            return minimap_img

        except Exception as e:
            self.logger.error(f"Erro ao capturar minimapa: {e}")
            return None

    def create_color_mask(self, bgr_image: np.ndarray, color_name: str) -> Optional[np.ndarray]:
        """
        Cria máscara para uma cor específica usando cores BGR exatas

        Args:
            bgr_image: Imagem em formato BGR (direto da captura)
            color_name: Nome da cor ('walkable', 'hole', 'wall')

        Returns:
            Máscara binária (255 onde cor está presente, 0 caso contrário)
        """
        if color_name not in self.colors:
            return None

        color_config = self.colors[color_name]

        # Suporta novo formato (bgr_colors) e formato antigo (hsv_lower/hsv_upper) para compatibilidade
        if "bgr_colors" in color_config:
            # Novo formato: lista de cores BGR exatas
            mask = np.zeros(bgr_image.shape[:2], dtype=np.uint8)
            tolerance = self.color_tolerance

            for bgr in color_config["bgr_colors"]:
                lower = np.array([max(0, c - tolerance) for c in bgr], dtype=np.uint8)
                upper = np.array([min(255, c + tolerance) for c in bgr], dtype=np.uint8)
                color_mask = cv2.inRange(bgr_image, lower, upper)
                mask = cv2.bitwise_or(mask, color_mask)

            return mask
        else:
            # Formato antigo: HSV ranges (para compatibilidade)
            hsv_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
            lower = np.array(color_config["hsv_lower"])
            upper = np.array(color_config["hsv_upper"])
            return cv2.inRange(hsv_image, lower, upper)

    def is_direction_safe(self, minimap: np.ndarray, direction: str) -> bool:
        """
        Verifica se uma direção é segura para andar

        Args:
            minimap: Imagem do minimapa (BGR)
            direction: Direção a verificar ('UP', 'DOWN', 'LEFT', 'RIGHT')

        Returns:
            True se direção é segura, False caso contrário
        """
        try:
            # Cria máscaras para cada tipo de terreno (agora usa BGR direto)
            walkable_mask = self.create_color_mask(minimap, "walkable")
            hole_mask = self.create_color_mask(minimap, "hole")
            wall_mask = self.create_color_mask(minimap, "wall")

            # Define região a verificar baseado na direção
            check_dist = self.check_distance
            margin = self.safety_margin

            if direction == 'UP':
                # Verifica pixels acima do centro
                y_start = max(0, self.center_y - check_dist)
                y_end = self.center_y - margin
                x_start = self.center_x - 5
                x_end = self.center_x + 5
            elif direction == 'DOWN':
                # Verifica pixels abaixo do centro
                y_start = self.center_y + margin
                y_end = min(self.minimap_height, self.center_y + check_dist)
                x_start = self.center_x - 5
                x_end = self.center_x + 5
            elif direction == 'LEFT':
                # Verifica pixels à esquerda do centro
                y_start = self.center_y - 5
                y_end = self.center_y + 5
                x_start = max(0, self.center_x - check_dist)
                x_end = self.center_x - margin
            elif direction == 'RIGHT':
                # Verifica pixels à direita do centro
                y_start = self.center_y - 5
                y_end = self.center_y + 5
                x_start = self.center_x + margin
                x_end = min(self.minimap_width, self.center_x + check_dist)
            else:
                return False

            # Garante limites válidos
            y_start = max(0, min(y_start, self.minimap_height - 1))
            y_end = max(0, min(y_end, self.minimap_height))
            x_start = max(0, min(x_start, self.minimap_width - 1))
            x_end = max(0, min(x_end, self.minimap_width))

            # Extrai região de verificação
            if hole_mask is not None:
                region_hole = hole_mask[y_start:y_end, x_start:x_end]
                if np.any(region_hole > 0):
                    self.logger.debug(f"   {direction}: ❌ Buraco detectado (amarelo)")
                    return False

            if wall_mask is not None:
                region_wall = wall_mask[y_start:y_end, x_start:x_end]
                if np.any(region_wall > 0):
                    self.logger.debug(f"   {direction}: ❌ Parede detectada (preto/cinza)")
                    return False

            # Se não encontrou obstáculos E encontrou chão walkable, é seguro
            if walkable_mask is not None:
                region_walkable = walkable_mask[y_start:y_end, x_start:x_end]
                if np.any(region_walkable > 0):
                    self.logger.debug(f"   {direction}: ✅ Chão seguro (laranja)")
                    return True

            # Se não encontrou nada, assume como inseguro por precaução
            self.logger.debug(f"   {direction}: ⚠️ Cor não reconhecida (assume inseguro)")
            return False

        except Exception as e:
            self.logger.error(f"Erro ao verificar direção {direction}: {e}")
            return False

    def get_safe_directions(self) -> List[str]:
        """
        Analisa minimapa e retorna lista de direções seguras

        Returns:
            Lista de direções seguras (['UP', 'DOWN', 'LEFT', 'RIGHT'])
        """
        # Captura minimapa
        minimap = self.capture_minimap()
        if minimap is None:
            self.logger.warning("Não foi possível capturar minimapa, retornando todas as direções")
            return ['UP', 'DOWN', 'LEFT', 'RIGHT']

        self.logger.debug("🔍 Analisando direções no minimapa...")

        # Verifica cada direção
        safe_directions = []
        for direction in ['UP', 'DOWN', 'LEFT', 'RIGHT']:
            if self.is_direction_safe(minimap, direction):
                safe_directions.append(direction)

        if safe_directions:
            self.logger.info(f"📋 Direções seguras: {safe_directions}")
        else:
            self.logger.warning("⚠️ Nenhuma direção segura detectada! Usando fallback...")
            # Fallback: tenta direção oposta à última ou retorna todas
            safe_directions = ['UP', 'DOWN', 'LEFT', 'RIGHT']

        self.last_safe_directions = safe_directions
        return safe_directions

    def get_walkable_edges(self, min_distance_from_center: int = 30) -> List[Tuple[int, int]]:
        """
        Detecta extremidades das áreas caminháveis no CENTRO dos caminhos
        (longe das paredes para movimento natural)

        Args:
            min_distance_from_center: Distância mínima do centro do minimapa (pixels)

        Returns:
            Lista de tuplas (x, y) com coordenadas relativas ao minimapa
        """
        # Captura minimapa
        minimap = self.capture_minimap()
        if minimap is None:
            self.logger.warning("Não foi possível capturar minimapa para detectar extremidades")
            return []

        try:
            # Cria máscara do chão caminhável (agora usa BGR direto)
            walkable_mask = self.create_color_mask(minimap, "walkable")

            if walkable_mask is None:
                self.logger.warning("Máscara de chão caminhável não disponível")
                return []

            # NOVO: Erosão SIMPLIFICADA - Apenas remove ruído, sem destruir caminhos
            # Usa kernel 3x3 com 1 iteração (suave)
            kernel = np.ones((3, 3), np.uint8)
            eroded_mask = cv2.erode(walkable_mask, kernel, iterations=1)

            # Se a erosão removeu tudo (caminho muito fino), usa original
            if np.count_nonzero(eroded_mask) == 0:
                 self.logger.warning("⚠️  Erosão removeu todos os pixels, usando máscara original")
                 eroded_mask = walkable_mask
            else:
                 self.logger.debug("🎨 Erosão suave aplicada (3x3, iter=1) para remover ruído")

            # Se NENHUMA erosão funcionou, usa máscara original (mas ainda vai verificar paredes!)
            if eroded_mask is None:
                self.logger.warning(
                    "⚠️  Todas erosões removeram pixels demais, usando máscara original "
                    "(verificação de paredes AINDA ATIVA)"
                )
                eroded_mask = walkable_mask

            # Cria máscara de PAREDES para verificação (agora usa BGR direto)
            wall_mask = self.create_color_mask(minimap, "wall")
            if wall_mask is None:
                wall_mask = np.zeros_like(walkable_mask)  # Cria máscara vazia se não configurado

            hole_mask = self.create_color_mask(minimap, "hole")
            if hole_mask is None:
                hole_mask = np.zeros_like(walkable_mask)

            # Encontra todos os pixels caminháveis (após erosão = centro dos caminhos)
            walkable_points = np.argwhere(eroded_mask > 0)  # Retorna (y, x)

            if len(walkable_points) == 0:
                self.logger.warning("Nenhum pixel caminhável detectado após erosão")
                return []

            # Filtra pontos que estão longe do centro E não têm paredes/buracos por perto
            edges = []
            safety_radius = self.safety_margin  # Usa valor configurado (default 3)

            rejected_too_close = 0
            rejected_wall = 0
            rejected_hole = 0

            for point in walkable_points:
                y, x = point

                # Calcula distância euclidiana do centro
                distance = np.sqrt(
                    (x - self.center_x)**2 + (y - self.center_y)**2
                )

                # Deve estar longe do centro
                if distance < min_distance_from_center:
                    rejected_too_close += 1
                    continue

                # CRÍTICO: Verifica se há PAREDES ou BURACOS numa área ao redor
                y_min = max(0, y - safety_radius)
                y_max = min(wall_mask.shape[0], y + safety_radius + 1)
                x_min = max(0, x - safety_radius)
                x_max = min(wall_mask.shape[1], x + safety_radius + 1)

                # Extrai região ao redor do ponto
                region_wall = wall_mask[y_min:y_max, x_min:x_max]
                region_hole = hole_mask[y_min:y_max, x_min:x_max]

                # Se há QUALQUER pixel preto (parede) ou amarelo (buraco) por perto, REJEITA
                has_wall_nearby = np.any(region_wall > 0)
                has_hole_nearby = np.any(region_hole > 0)

                if has_wall_nearby:
                    rejected_wall += 1
                    continue  # REJEITA - parede detectada!

                if has_hole_nearby:
                    rejected_hole += 1
                    continue  # REJEITA - buraco detectado!

                # Ponto é SEGURO - adiciona à lista
                edges.append((int(x), int(y)))

            # Log de estatísticas de filtragem
            total_candidates = len(walkable_points)
            self.logger.info(
                f"🔍 Análise de {total_candidates} pontos candidatos: "
                f"✅ {len(edges)} aceitos | "
                f"❌ {rejected_too_close} muito perto | "
                f"🧱 {rejected_wall} com parede | "
                f"🕳️ {rejected_hole} com buraco"
            )

            # Limita número de pontos (performance, mas garante densidade suficiente para setores)
            if len(edges) > 200:
                # Seleciona 200 pontos aleatórios
                import random
                edges = random.sample(edges, 200)

            if len(edges) == 0:
                self.logger.error(
                    "❌ NENHUM ponto seguro encontrado! "
                    f"Todos os {total_candidates} candidatos foram rejeitados."
                )

            return edges

        except Exception as e:
            self.logger.error(f"Erro ao detectar extremidades: {e}")
            return []

    def is_player_moving(self, previous_minimap: Optional[np.ndarray] = None,
                        threshold: int = 30) -> bool:
        """
        Detecta se o player está se movendo comparando o MAPA ao redor da cruz
        A cruz fica fixa no centro, mas o mapa rola quando você anda

        Args:
            previous_minimap: Frame anterior do minimapa (se None, usa last_minimap)
            threshold: Número mínimo de pixels diferentes para considerar movimento (padrão: 30)

        Returns:
            True se player está se movendo (mapa rolando), False se parado
        """
        # Captura minimapa atual
        current_minimap = self.capture_minimap()
        if current_minimap is None:
            return False

        # Usa frame anterior fornecido ou o último armazenado
        if previous_minimap is None:
            previous_minimap = self.last_minimap

        if previous_minimap is None:
            self.logger.debug("Nenhum frame anterior disponível para comparação")
            return False

        try:
            # Cria máscara para analisar o MAPA ao redor da cruz (não a cruz em si)
            # Região anular: do raio interno (ignora cruz) até raio externo (analisa mapa)
            inner_radius = 5   # Ignora cruz (7x7 = raio ~3, usamos 5 para margem)
            outer_radius = 25  # Analisa até 25 pixels do centro (boa parte do mapa)

            # Cria máscara circular
            height, width = current_minimap.shape[:2]
            y, x = np.ogrid[:height, :width]

            # Distância de cada pixel ao centro
            dist_from_center = np.sqrt((x - self.center_x)**2 + (y - self.center_y)**2)

            # Máscara anular: pixels entre inner e outer radius
            mask = ((dist_from_center >= inner_radius) & (dist_from_center <= outer_radius)).astype(np.uint8)

            # Aplica máscara aos frames (só analisa o anel ao redor da cruz)
            prev_masked = cv2.bitwise_and(previous_minimap, previous_minimap, mask=mask)
            curr_masked = cv2.bitwise_and(current_minimap, current_minimap, mask=mask)

            # Calcula diferença absoluta NO MAPA (não na cruz)
            diff = cv2.absdiff(prev_masked, curr_masked)

            # Conta pixels que mudaram significativamente
            # Threshold: mudança > 25 na escala de cinza
            gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            changed_pixels = np.sum(gray_diff > 25)

            # Calcula percentual de mudança (relativo à área analisada)
            analyzed_pixels = np.sum(mask)
            change_percent = (changed_pixels / analyzed_pixels * 100) if analyzed_pixels > 0 else 0

            # Considera movendo se:
            # 1. Número absoluto de pixels mudados > threshold OU
            # 2. Percentual de mudança > 3%
            is_moving = changed_pixels >= threshold or change_percent > 3.0

            # Log detalhado
            if is_moving or self.debug:
                self.logger.debug(
                    f"🔍 Detecção do MAPA: {changed_pixels} pixels mudaram "
                    f"({change_percent:.1f}% da área analisada, threshold: {threshold}) "
                    f"→ {'🏃 MOVENDO' if is_moving else '⏸️ PARADO'}"
                )

            # Debug: salva imagens se debug ativo
            if self.debug and is_moving:
                cv2.imwrite("debug_minimap_prev_masked.png", prev_masked)
                cv2.imwrite("debug_minimap_curr_masked.png", curr_masked)
                cv2.imwrite("debug_minimap_diff.png", diff * 10)  # Amplifica para visualização

            return is_moving

        except Exception as e:
            self.logger.error(f"Erro ao detectar movimento: {e}")
            return False

    def wait_until_stopped(self, timeout_seconds: float = 30.0,
                           check_interval_ms: int = 250,
                           consecutive_checks: int = 3,
                           interrupt_callback=None) -> bool:
        """
        Aguarda até o player parar de se mover
        Requer múltiplas verificações consecutivas para confirmar que está parado

        Args:
            timeout_seconds: Timeout máximo em segundos (padrão: 30s)
            check_interval_ms: Intervalo entre verificações em ms (padrão: 300ms)
            consecutive_checks: Número de checks consecutivos necessários para confirmar parada (padrão: 8)
            interrupt_callback: Função opcional que retorna True para interromper a espera (ex: detectou criatura)

        Returns:
            True se parou, False se timeout ou interrompido
        """
        start_time = time.time()
        check_interval = check_interval_ms / 1000.0

        self.logger.info(
            f"⏳ Aguardando player parar "
            f"(timeout: {timeout_seconds}s, checks: {consecutive_checks}, intervalo: {check_interval_ms}ms)..."
        )

        # Captura frame inicial
        previous_frame = self.capture_minimap()

        # Contador de verificações consecutivas sem movimento
        stopped_count = 0

        while (time.time() - start_time) < timeout_seconds:
            time.sleep(check_interval)

            # NOVO: Verifica se deve interromper (ex: criatura detectada)
            if interrupt_callback is not None and interrupt_callback():
                self.logger.info("⚔️  Movimento interrompido (criatura detectada!)")
                return False

            # Verifica se ainda está se movendo
            is_moving = self.is_player_moving(previous_frame)
            elapsed = time.time() - start_time

            if not is_moving:
                stopped_count += 1
                self.logger.info(f"   ⏸️  Parado: {stopped_count}/{consecutive_checks} checks (t={elapsed:.2f}s)")

                # Só confirma parada após N verificações consecutivas
                if stopped_count >= consecutive_checks:
                    self.logger.info(f"✅ Player confirmado parado após {elapsed:.2f}s")
                    return True
            else:
                # Se moveu, reseta contador
                if stopped_count > 0:
                    self.logger.info(f"   🏃 Movimento detectado, resetando contador (estava em {stopped_count}/{consecutive_checks})")
                else:
                    self.logger.debug(f"   🏃 Ainda movendo... (t={elapsed:.2f}s)")
                stopped_count = 0

            # Atualiza frame anterior
            previous_frame = self.last_minimap

        self.logger.warning(f"⚠️  Timeout: player não parou após {timeout_seconds}s")
        return False

    def save_debug_image(self, filename: str = "debug_minimap.png"):
        """Salva última captura do minimapa para debug"""
        if self.last_minimap is not None:
            cv2.imwrite(filename, self.last_minimap)
            self.logger.info(f"💾 Minimapa salvo em {filename}")

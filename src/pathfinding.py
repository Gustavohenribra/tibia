"""
Sistema de Pathfinding para Navegação Inteligente
Seleciona pontos de destino nas extremidades do mapa de forma inteligente
"""

import time
import random
import math
from typing import List, Tuple, Optional, Dict
from collections import deque, defaultdict
from utils.logger import get_logger


class PathfindingSystem:
    """Gerencia seleção inteligente de pontos de destino no minimapa"""

    SECTOR_COUNT = 8  # Número de setores (N, NE, E, SE, S, SW, W, NW)

    def __init__(self, minimap_reader, settings: dict):
        """
        Inicializa sistema de pathfinding

        Args:
            minimap_reader: Instância do MinimapReader
            settings: Configurações de pathfinding do bot_settings.json
        """
        self.logger = get_logger()
        self.minimap_reader = minimap_reader
        self.settings = settings

        # Configurações
        self.edge_distance = settings.get("edge_check_distance", 30)
        self.stuck_threshold_seconds = settings.get("max_stuck_time_ms", 3000) / 1000.0

        # Estado de navegação por setores
        # Rastreia timestamp da última visita a cada setor para "Heatmap" temporal
        self.sector_timestamps = {i: 0.0 for i in range(self.SECTOR_COUNT)}
        self.last_sector = None
        self.last_edge = None

        # Estatísticas
        self.total_paths = 0
        self.stuck_count = 0

        self.logger.info(f"🧭 PathfindingSystem inicializado")
        self.logger.info(f"   Distância de extremidade: {self.edge_distance}px")
        self.logger.info(f"   Estratégia: Setores Ponderados ({self.SECTOR_COUNT} direções)")

    def _get_sector(self, x: int, y: int) -> int:
        """
        Calcula o setor (0-7) para uma coordenada (x, y)
        0=Leste, 1=Sudeste, 2=Sul, ..., sentido horário (ou similar, base trigonométrica)

        Args:
            x, y: Coordenadas do ponto no minimapa

        Returns:
            Índice do setor (0 a 7)
        """
        dx = x - self.minimap_reader.center_x
        dy = y - self.minimap_reader.center_y

        # Atan2 retorna radianos entre -pi e pi
        # 0 é direita (Leste), pi/2 é baixo (Sul) no sistema de imagem
        angle = math.atan2(dy, dx)

        # Converte para 0-8 setores
        # Normaliza para 0-2pi
        if angle < 0:
            angle += 2 * math.pi

        # Cada setor tem pi/4 radianos (45 graus)
        sector = int(angle / (2 * math.pi / self.SECTOR_COUNT))
        return sector % self.SECTOR_COUNT

    def get_next_edge(self) -> Optional[Tuple[int, int]]:
        """
        Seleciona próxima extremidade para visitar usando lógica ponderada por setores
        Prioriza setores menos visitados recentemente e evita backtracking imediato

        Returns:
            Tupla (x, y) com coordenadas relativas ao minimapa, ou None se não encontrou
        """
        # Obtém todas as extremidades disponíveis
        edges = self.minimap_reader.get_walkable_edges(
            min_distance_from_center=self.edge_distance
        )

        if not edges:
            self.logger.warning("⚠️  Nenhuma extremidade caminhável detectada")
            return None

        # Agrupa extremidades por setor
        edges_by_sector = defaultdict(list)
        for edge in edges:
            sector = self._get_sector(edge[0], edge[1])
            edges_by_sector[sector].append(edge)

        available_sectors = list(edges_by_sector.keys())
        if not available_sectors:
            return None

        # Calcula pesos para cada setor
        current_time = time.time()
        weights = []
        debug_scores = []

        for sector in available_sectors:
            # 1. Fator Recência: Quanto mais tempo sem visitar, maior o peso
            last_visit = self.sector_timestamps.get(sector, 0)
            time_delta = current_time - last_visit
            # Limita delta para evitar pesos infinitos ou zeros
            score = min(time_delta, 300.0) + 5.0 # Base score

            # 2. Fator Anti-Backtrack: Penaliza setor oposto ao anterior
            is_opposite = False
            if self.last_sector is not None:
                # Setor oposto (distância de 4 setores em 8)
                opposite_sector = (self.last_sector + 4) % self.SECTOR_COUNT
                if sector == opposite_sector:
                    score *= 0.1  # Penalidade forte (10% do score original)
                    is_opposite = True
                elif sector == (opposite_sector + 1) % self.SECTOR_COUNT or \
                     sector == (opposite_sector - 1) % self.SECTOR_COUNT:
                     score *= 0.3 # Penalidade média para vizinhos do oposto

            weights.append(score)
            debug_scores.append(f"S{sector}: {score:.1f}{'⛔' if is_opposite else ''}")

        # Seleciona setor com base nos pesos (Weighted Random)
        # Isso permite aleatoriedade mas favorece fortemente a exploração
        try:
            selected_sector = random.choices(available_sectors, weights=weights, k=1)[0]
        except (ValueError, IndexError):
            # Fallback seguro
            selected_sector = random.choice(available_sectors)

        # Escolhe uma extremidade aleatória dentro do setor selecionado
        selected_edge = random.choice(edges_by_sector[selected_sector])

        # Atualiza estado
        self.sector_timestamps[selected_sector] = current_time
        self.last_sector = selected_sector
        self.last_edge = selected_edge
        self.total_paths += 1

        self.logger.info(
            f"🎯 Setor {selected_sector} selecionado (Pesos: {', '.join(debug_scores)})"
        )

        return selected_edge

    def get_opposite_direction_edge(self) -> Optional[Tuple[int, int]]:
        """
        Obtém uma extremidade na direção oposta à última visitada
        Útil quando o bot fica preso

        Returns:
            Tupla (x, y) ou None
        """
        if self.last_edge is None:
            return self.get_next_edge()

        # Obtém todas as extremidades
        edges = self.minimap_reader.get_walkable_edges(
            min_distance_from_center=self.edge_distance
        )

        if not edges:
            return None

        # Calcula vetor da última extremidade em relação ao centro
        center_x = self.minimap_reader.center_x
        center_y = self.minimap_reader.center_y

        last_vector_x = self.last_edge[0] - center_x
        last_vector_y = self.last_edge[1] - center_y

        # Encontra extremidade com vetor mais oposto (produto escalar negativo)
        best_edge = None
        best_score = float('inf')

        for edge in edges:
            edge_vector_x = edge[0] - center_x
            edge_vector_y = edge[1] - center_y

            # Produto escalar (quanto mais negativo, mais oposto)
            dot_product = (edge_vector_x * last_vector_x +
                          edge_vector_y * last_vector_y)

            if dot_product < best_score:
                best_score = dot_product
                best_edge = edge

        if best_edge:
            self.logger.info(f"🔄 Direção oposta selecionada: {best_edge}")
            
            # Atualiza setor da nova direção
            current_time = time.time()
            sector = self._get_sector(best_edge[0], best_edge[1])
            
            self.sector_timestamps[sector] = current_time
            self.last_sector = sector
            self.last_edge = best_edge

        return best_edge

    def is_stuck(self, start_time: float) -> bool:
        """
        Verifica se o bot está preso (não chegou ao destino no tempo esperado)

        Args:
            start_time: Timestamp do início do movimento

        Returns:
            True se preso
        """
        elapsed = time.time() - start_time
        is_stuck = elapsed >= self.stuck_threshold_seconds

        if is_stuck:
            self.stuck_count += 1
            self.logger.warning(
                f"⚠️  Bot parece estar preso! "
                f"({elapsed:.1f}s >= {self.stuck_threshold_seconds:.1f}s)"
            )

        return is_stuck

    def reset_history(self):
        """Limpa histórico de visitas"""
        # Reseta todos os timestamps para 0
        for s in self.sector_timestamps:
            self.sector_timestamps[s] = 0.0
        self.last_sector = None
        self.last_edge = None
        self.logger.debug("🔄 Histórico de setores resetado")

    def get_stats(self) -> dict:
        """Retorna estatísticas de pathfinding"""
        # Conta quantos setores foram visitados recentemente (> 0)
        visited_sectors = sum(1 for t in self.sector_timestamps.values() if t > 0)
        
        return {
            "total_paths": self.total_paths,
            "stuck_count": self.stuck_count,
            "visited_sectors": visited_sectors,
            "last_edge": self.last_edge,
            "last_sector": self.last_sector
        }


class EdgeSelector:
    """Seletor de extremidades com estratégias diferentes"""

    @staticmethod
    def select_random(edges: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        """Seleciona aleatoriamente"""
        if not edges:
            return None
        return random.choice(edges)

    @staticmethod
    def select_farthest(edges: List[Tuple[int, int]],
                       center_x: int,
                       center_y: int) -> Optional[Tuple[int, int]]:
        """Seleciona a extremidade mais distante do centro"""
        if not edges:
            return None

        farthest = max(
            edges,
            key=lambda e: (e[0] - center_x)**2 + (e[1] - center_y)**2
        )

        return farthest

    @staticmethod
    def select_by_quadrant(edges: List[Tuple[int, int]],
                          center_x: int,
                          center_y: int,
                          preferred_quadrant: Optional[str] = None) -> Optional[Tuple[int, int]]:
        """
        Seleciona extremidade em um quadrante específico

        Args:
            edges: Lista de extremidades
            center_x: Centro X do minimapa
            center_y: Centro Y do minimapa
            preferred_quadrant: 'NE', 'NW', 'SE', 'SW' ou None (aleatório)

        Returns:
            Extremidade selecionada ou None
        """
        if not edges:
            return None

        # Divide em quadrantes
        quadrants = {
            'NE': [],  # Nordeste (x > center, y < center)
            'NW': [],  # Noroeste (x < center, y < center)
            'SE': [],  # Sudeste (x > center, y > center)
            'SW': []   # Sudoeste (x < center, y > center)
        }

        for edge in edges:
            x, y = edge

            if x >= center_x and y < center_y:
                quadrants['NE'].append(edge)
            elif x < center_x and y < center_y:
                quadrants['NW'].append(edge)
            elif x >= center_x and y >= center_y:
                quadrants['SE'].append(edge)
            else:
                quadrants['SW'].append(edge)

        # Seleciona quadrante
        if preferred_quadrant and quadrants[preferred_quadrant]:
            return random.choice(quadrants[preferred_quadrant])

        # Seleciona aleatoriamente de um quadrante não vazio
        non_empty = [q for q in quadrants.values() if q]
        if non_empty:
            return random.choice(random.choice(non_empty))

        return None

"""
Sistema de Movimentação Automática
Navega clicando nas extremidades do minimapa de forma inteligente
"""

import time
import random
from typing import Optional
from utils.logger import get_logger
from utils.mouse_sender import get_mouse_sender
from pathfinding import PathfindingSystem


class Movement:
    """Controla movimento inteligente do personagem via clicks no minimapa"""

    def __init__(self, key_sender, settings: dict, minimap_reader=None, interrupt_callback=None, screen_capture=None, mouse_sender_method: str = None):
        """
        Inicializa sistema de movimento

        Args:
            key_sender: Instância do key sender (mantido para compatibilidade)
            settings: Configurações de movimento do bot_settings.json
            minimap_reader: Instância do MinimapReader (necessário)
            interrupt_callback: Função opcional para interromper movimento (ex: detectou criatura)
            screen_capture: Instância do OBSScreenCapture (para detecção de resolução)
            mouse_sender_method: Método do mouse sender ("SendInput" ou "PostMessage"). Se None, usa "SendInput"
        """
        self.logger = get_logger()
        self.key_sender = key_sender  # Mantido para compatibilidade
        self.settings = settings
        self.minimap_reader = minimap_reader
        self.interrupt_callback = interrupt_callback

        # Configurações
        self.enabled = settings.get("enable", True)
        self.pause_after_arrival_min_ms = settings.get("pause_after_arrival_min_ms", 1000)
        self.pause_after_arrival_max_ms = settings.get("pause_after_arrival_max_ms", 3000)

        # Obtém resolução OBS para conversão de coordenadas
        obs_resolution = None
        if screen_capture is not None:
            obs_res = screen_capture.get_resolution()
            if obs_res:
                obs_resolution = obs_res
                self.logger.info(f"🎥 Resolução OBS detectada: {obs_res[0]}x{obs_res[1]}")

        # Define método do mouse (usa parâmetro ou padrão SendInput)
        mouse_method = mouse_sender_method if mouse_sender_method else "SendInput"

        # Mouse sender para clicks (com conversão OBS → Tela Real)
        self.mouse_sender = get_mouse_sender(
            method=mouse_method,
            click_duration_min_ms=50,
            click_duration_max_ms=100,
            position_variance_px=1,
            delay_between_clicks_ms=100,
            obs_resolution=obs_resolution,
            debug=False
        )

        # Pathfinding system
        pathfinding_settings = settings.get("pathfinding", {})
        if not pathfinding_settings:
            # Valores padrão
            pathfinding_settings = {
                "edge_check_distance": 30,
                "history_size": 5,
                "max_stuck_time_ms": 3000
            }

        if minimap_reader:
            self.pathfinding = PathfindingSystem(minimap_reader, pathfinding_settings)
        else:
            self.pathfinding = None
            self.logger.warning("⚠️  MinimapReader não fornecido - pathfinding desabilitado")

        # Coordenadas da região do minimapa (para cálculo absoluto)
        if minimap_reader:
            self.minimap_region_x = minimap_reader.minimap_x
            self.minimap_region_y = minimap_reader.minimap_y
        else:
            self.minimap_region_x = 0
            self.minimap_region_y = 0

        # Estado
        self.is_moving = False
        self.last_movement_time = 0
        self.consecutive_movements = 0

        if self.enabled:
            self.logger.info(f"🚶 Movimento automático: ATIVADO (modo: PATHFINDING)")
            if self.minimap_reader:
                self.logger.info(f"   Sistema de clicks no minimapa configurado")
        else:
            self.logger.info(f"🚶 Movimento automático: DESATIVADO")

    def should_move(self, time_since_last_combat: float) -> bool:
        """
        Verifica se deve iniciar movimento

        Args:
            time_since_last_combat: Tempo em segundos desde último combate

        Returns:
            True se deve se mover
        """
        if not self.enabled:
            return False

        if not self.minimap_reader or not self.pathfinding:
            return False

        # Cooldown mínimo entre movimentos
        time_since_last_move = time.time() - self.last_movement_time
        if time_since_last_move < 0.3:  # Mínimo 0.3 segundos entre ciclos
            return False

        # Move se passou tempo configurado sem combate
        min_time_without_combat = 0.8  # Tempo mínimo sem combate antes de mover
        return time_since_last_combat >= min_time_without_combat

    def walk_to_edge(self, max_stuck_retries: int = 2) -> bool:
        """
        Clica em uma extremidade do mapa e aguarda chegada

        Args:
            max_stuck_retries: Número máximo de tentativas se ficar preso

        Returns:
            True se executou movimento com sucesso
        """
        if not self.enabled or not self.pathfinding:
            return False

        try:
            retry_count = 0

            while retry_count <= max_stuck_retries:
                # Seleciona próxima extremidade
                if retry_count == 0:
                    edge = self.pathfinding.get_next_edge()
                else:
                    # Se ficou preso, tenta direção oposta
                    self.logger.info("🔄 Tentando direção oposta...")
                    edge = self.pathfinding.get_opposite_direction_edge()

                if edge is None:
                    self.logger.warning("⚠️  Nenhuma extremidade disponível")
                    return False

                edge_x, edge_y = edge

                self.logger.info(
                    f"🎯 Clicando em extremidade: ({edge_x}, {edge_y}) no minimapa"
                )

                # Clica no minimapa
                click_success = self.mouse_sender.click_minimap(
                    minimap_x=edge_x,
                    minimap_y=edge_y,
                    minimap_region_x=self.minimap_region_x,
                    minimap_region_y=self.minimap_region_y,
                    button='left'
                )

                if not click_success:
                    self.logger.error("❌ Falha ao clicar no minimapa")
                    return False

                # Aguarda um pouco para o cliente Tibia processar o click
                time.sleep(0.4)

                self.is_moving = True

                # Aguarda player chegar (com timeout)
                # Passa callback para interromper se detectar criatura
                start_time = time.time()
                arrived = self.minimap_reader.wait_until_stopped(
                    timeout_seconds=self.pathfinding.stuck_threshold_seconds,
                    interrupt_callback=self.interrupt_callback
                )

                self.is_moving = False

                # Verifica se ficou preso
                if not arrived:
                    if self.pathfinding.is_stuck(start_time):
                        retry_count += 1
                        if retry_count <= max_stuck_retries:
                            self.logger.warning(
                                f"⚠️  Tentativa {retry_count}/{max_stuck_retries} após travamento"
                            )
                            continue
                        else:
                            self.logger.error("❌ Falha após múltiplas tentativas")
                            return False
                    else:
                        # Timeout normal, mas não preso
                        self.logger.warning("⚠️  Timeout ao aguardar chegada")
                        break

                # Chegou com sucesso!
                self.logger.info("✅ Chegou à extremidade")

                # Pausa humanizada após chegar (simula pensamento)
                pause_duration = random.gauss(
                    (self.pause_after_arrival_min_ms + self.pause_after_arrival_max_ms) / 2,
                    (self.pause_after_arrival_max_ms - self.pause_after_arrival_min_ms) / 4
                )
                pause_duration = max(
                    self.pause_after_arrival_min_ms / 1000.0,
                    min(self.pause_after_arrival_max_ms / 1000.0, pause_duration / 1000.0)
                )

                time.sleep(pause_duration)

                self.last_movement_time = time.time()
                self.consecutive_movements += 1

                return True

            # Se chegou aqui, todas as tentativas falharam
            return False

        except Exception as e:
            self.logger.error(f"Erro ao mover para extremidade: {e}")
            self.is_moving = False
            return False

    def explore_area(self, max_movements: int = 3) -> int:
        """
        Explora a área visitando múltiplas extremidades

        Args:
            max_movements: Número máximo de movimentos a fazer

        Returns:
            Número de movimentos executados
        """
        if not self.enabled:
            return 0

        self.logger.info(f"🔍 Explorando área")

        movements_done = 0
        for i in range(max_movements):
            if self.walk_to_edge():
                movements_done += 1
            else:
                break

        if movements_done > 0:
            self.logger.info(f"✅ Exploração completa")
        self.consecutive_movements = 0  # Reset contador

        return movements_done

    def stop(self):
        """Para qualquer movimento em andamento"""
        self.is_moving = False

    def get_stats(self) -> dict:
        """Retorna estatísticas de movimento"""
        base_stats = {
            "enabled": self.enabled,
            "is_moving": self.is_moving,
            "total_movements": self.consecutive_movements,
            "last_movement_time": self.last_movement_time
        }

        # Adiciona estatísticas de pathfinding se disponível
        if self.pathfinding:
            base_stats.update({
                "pathfinding": self.pathfinding.get_stats()
            })

        # Adiciona estatísticas de mouse se disponível
        if self.mouse_sender:
            base_stats.update({
                "mouse": self.mouse_sender.get_stats()
            })

        return base_stats

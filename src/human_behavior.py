"""
Sistema de Comportamento Humanizado
Delays variáveis, distribuição gaussiana, micro-pauses
"""

import time
import random
import numpy as np


class HumanBehavior:
    """Simula comportamento humano com delays e randomização"""

    def __init__(self,
                 base_delay_ms: int = 150,
                 variance_ms: int = 50,
                 reaction_min_ms: int = 0,
                 reaction_max_ms: int = 300,
                 micro_pause_chance: float = 0.02):
        """
        Inicializa comportamento humanizado

        Args:
            base_delay_ms: Delay base entre ações
            variance_ms: Variação do delay (±)
            reaction_min_ms: Tempo de reação mínimo
            reaction_max_ms: Tempo de reação máximo
            micro_pause_chance: Chance de micro-pause (0-1)
        """
        self.base_delay = base_delay_ms / 1000.0
        self.variance = variance_ms / 1000.0
        self.reaction_min = reaction_min_ms / 1000.0
        self.reaction_max = reaction_max_ms / 1000.0
        self.micro_pause_chance = micro_pause_chance

    def get_delay(self) -> float:
        """
        Retorna delay humanizado (distribuição gaussiana)

        Returns:
            Delay em segundos
        """
        # Distribuição gaussiana (mais natural que uniforme)
        delay = np.random.normal(self.base_delay, self.variance / 3)

        # Clamp para valores positivos
        delay = max(0.01, delay)

        return delay

    def get_reaction_time(self) -> float:
        """
        Retorna tempo de reação humanizado

        Returns:
            Tempo de reação em segundos
        """
        return random.uniform(self.reaction_min, self.reaction_max)

    def should_micro_pause(self) -> bool:
        """
        Decide se deve fazer um micro-pause

        Returns:
            True se deve pausar
        """
        return random.random() < self.micro_pause_chance

    def micro_pause(self):
        """Executa um micro-pause (200-500ms)"""
        pause_time = random.uniform(0.2, 0.5)
        time.sleep(pause_time)

    def wait_before_action(self):
        """Espera antes de executar ação (delay + possível micro-pause)"""
        # Delay normal
        time.sleep(self.get_delay())

        # Micro-pause ocasional
        if self.should_micro_pause():
            self.micro_pause()

    def wait_after_action(self):
        """Espera após executar ação (reaction time)"""
        time.sleep(self.get_reaction_time())

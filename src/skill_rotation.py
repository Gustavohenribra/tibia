"""
Sistema de Rotação de Skills
Gerencia prioridades, cooldowns e condições
"""

import time
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from ocr_reader import Stats


@dataclass
class Skill:
    """Representa uma skill"""
    name: str
    hotkey: str
    priority: int
    cooldown: float
    mana_cost: int = 0
    skill_type: str = "damage"
    conditions: Dict = None
    last_used: float = 0.0

    def is_ready(self) -> bool:
        """Verifica se skill está fora de cooldown"""
        return (time.time() - self.last_used) >= self.cooldown

    def can_use(self, stats: Stats) -> bool:
        """
        Verifica se pode usar a skill baseado nas condições

        Args:
            stats: Estatísticas do personagem

        Returns:
            True se pode usar
        """
        if not self.is_ready():
            return False

        if self.conditions is None:
            return True

        # Check HP conditions
        if "max_hp_percent" in self.conditions:
            if stats.hp_percent > self.conditions["max_hp_percent"]:
                return False

        if "min_hp_percent" in self.conditions:
            if stats.hp_percent < self.conditions["min_hp_percent"]:
                return False

        # Check Mana conditions
        if "max_mana_percent" in self.conditions:
            if stats.mana_percent > self.conditions["max_mana_percent"]:
                return False

        if "min_mana_percent" in self.conditions:
            if stats.mana_percent < self.conditions["min_mana_percent"]:
                return False

        if "min_mana" in self.conditions:
            if stats.mana_current < self.conditions["min_mana"]:
                return False

        # Check mana cost
        if self.mana_cost > 0:
            if stats.mana_current < self.mana_cost:
                return False

        # Check combat (apenas para skills de damage)
        if self.conditions.get("has_target", False):
            if not stats.in_active_combat:
                return False

        return True

    def use(self):
        """Marca skill como usada"""
        self.last_used = time.time()


class SkillRotation:
    """Gerencia rotação de skills"""

    def __init__(self, config_path: str = "config/skills.json"):
        """
        Inicializa rotação

        Args:
            config_path: Caminho para config JSON
        """
        self.skills: List[Skill] = []
        self.global_settings: Dict = {}
        self.load_config(config_path)

    def load_config(self, config_path: str):
        """Carrega configuração JSON"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Carrega global settings
            self.global_settings = data.get("global_settings", {})

            # Carrega skills
            skills_data = data.get("skills", [])
            self.skills = []

            for skill_data in skills_data:
                skill = Skill(
                    name=skill_data["name"],
                    hotkey=skill_data["hotkey"],
                    priority=skill_data["priority"],
                    cooldown=skill_data["cooldown"],
                    mana_cost=skill_data.get("mana_cost", 0),
                    skill_type=skill_data.get("type", "damage"),
                    conditions=skill_data.get("conditions", {})
                )
                self.skills.append(skill)

            # Ordena por prioridade (maior = mais importante)
            self.skills.sort(key=lambda s: s.priority, reverse=True)

            print(f"✅ Rotação carregada: {len(self.skills)} skills")

        except Exception as e:
            print(f"❌ Erro ao carregar config: {e}")
            raise

    def get_next_skill(self, stats: Stats) -> Optional[Skill]:
        """
        Retorna próxima skill a ser usada baseado em prioridade e condições

        Args:
            stats: Estatísticas do personagem

        Returns:
            Skill ou None
        """
        # Check emergency mode
        emergency_hp = self.global_settings.get("emergency_hp_percent", 20)
        if stats.hp_percent < emergency_hp:
            # Prioriza healing
            for skill in self.skills:
                if skill.skill_type == "healing" and skill.can_use(stats):
                    return skill
            return None

        # Check pause rotation
        pause_hp = self.global_settings.get("pause_rotation_when_hp_below", 30)
        if stats.hp_percent < pause_hp:
            # Só usa healing/mana
            for skill in self.skills:
                if skill.skill_type in ["healing", "mana"] and skill.can_use(stats):
                    return skill
            return None

        # Rotação normal (por prioridade)
        for skill in self.skills:
            if skill.can_use(stats):
                return skill

        return None

    def use_skill(self, skill: Skill):
        """Marca skill como usada"""
        skill.use()

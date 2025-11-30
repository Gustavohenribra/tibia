"""
Sistema de Rotação de Skills
Gerencia prioridades, cooldowns e condições
"""

import time
import json
from typing import List, Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass
from ocr_reader import Stats

if TYPE_CHECKING:
    from potion_monitor import PotionMonitor


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

    # Anti-spam: rastreia tentativas sem efeito
    failed_attempts: int = 0  # Tentativas consecutivas sem efeito
    max_failed_attempts: int = 3  # Máximo de tentativas antes de bloquear
    blocked_until: float = 0.0  # Timestamp até quando está bloqueada
    block_duration: float = 30.0  # Duração do bloqueio em segundos (30s padrão)

    # Para verificação de efeito
    hp_before_use: int = 0
    mana_before_use: int = 0

    def is_ready(self) -> bool:
        """Verifica se skill está fora de cooldown"""
        return (time.time() - self.last_used) >= self.cooldown

    def is_blocked(self) -> bool:
        """Verifica se skill está bloqueada por falhas consecutivas"""
        if self.blocked_until > 0 and time.time() < self.blocked_until:
            return True
        # Se passou o tempo de bloqueio, reseta
        if self.blocked_until > 0 and time.time() >= self.blocked_until:
            self.blocked_until = 0.0
            self.failed_attempts = 0
        return False

    def mark_no_effect(self):
        """Marca que a skill não teve efeito (sem poção/sem mana real)"""
        self.failed_attempts += 1
        if self.failed_attempts >= self.max_failed_attempts:
            self.blocked_until = time.time() + self.block_duration
            print(f"⚠️  {self.name}: Bloqueada por {self.block_duration}s (sem efeito {self.failed_attempts}x)")

    def mark_success(self):
        """Marca que a skill teve efeito - reseta contador de falhas"""
        self.failed_attempts = 0
        self.blocked_until = 0.0

    def save_stats_before(self, hp: int, mana: int):
        """Salva HP/Mana antes de usar para verificar efeito depois"""
        self.hp_before_use = hp
        self.mana_before_use = mana

    def get_remaining_block_time(self) -> float:
        """Retorna tempo restante de bloqueio em segundos"""
        if self.blocked_until > 0:
            remaining = self.blocked_until - time.time()
            return max(0, remaining)
        return 0

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

        # Anti-spam: verifica se está bloqueada por falhas consecutivas
        if self.is_blocked():
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

    def __init__(self, config_path: str = "config/skills.json",
                 potion_monitor: Optional["PotionMonitor"] = None):
        """
        Inicializa rotação

        Args:
            config_path: Caminho para config JSON
            potion_monitor: Monitor de poções (opcional, para verificar quantidade antes de usar)
        """
        self.skills: List[Skill] = []
        self.global_settings: Dict = {}
        self.potion_monitor = potion_monitor
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
                # Configurações anti-spam opcionais
                if "max_failed_attempts" in skill_data:
                    skill.max_failed_attempts = skill_data["max_failed_attempts"]
                if "block_duration" in skill_data:
                    skill.block_duration = skill_data["block_duration"]
                self.skills.append(skill)

            # Ordena por prioridade (maior = mais importante)
            self.skills.sort(key=lambda s: s.priority, reverse=True)

            print(f"✅ Rotação carregada: {len(self.skills)} skills")

        except Exception as e:
            print(f"❌ Erro ao carregar config: {e}")
            raise

    def _can_use_with_potion_check(self, skill: Skill, stats: Stats) -> bool:
        """
        Verifica se pode usar skill, incluindo verificação de poção disponível

        Args:
            skill: Skill a verificar
            stats: Stats do personagem

        Returns:
            True se pode usar (condições OK e poção disponível se aplicável)
        """
        # Primeiro verifica condições normais
        if not skill.can_use(stats):
            return False

        # Se for poção (healing sem mana_cost ou tipo mana), verifica quantidade
        is_potion = (
            (skill.skill_type == "healing" and skill.mana_cost == 0) or
            skill.skill_type == "mana"
        )

        if is_potion and self.potion_monitor:
            # Verifica se tem poção no slot
            can_use = self.potion_monitor.can_use_potion(skill.hotkey)
            if not can_use:
                # Marca skill como bloqueada se não tem poção
                if not skill.is_blocked():
                    skill.blocked_until = time.time() + skill.block_duration
                    print(f"🚫 {skill.name}: SEM POÇÃO! Bloqueada por {skill.block_duration}s")
                return False

        return True

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
                if skill.skill_type == "healing" and self._can_use_with_potion_check(skill, stats):
                    return skill
            return None

        # Check pause rotation
        pause_hp = self.global_settings.get("pause_rotation_when_hp_below", 30)
        if stats.hp_percent < pause_hp:
            # Só usa healing/mana
            for skill in self.skills:
                if skill.skill_type in ["healing", "mana"] and self._can_use_with_potion_check(skill, stats):
                    return skill
            return None

        # Rotação normal (por prioridade)
        for skill in self.skills:
            if self._can_use_with_potion_check(skill, stats):
                return skill

        return None

    def use_skill(self, skill: Skill):
        """Marca skill como usada"""
        skill.use()

    def prepare_skill_use(self, skill: Skill, stats: Stats):
        """
        Prepara uso de skill salvando HP/Mana atual para verificar efeito depois
        Chamar ANTES de executar a skill
        """
        skill.save_stats_before(stats.hp_current, stats.mana_current)

    def verify_skill_effect(self, skill: Skill, stats: Stats, effect_threshold: int = 5) -> bool:
        """
        Verifica se a skill teve efeito comparando HP/Mana antes e depois
        Chamar ~1 segundo DEPOIS de executar a skill

        Args:
            skill: Skill que foi usada
            stats: Stats atuais (após uso)
            effect_threshold: Diferença mínima para considerar efeito

        Returns:
            True se teve efeito, False se não teve
        """
        had_effect = False

        if skill.skill_type == "healing":
            # Healing: HP deve ter aumentado
            hp_diff = stats.hp_current - skill.hp_before_use
            if hp_diff > effect_threshold:
                had_effect = True
            # Se HP já está no máximo, considera sucesso (não tinha o que curar)
            elif stats.hp_percent >= 95:
                had_effect = True

        elif skill.skill_type == "mana":
            # Mana pot: Mana deve ter aumentado
            mana_diff = stats.mana_current - skill.mana_before_use
            if mana_diff > effect_threshold:
                had_effect = True
            # Se Mana já está no máximo, considera sucesso
            elif stats.mana_percent >= 95:
                had_effect = True

        elif skill.skill_type == "damage":
            # Para damage, não verificamos efeito (sempre considera sucesso)
            had_effect = True

        # Atualiza estado da skill
        if had_effect:
            skill.mark_success()
        else:
            skill.mark_no_effect()

        return had_effect

    def get_blocked_skills_info(self) -> List[str]:
        """Retorna lista de skills bloqueadas e tempo restante"""
        blocked = []
        for skill in self.skills:
            if skill.is_blocked():
                remaining = skill.get_remaining_block_time()
                blocked.append(f"{skill.name}: {remaining:.0f}s restantes")
        return blocked

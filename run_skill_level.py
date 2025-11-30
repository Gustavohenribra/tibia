"""
Tibia Skill Level Bot
Bot para treinar magic level castando healing e consumindo mana/food automaticamente
"""

import sys
import os
import time
import random
import json
import keyboard
from datetime import datetime

# Adiciona src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from screen_capture_obs import OBSScreenCapture
from ocr_reader import OCRReader
from potion_monitor import PotionMonitor
from utils.key_sender import get_key_sender
from utils.logger import get_logger


class SkillLevelBot:
    """Bot de treino de magic level"""

    def __init__(self,
                 settings_path: str = "config/bot_settings.json",
                 skills_path: str = "config/skills.json"):
        """
        Inicializa o bot

        Args:
            settings_path: Caminho para configuracoes gerais
            skills_path: Caminho para configuracoes de skills
        """
        self.logger = get_logger(level="INFO")
        self.running = False
        self.paused = False

        # Carrega configuracoes
        self.logger.info("Carregando configuracoes...")
        with open(settings_path, 'r') as f:
            self.settings = json.load(f)

        # Configuracoes de skill level
        self.skill_config = self.settings.get("skill_level", {})
        self.healing_key = self.skill_config.get("healing_key", "3")
        self.healing_min = self.skill_config.get("healing_interval_min_sec", 2)
        self.healing_max = self.skill_config.get("healing_interval_max_sec", 4)
        self.healing_mana_cost = self.skill_config.get("healing_mana_cost", 10)  # Custo de mana do healing
        self.food_key = self.skill_config.get("food_key", "9")
        self.mana_key = self.skill_config.get("mana_key", "2")
        self.mana_threshold = self.skill_config.get("mana_threshold_percent", 40)

        # Regioes da tela
        self.mana_region = self.settings["screen_regions"]["mana_bar"]
        self.food_timer_region = self.settings["screen_regions"].get("food_timer")

        if self.food_timer_region is None:
            self.logger.warning("[AVISO] Regiao do food_timer nao configurada!")
            self.logger.warning("Execute: py tools/calibrate_food_timer.py")

        # Inicializa componentes
        self.logger.info("Inicializando componentes...")

        # Screen capture
        cam_index = self.settings["obs_camera"]["device_index"]
        self.screen_capture = OBSScreenCapture(camera_index=cam_index)

        # OCR
        self.ocr_reader = OCRReader(debug=False)

        # Key sender
        key_method = self.settings["key_sender"]["method"]
        self.key_sender = get_key_sender(method=key_method)

        # Monitor de poções (verifica quantidade antes de usar)
        self.potion_monitor = None
        if "potion_slots" in self.settings and self.settings["potion_slots"]:
            self.potion_monitor = PotionMonitor(
                self.screen_capture,
                self.ocr_reader,
                settings_path
            )
            self.logger.info(f"🧪 Monitor de poções: ATIVADO ({len(self.settings['potion_slots'])} slots)")
        else:
            self.logger.info("🧪 Monitor de poções: DESATIVADO (configure com tools/calibrate_potion_slots.py)")

        # Estatisticas
        self.stats = {
            "healing_casts": 0,
            "mana_potions": 0,
            "food_eaten": 0,
            "start_time": None
        }

        # Estado
        self.last_food_timer = None
        self.last_mana_percent = None

        self.logger.info("Bot inicializado!")
        self._print_config()

    def _print_config(self):
        """Imprime configuracao atual"""
        self.logger.info("")
        self.logger.info("=" * 50)
        self.logger.info("CONFIGURACAO:")
        self.logger.info(f"  Healing: tecla '{self.healing_key}' a cada {self.healing_min}-{self.healing_max}s (custo: {self.healing_mana_cost} mana)")
        self.logger.info(f"  Mana Potion: tecla '{self.mana_key}' quando mana < {self.mana_threshold}%")
        self.logger.info(f"  Food: tecla '{self.food_key}' quando timer = 00:00")
        self.logger.info("=" * 50)
        self.logger.info("")

    def _log(self, category: str, message: str):
        """Log formatado com timestamp e categoria"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{category}] {message}")

    def _capture_mana(self):
        """Captura regiao da mana"""
        return self.screen_capture.capture_region(
            x=self.mana_region["x"],
            y=self.mana_region["y"],
            width=self.mana_region["width"],
            height=self.mana_region["height"]
        )

    def _capture_food_timer(self):
        """Captura regiao do food timer"""
        if self.food_timer_region is None:
            return None
        return self.screen_capture.capture_region(
            x=self.food_timer_region["x"],
            y=self.food_timer_region["y"],
            width=self.food_timer_region["width"],
            height=self.food_timer_region["height"]
        )

    def _read_mana(self):
        """Le mana atual"""
        mana_img = self._capture_mana()
        if mana_img is None:
            return None, None, None

        result = self.ocr_reader.read_mana(mana_img)
        if result is None:
            return None, None, None

        current, maximum = result
        percent = (current / maximum * 100) if maximum > 0 else 0
        return current, maximum, percent

    def _read_food_timer(self):
        """Le food timer"""
        food_img = self._capture_food_timer()
        if food_img is None:
            return None

        return self.ocr_reader.read_food_timer(food_img)

    def _press_key(self, key: str):
        """Pressiona tecla com delay humanizado"""
        # Delay pre-acao
        time.sleep(random.uniform(0.02, 0.05))
        self.key_sender.press_key(key)
        # Delay pos-acao
        time.sleep(random.uniform(0.05, 0.1))

    def _check_food(self):
        """Verifica e consome food se necessario"""
        timer = self._read_food_timer()

        if timer != self.last_food_timer:
            self._log("FOOD", f"Timer: {timer if timer else 'N/A'}")
            self.last_food_timer = timer

        if self.ocr_reader.is_food_timer_empty(timer):
            # Verifica se tem food antes de usar
            if self.potion_monitor:
                can_use = self.potion_monitor.can_use_potion(self.food_key)
                if not can_use:
                    self._log("FOOD", f"🚫 SEM COMIDA no slot [{self.food_key}]! Pulando...")
                    return False

            self._log("FOOD", f"Timer zerado! Consumindo comida (tecla {self.food_key})")
            self._press_key(self.food_key)
            self.stats["food_eaten"] += 1
            time.sleep(0.5)  # Cooldown apos comer
            return True

        return False

    def _check_mana(self):
        """Verifica e consome mana potion se necessario"""
        current, maximum, percent = self._read_mana()

        if percent is None:
            self._log("MANA", "Falha ao ler mana")
            return False

        # Log periodico de mana (a cada mudanca significativa)
        if self.last_mana_percent is None or abs(percent - self.last_mana_percent) >= 5:
            status = "OK" if percent >= self.mana_threshold else "BAIXA"
            self._log("MANA", f"{current}/{maximum} ({percent:.0f}%) - {status}")
            self.last_mana_percent = percent

        if percent < self.mana_threshold:
            # Verifica se tem poção antes de usar
            if self.potion_monitor:
                can_use = self.potion_monitor.can_use_potion(self.mana_key)
                if not can_use:
                    self._log("MANA", f"🚫 SEM POÇÃO no slot [{self.mana_key}]! Pulando...")
                    return False

            self._log("MANA", f"Mana baixa ({percent:.0f}%)! Consumindo potion (tecla {self.mana_key})")
            self._press_key(self.mana_key)
            self.stats["mana_potions"] += 1
            time.sleep(0.5)  # Cooldown apos beber
            return True

        return False

    def _cast_healing(self):
        """Casta spell de healing (apenas se tiver mana suficiente)"""
        # Verifica mana atual
        current, maximum, percent = self._read_mana()

        if current is None:
            self._log("HEAL", "Falha ao ler mana, pulando cast")
            return False

        # Verifica se tem mana suficiente para castar
        if current < self.healing_mana_cost:
            self._log("HEAL", f"🚫 SEM MANA para healing ({current}/{self.healing_mana_cost})! Pulando...")
            return False

        self._log("HEAL", f"Castando healing (tecla {self.healing_key})")
        self._press_key(self.healing_key)
        self.stats["healing_casts"] += 1
        return True

    def _setup_hotkeys(self):
        """Configura hotkeys do bot"""
        toggle_key = self.settings.get("hotkeys", {}).get("toggle_bot", "F9")
        stop_key = self.settings.get("hotkeys", {}).get("emergency_stop", "F10")

        keyboard.on_press_key(toggle_key, lambda _: self._toggle_pause())
        keyboard.on_press_key(stop_key, lambda _: self._emergency_stop())

        self.logger.info(f"Hotkeys: {toggle_key}=pausar/continuar, {stop_key}=parar")

    def _toggle_pause(self):
        """Alterna pausa do bot"""
        self.paused = not self.paused
        status = "PAUSADO" if self.paused else "RODANDO"
        self._log("BOT", f"Status: {status}")

    def _emergency_stop(self):
        """Para o bot imediatamente"""
        self._log("BOT", "PARADA DE EMERGENCIA!")
        self.running = False

    def _print_stats(self):
        """Imprime estatisticas finais"""
        if self.stats["start_time"]:
            elapsed = time.time() - self.stats["start_time"]
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)

            self.logger.info("")
            self.logger.info("=" * 50)
            self.logger.info("ESTATISTICAS:")
            self.logger.info(f"  Tempo rodando: {minutes}m {seconds}s")
            self.logger.info(f"  Healing casts: {self.stats['healing_casts']}")
            self.logger.info(f"  Mana potions: {self.stats['mana_potions']}")
            self.logger.info(f"  Food consumido: {self.stats['food_eaten']}")
            self.logger.info("=" * 50)

    def main_loop(self):
        """Loop principal do bot"""
        self._log("BOT", "Iniciando loop principal...")
        self.stats["start_time"] = time.time()

        while self.running:
            try:
                if self.paused:
                    time.sleep(0.1)
                    continue

                # 1. Verifica food timer
                self._check_food()

                # 2. Verifica mana
                self._check_mana()

                # 3. Casta healing
                self._cast_healing()

                # 4. Delay aleatorio entre casts
                delay = random.uniform(self.healing_min, self.healing_max)
                self._log("HEAL", f"Proximo cast em {delay:.1f}s")
                time.sleep(delay)

            except KeyboardInterrupt:
                self._log("BOT", "Interrompido pelo usuario")
                break
            except Exception as e:
                self._log("ERRO", f"{e}")
                time.sleep(1)

    def start(self):
        """Inicia o bot"""
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("    SKILL LEVEL BOT - INICIANDO")
        self.logger.info("=" * 60)
        self.logger.info("")

        # Configura hotkeys
        self._setup_hotkeys()

        # Verifica se food timer esta configurado
        if self.food_timer_region is None:
            self.logger.error("ERRO: Food timer nao calibrado!")
            self.logger.error("Execute primeiro: py tools/calibrate_food_timer.py")
            return

        self.logger.info("Pressione a tecla de toggle para iniciar...")
        self.logger.info("")

        # Aguarda usuario pressionar toggle
        self.paused = True
        self.running = True

        try:
            self.main_loop()
        finally:
            self._print_stats()
            self.logger.info("Bot finalizado.")


def print_banner():
    """Imprime banner do bot"""
    banner = """
========================================================
       TIBIA SKILL LEVEL BOT

  Treina magic level automaticamente:
  - Casta healing a cada 2-4 segundos
  - Consome mana potion quando mana baixa
  - Come food quando timer zera
========================================================
"""
    print(banner)


def main():
    """Funcao principal"""
    print_banner()

    try:
        bot = SkillLevelBot(
            settings_path="config/bot_settings.json",
            skills_path="config/skills.json"
        )
        bot.start()

    except FileNotFoundError as e:
        print(f"ERRO: Arquivo nao encontrado: {e}")
        print("Verifique se os arquivos de configuracao existem.")
        sys.exit(1)

    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

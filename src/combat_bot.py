"""
Combat Bot Principal
Orquestra captura, OCR, rotação e input
"""

import time
import json
import keyboard
import cv2
import numpy as np
from typing import Optional
from screen_capture_obs import OBSScreenCapture
from ocr_reader import OCRReader, Stats
from skill_rotation import SkillRotation
from human_behavior import HumanBehavior
from movement import Movement
from minimap_reader import MinimapReader
from utils.key_sender import get_key_sender
from utils.logger import get_logger


class CombatBot:
    """Bot de combate principal"""

    def __init__(self,
                 settings_path: str = "config/bot_settings.json",
                 skills_path: str = "config/skills.json"):
        """
        Inicializa bot

        Args:
            settings_path: Caminho para settings
            skills_path: Caminho para skills
        """
        self.logger = get_logger()
        self.logger.info("Inicializando Combat Bot...")

        # Carrega settings
        with open(settings_path, 'r') as f:
            self.settings = json.load(f)

        # Inicializa componentes
        self.screen_capture = OBSScreenCapture(
            camera_index=self.settings["obs_camera"]["device_index"]
        )

        self.ocr_reader = OCRReader(
            tesseract_config=self.settings["ocr_settings"]["config"],
            resize_scale=self.settings["ocr_settings"]["resize_scale"],
            threshold_min=self.settings["ocr_settings"]["threshold_min"],
            threshold_max=self.settings["ocr_settings"]["threshold_max"]
        )

        self.rotation = SkillRotation(skills_path)

        self.behavior = HumanBehavior(
            base_delay_ms=self.settings["human_behavior"]["base_delay_ms"],
            variance_ms=self.settings["human_behavior"]["random_variance_ms"],
            reaction_min_ms=self.settings["human_behavior"]["reaction_time_min_ms"],
            reaction_max_ms=self.settings["human_behavior"]["reaction_time_max_ms"],
            micro_pause_chance=self.settings["human_behavior"]["micro_pause_chance_percent"] / 100
        )

        self.key_sender = get_key_sender(
            method=self.settings["key_sender"]["method"],
            press_duration_min_ms=self.settings["key_sender"]["key_press_duration_min_ms"],
            press_duration_max_ms=self.settings["key_sender"]["key_press_duration_max_ms"],
            delay_between_keys_ms=self.settings["key_sender"]["delay_between_keys_ms"],
            debug=True  # Ativa debug para ver o que está acontecendo
        )

        # MinimapReader (navegação inteligente)
        minimap_settings = self.settings.get("minimap", {})
        if minimap_settings.get("enable", False):
            self.minimap_reader = MinimapReader(self.screen_capture, minimap_settings)
        else:
            self.minimap_reader = None
            self.logger.info("🗺️  Minimapa: DESATIVADO")

        # Estado
        self.running = False
        self.paused = False
        self.enabled = True  # Bot começa habilitado
        self.stats_history = []
        self.skills_used_count = 0
        self.start_time = 0

        # Auto-targeting
        self.auto_targeting_enabled = self.settings.get("auto_targeting", {}).get("enable", False)
        self.target_key = self.settings.get("auto_targeting", {}).get("target_key", "space")
        self.target_delay_ms = self.settings.get("auto_targeting", {}).get("delay_after_kill_ms", 300)
        self.target_delay_variance_ms = self.settings.get("auto_targeting", {}).get("delay_variance_ms", 100)

        # Combat (chase e loot)
        self.chase_enabled = self.settings.get("combat", {}).get("enable_chase", True)
        self.chase_key = self.settings.get("combat", {}).get("chase_key", "k")
        self.chase_on_combat = self.settings.get("combat", {}).get("chase_on_combat", True)
        self.auto_loot_enabled = self.settings.get("combat", {}).get("enable_auto_loot", True)
        self.loot_key = self.settings.get("combat", {}).get("loot_key", "alt+q")
        self.loot_delay_ms = self.settings.get("combat", {}).get("loot_delay_after_kill_ms", 500)

        # Chase button detection (coordenadas e cores)
        chase_btn_cfg = self.settings.get("combat", {}).get("chase_button", {})
        self.chase_button_x1 = chase_btn_cfg.get("x1", 1892)
        self.chase_button_y1 = chase_btn_cfg.get("y1", 163)
        self.chase_button_x2 = chase_btn_cfg.get("x2", 1911)
        self.chase_button_y2 = chase_btn_cfg.get("y2", 186)

        # Configuração de cores para detecção de chase ativo (verde)
        color_range = chase_btn_cfg.get("active_color_range", {})
        self.chase_active_color_lower = np.array([
            color_range.get("h_lower", 35),
            color_range.get("s_lower", 80),
            color_range.get("v_lower", 80)
        ])
        self.chase_active_color_upper = np.array([
            color_range.get("h_upper", 85),
            color_range.get("s_upper", 255),
            color_range.get("v_upper", 255)
        ])
        self.chase_active_threshold = chase_btn_cfg.get("active_threshold_percent", 10.0)

        # Movimento (com navegação inteligente via minimapa)
        # Passa callback para interromper movimento quando detectar criatura
        mouse_sender_method = self.settings.get("mouse_sender", {}).get("method", "SendInput")
        self.movement = Movement(
            self.key_sender,
            self.settings.get("movement", {}),
            minimap_reader=self.minimap_reader,
            interrupt_callback=self._should_interrupt_movement,
            screen_capture=self.screen_capture,
            mouse_sender_method=mouse_sender_method
        )

        # Controle de combate
        self.last_combat_time = time.time()
        self.in_combat_state = False
        self.last_auto_target_time = 0  # Para controle de cooldown

        # Movimentos aleatórios durante combate
        random_move_cfg = self.settings.get("combat", {}).get("random_movement_in_combat", {})
        self.random_movement_enabled = random_move_cfg.get("enable", True)
        self.random_movement_chance = random_move_cfg.get("chance_percent", 15) / 100.0
        self.random_movement_min_interval = random_move_cfg.get("min_interval_seconds", 3)
        self.random_movement_max_interval = random_move_cfg.get("max_interval_seconds", 8)
        self.random_movement_keys = random_move_cfg.get("keys", ["up", "down", "left", "right"])
        self.last_random_movement_time = time.time()

        # Timer para verificação contínua de chase durante combate
        self.last_chase_check_time = 0
        self.chase_check_interval_seconds = 2.0  # Verifica chase a cada 2 segundos

        # Regiões
        self.regions = self.settings["screen_regions"]

        # Estado Sentry Mode (Sentinela)
        self.sentry_mode = False
        self.last_sentry_log_time = 0

        # Configura hotkeys
        self._setup_hotkeys()

        self.logger.info("✅ Bot inicializado com sucesso!")
        self.logger.info(f"⌨️  Teclas de controle:")
        self.logger.info(f"  {self.settings['hotkeys']['toggle_bot']} - Ativar/Desativar bot")
        self.logger.info(f"  {self.settings['hotkeys'].get('toggle_sentry_mode', 'insert')} - Alternar Modo Sentinela (Parado)")
        self.logger.info(f"  {self.settings['hotkeys']['emergency_stop']} - Parada de emergência")
        if self.auto_targeting_enabled:
            self.logger.info(f"🎯 Auto-targeting: ATIVADO (tecla: {self.target_key})")
        if self.chase_enabled:
            self.logger.info(f"🏃 Chase automático: ATIVADO (tecla: {self.chase_key})")
        if self.auto_loot_enabled:
            self.logger.info(f"💰 Loot automático: ATIVADO (tecla: {self.loot_key})")

    def _setup_hotkeys(self):
        """Configura os hotkeys do bot"""
        # Toggle bot
        toggle_key = self.settings['hotkeys']['toggle_bot'].lower()
        keyboard.add_hotkey(toggle_key, self._toggle_bot)

        # Toggle sentry mode
        sentry_key = self.settings['hotkeys'].get('toggle_sentry_mode', 'insert').lower()
        keyboard.add_hotkey(sentry_key, self._toggle_sentry_mode)

        # Emergency stop
        stop_key = self.settings['hotkeys']['emergency_stop'].lower()
        keyboard.add_hotkey(stop_key, self._emergency_stop)

    def _toggle_bot(self):
        """Callback para toggle do bot"""
        self.enabled = not self.enabled
        status = "🟢 ATIVADO" if self.enabled else "🔴 DESATIVADO"
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"  BOT {status}")
        self.logger.info(f"{'='*50}\n")

    def _toggle_sentry_mode(self):
        """Callback para toggle do modo sentinela"""
        self.sentry_mode = not self.sentry_mode
        status = "🛡️ ATIVADO" if self.sentry_mode else "🏃 DESATIVADO"
        self.logger.info(f"Modo Sentinela: {status}")

    def _emergency_stop(self):
        """Callback para parada de emergência"""
        self.logger.warning("\n⚠️  PARADA DE EMERGÊNCIA ACIONADA!")
        self.running = False

    def _should_interrupt_movement(self) -> bool:
        """
        Verifica se movimento deve ser interrompido (ex: criatura detectada)
        Chamado durante wait_until_stopped para permitir interrupção rápida

        Returns:
            True se deve interromper movimento
        """
        # Captura stats rapidamente
        stats = self.get_stats()

        if stats is None:
            return False

        # Interrompe se detectou criatura
        if stats.has_creatures_nearby or stats.in_active_combat:
            return True

        return False

    def get_stats(self) -> Optional[Stats]:
        """
        Captura e lê estatísticas (HP/Mana/Target)

        Returns:
            Stats ou None
        """
        # Filtra apenas os parâmetros necessários (remove _points)
        hp_params = {k: v for k, v in self.regions["hp_bar"].items() if not k.startswith('_')}
        mana_params = {k: v for k, v in self.regions["mana_bar"].items() if not k.startswith('_')}

        # Captura regiões HP e Mana
        hp_img = self.screen_capture.capture_region(**hp_params)
        mana_img = self.screen_capture.capture_region(**mana_params)

        if hp_img is None or mana_img is None:
            return None

        # Captura região do target (se existir na config)
        target_img = None
        if "target_hp" in self.regions:
            target_params = {k: v for k, v in self.regions["target_hp"].items() if not k.startswith('_')}
            target_img = self.screen_capture.capture_region(**target_params)

        # OCR com detecção de alvo
        stats = self.ocr_reader.read_stats(hp_img, mana_img, target_img)

        return stats

    def execute_skill(self, skill):
        """Executa uma skill"""
        # Delay antes
        self.behavior.wait_before_action()

        # Envia tecla
        self.key_sender.press_key(skill.hotkey)

        # Marca como usada
        self.rotation.use_skill(skill)
        self.skills_used_count += 1

        # Log
        self.logger.debug(f"Skill: {skill.name} ({skill.hotkey})")

        # Delay após
        self.behavior.wait_after_action()

    def try_auto_target(self):
        """Tenta selecionar próximo alvo automaticamente"""
        if not self.auto_targeting_enabled or not self.enabled:
            return

        import random

        # Delay humanizado antes de pressionar a tecla
        delay = self.target_delay_ms + random.randint(
            -self.target_delay_variance_ms,
            self.target_delay_variance_ms
        )
        time.sleep(delay / 1000.0)

        # Pressiona tecla de targeting
        self.key_sender.press_key(self.target_key)
        self.logger.info(f"🎯 Auto-targeting: pressionou '{self.target_key}' para próximo alvo")

    def activate_chase(self):
        """Ativa chase (seguir criatura)"""
        if not self.chase_enabled or not self.enabled:
            return

        # Pressiona tecla de chase
        self.key_sender.press_key(self.chase_key)
        self.logger.info(f"🏃 Chase ativado (tecla: {self.chase_key})")

    def check_chase_button_state(self) -> bool:
        """
        Verifica se o botão de chase está ativo (verde) ou inativo (cinza/branco)

        Returns:
            True se ativo (verde), False se inativo (cinza/branco)
        """
        try:
            # Calcula dimensões do botão
            width = self.chase_button_x2 - self.chase_button_x1
            height = self.chase_button_y2 - self.chase_button_y1

            # Captura região do botão chase
            chase_button_img = self.screen_capture.capture_region(
                x=self.chase_button_x1,
                y=self.chase_button_y1,
                width=width,
                height=height
            )

            if chase_button_img is None:
                self.logger.warning("⚠️  Falha ao capturar botão chase")
                return False

            # Converte para HSV
            hsv = cv2.cvtColor(chase_button_img, cv2.COLOR_BGR2HSV)

            # Detecta pixels verdes (botão ativo)
            green_mask = cv2.inRange(hsv, self.chase_active_color_lower, self.chase_active_color_upper)

            # Calcula percentual de pixels verdes
            green_pixels = cv2.countNonZero(green_mask)
            total_pixels = chase_button_img.shape[0] * chase_button_img.shape[1]
            green_percent = (green_pixels / total_pixels) * 100

            # Se percentual de verde está acima do threshold, botão está ativo
            is_active = green_percent > self.chase_active_threshold

            self.logger.debug(
                f"Chase button: {green_percent:.1f}% verde "
                f"(threshold: {self.chase_active_threshold}%) -> "
                f"{'ATIVO ✅' if is_active else 'INATIVO ⚪'}"
            )

            return is_active

        except Exception as e:
            self.logger.error(f"❌ Erro ao verificar botão chase: {e}")
            return False

    def ensure_chase_active(self):
        """
        Garante que chase está ativo, verificando visualmente o botão
        e pressionando K apenas se necessário
        """
        if not self.chase_enabled or not self.enabled:
            return

        # Verifica estado atual do botão
        is_active = self.check_chase_button_state()

        if not is_active:
            self.logger.info("🏃 Chase inativo detectado, ativando...")
            self.key_sender.press_key(self.chase_key)
            time.sleep(0.2)  # Aguarda atualização visual

            # Verifica novamente se ativou
            is_active_after = self.check_chase_button_state()
            if is_active_after:
                self.logger.info("✅ Chase ativado com sucesso!")
            else:
                self.logger.warning("⚠️  Chase pode não ter sido ativado corretamente")
        else:
            self.logger.debug("✅ Chase já está ativo, nenhuma ação necessária")

    def auto_loot(self):
        """Executa loot automático"""
        if not self.auto_loot_enabled or not self.enabled:
            return

        import random

        # Delay antes de lootar
        delay = self.loot_delay_ms / 1000.0
        time.sleep(delay)

        # Pressiona tecla de loot MÚLTIPLAS VEZES para garantir que seja recebida
        # (Tibia às vezes perde teclas se enviadas muito rápido)
        success_count = 0
        for attempt in range(3):
            success = self.key_sender.press_key(self.loot_key)
            if success:
                success_count += 1

            # Pequeno delay entre tentativas (150ms)
            if attempt < 2:  # Não dá delay após a última
                time.sleep(0.15)

        if success_count > 0:
            self.logger.info(f"💰 Loot executado")
        else:
            self.logger.error(f"❌ Falha ao enviar loot")

    def try_random_movement_in_combat(self):
        """
        Executa movimentos aleatórios durante combate (mais natural)
        Aperta setas de movimento esporadicamente
        IMPORTANTE: Reativa chase após movimento (setas desativam chase no Tibia)
        """
        if not self.random_movement_enabled or not self.enabled:
            return

        import random

        # Verifica intervalo desde último movimento
        time_since_last = time.time() - self.last_random_movement_time

        # Intervalo aleatório entre min e max
        next_interval = random.uniform(
            self.random_movement_min_interval,
            self.random_movement_max_interval
        )

        # Se passou tempo suficiente
        if time_since_last >= next_interval:
            # Chance de executar movimento
            if random.random() < self.random_movement_chance:
                # Seleciona seta aleatória
                key = random.choice(self.random_movement_keys)

                # Pressiona seta brevemente
                self.key_sender.press_key(key)
                self.logger.debug(f"🎲 Movimento aleatório em combate: {key}")

                # IMPORTANTE: Reativa chase (setas desativam chase no Tibia)
                time.sleep(0.1)  # Pequeno delay para garantir que o movimento foi processado
                self.ensure_chase_active()

            # Atualiza timestamp
            self.last_random_movement_time = time.time()

    def bot_loop(self):
        """Loop principal do bot"""
        target_fps = self.settings["bot_loop"]["fps_target"]
        frame_time = 1.0 / target_fps
        last_log_time = 0
        last_target_state = False

        while self.running:
            loop_start = time.time()

            try:
                # Obtem stats
                stats = self.get_stats()

                if stats is None:
                    self.logger.warning("Falha ao ler stats (OCR)")
                    time.sleep(0.1)
                    continue

                # Adiciona ao histórico
                self.stats_history.append(stats)

                # Log de stats a cada 3 segundos (apenas se bot estiver enabled)
                if self.enabled:
                    current_time = time.time()
                    if current_time - last_log_time >= 3.0:
                        # Define status baseado no estado
                        if stats.in_active_combat:
                            combat_status = "🔴 EM COMBATE"
                        elif stats.has_creatures_nearby:
                            combat_status = "🟡 CRIATURAS PERTO"
                        else:
                            combat_status = "⏸️  SEM CRIATURAS"

                        self.logger.info(
                            f"{combat_status} | HP: {stats.hp_current}/{stats.hp_max} ({stats.hp_percent:.0f}%) | "
                            f"Mana: {stats.mana_current}/{stats.mana_max} ({stats.mana_percent:.0f}%)"
                        )
                        last_log_time = current_time

                    # Log quando estado de combate muda
                    if stats.in_active_combat != last_target_state:
                        if stats.in_active_combat:
                            self.logger.info("⚔️  Entrando em combate ativo!")

                            # Ativa chase ao entrar em combate (verifica visualmente se já está ativo)
                            if self.chase_on_combat:
                                self.ensure_chase_active()

                            # Atualiza tempo de combate
                            self.last_combat_time = time.time()

                        else:
                            if stats.has_creatures_nearby:
                                self.logger.info("🟡 Saiu de combate (criaturas ainda próximas)")
                            else:
                                self.logger.info("✅ Combate finalizado")

                            # Sequência após matar: Loot → Auto-target
                            self.auto_loot()
                            self.try_auto_target()

                        last_target_state = stats.in_active_combat

                    # Atualiza tempo de combate se estiver em combate
                    if stats.in_active_combat or stats.has_creatures_nearby:
                        self.last_combat_time = time.time()

                        # IMPORTANTE: Cancela movimento em andamento quando detecta criatura
                        if self.movement.is_moving:
                            self.logger.info("⚔️  Criaturas detectadas! Cancelando movimento para focar em combate...")
                            self.movement.is_moving = False

                        # VERIFICAÇÃO CONTÍNUA DE CHASE (a cada 2 segundos durante combate)
                        current_time = time.time()
                        time_since_last_check = current_time - self.last_chase_check_time
                        if time_since_last_check >= self.chase_check_interval_seconds:
                            self.ensure_chase_active()
                            self.last_chase_check_time = current_time

                        # Movimentos aleatórios durante combate (mais natural)
                        if stats.in_active_combat:
                            self.try_random_movement_in_combat()

                    # HUNT AUTOMÁTICA: Tenta atacar se tem criaturas perto mas não está em combate
                    if self.enabled and not self.paused:
                        if stats.has_creatures_nearby and not stats.in_active_combat:
                            # Cooldown de 0.5s entre tentativas (evita spam)
                            time_since_last_target = time.time() - self.last_auto_target_time
                            if time_since_last_target >= 0.5:
                                self.logger.debug("🎯 Criaturas detectadas, tentando atacar...")
                                self.try_auto_target()
                                self.last_auto_target_time = time.time()

                    # Movimento aleatório quando sem criaturas (apenas se bot enabled e não pausado)
                    if self.enabled and not self.paused and not stats.has_creatures_nearby:
                        if not self.sentry_mode:
                            # IMPORTANTE: Só move se não estiver já em movimento
                            if not self.movement.is_moving:
                                time_since_combat = time.time() - self.last_combat_time
                                should_move = self.movement.should_move(time_since_combat)
                                
                                # Debug de decisão de movimento (remover depois)
                                # self.logger.debug(f"Decisão movimento: should_move={should_move}, time_since_combat={time_since_combat:.1f}s")

                                # Se passou tempo suficiente sem combate, explora área
                                if should_move:
                                    self.logger.info("🔍 Sem criaturas detectadas, explorando área...")
                                    self.movement.explore_area(max_movements=2)  # 2 movimentos aleatórios
                            else:
                                pass
                                # self.logger.debug("Movimento ignorado: já está se movendo")
                        else:
                            # Log periódico de Sentry Mode
                            if time.time() - self.last_sentry_log_time > 5.0:
                                self.logger.info("🛡️ MODO SENTINELA ATIVO - Aguardando criaturas...")
                                self.last_sentry_log_time = time.time()

                # Safety checks
                if stats.hp_percent < self.settings["safety"]["pause_on_critical_hp_percent"]:
                    self.logger.warning(f"⚠️  HP CRÍTICO! {stats.hp_percent:.0f}%")
                    self.paused = True
                    time.sleep(1)
                    continue

                if stats.hp_current == 0:
                    self.logger.critical("💀 MORTO! Parando bot...")
                    self.running = False
                    break

                # Rotação (apenas se bot estiver enabled e não pausado)
                if self.enabled and not self.paused:
                    skill = self.rotation.get_next_skill(stats)

                    if skill:
                        # Healing/Mana: sempre executa (independente do estado)
                        # Damage: APENAS se em combate ATIVO (aro vermelho)
                        should_execute = (
                            skill.skill_type in ["healing", "mana"] or
                            (skill.skill_type == "damage" and stats.in_active_combat)
                        )

                        if should_execute:
                            skill_icon = "⚔️" if skill.skill_type == "damage" else "💊"
                            self.execute_skill(skill)
                            self.logger.info(f"{skill_icon} Skill: {skill.name} ({skill.hotkey})")

                # Mantém FPS
                elapsed = time.time() - loop_start
                if elapsed < frame_time:
                    time.sleep(frame_time - elapsed)

            except KeyboardInterrupt:
                self.logger.info("Interrompido pelo usuário")
                self.running = False
                break

            except Exception as e:
                self.logger.error(f"Erro no loop: {e}")
                time.sleep(1)

    def start(self):
        """Inicia bot"""
        self.running = True
        self.start_time = time.time()
        self.logger.info("Bot iniciado! Pressione Ctrl+C para parar")

        try:
            self.bot_loop()
        finally:
            self.stop()

    def stop(self):
        """Para bot"""
        self.running = False
        uptime = time.time() - self.start_time

        # Remove hotkeys
        try:
            keyboard.unhook_all()
        except Exception as e:
            self.logger.warning(f"Erro ao remover hotkeys: {e}")

        # Estatísticas finais
        if self.stats_history:
            avg_hp = sum(s.hp_percent for s in self.stats_history) / len(self.stats_history)
            avg_mana = sum(s.mana_percent for s in self.stats_history) / len(self.stats_history)
            self.logger.stats(uptime, self.skills_used_count, avg_hp, avg_mana)

        # Estatísticas do KeySender
        key_stats = self.key_sender.get_stats()
        self.logger.info(f"\n📊 Estatísticas do KeySender:")
        self.logger.info(f"  ✅ Teclas enviadas: {key_stats['keys_sent']}")
        self.logger.info(f"  ❌ Teclas falhadas: {key_stats['keys_failed']}")
        self.logger.info(f"  📈 Taxa de sucesso: {key_stats['success_rate']:.1f}%")

        self.logger.info("Bot parado")

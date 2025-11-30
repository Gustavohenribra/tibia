"""
Tibia Combat Bot - MODO MANUAL
Usuário controla movimento, bot cuida de combate/heal/loot
"""

import sys
import os

# Adiciona src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from combat_bot import CombatBot
from utils.logger import get_logger


def print_banner():
    """Imprime banner do bot"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║       🎮 TIBIA COMBAT BOT - MODO MANUAL                 ║
║                                                          ║
║  Você controla o movimento, bot cuida do resto:         ║
║  - Chase automático (K)                                 ║
║  - Auto-targeting (Space)                               ║
║  - Loot automático (L)                                  ║
║  - Healing/Pots/Skills                                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """Main function"""
    print_banner()

    logger = get_logger(level="INFO")

    logger.info("Iniciando bot em MODO MANUAL...")
    logger.info("Você controla o movimento, bot cuida de combate/heal/loot")
    logger.info("")

    try:
        # Inicializa bot
        bot = CombatBot(
            settings_path="config/bot_settings.json",
            skills_path="config/skills.json"
        )

        # ATIVA SENTRY MODE (sem movimento automático)
        bot.sentry_mode = True
        logger.info("🛡️ MODO SENTINELA ATIVADO - Sem movimento automático")
        logger.info("")

        # Inicia
        bot.start()

    except FileNotFoundError as e:
        logger.error(f"Arquivo de configuração não encontrado: {e}")
        logger.error("Execute a calibração primeiro: py tools/calibrate_screen.py")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

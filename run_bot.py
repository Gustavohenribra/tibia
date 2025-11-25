"""
Tibia Combat Bot - Interface de Execução
Knight (EK) - Sistema Profissional Anti-Detecção
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
║         🎮 TIBIA COMBAT BOT - KNIGHT (EK)                ║
║                                                          ║
║  Sistema Profissional Anti-Detecção                     ║
║  - Captura via OBS Virtual Camera                       ║
║  - OCR Preciso (99%+)                                   ║
║  - Rotação Inteligente                                  ║
║  - Comportamento Humanizado                             ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def main():
    """Main function"""
    print_banner()

    logger = get_logger(level="INFO")

    logger.info("Iniciando bot...")
    logger.info("Certifique-se que:")
    logger.info("  1. OBS está rodando com Virtual Camera ativa")
    logger.info("  2. Tibia está aberto e visível no OBS")
    logger.info("  3. Configurações em config/ estão corretas")
    logger.info("")

    try:
        # Inicializa bot
        bot = CombatBot(
            settings_path="config/bot_settings.json",
            skills_path="config/skills.json"
        )

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

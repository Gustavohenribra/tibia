"""
Sistema de Logging Profissional
Arquivos rotativos, console colorido, níveis de log
"""

import logging
import os
from datetime import datetime
from typing import Optional
from colorama import Fore, Style, init

# Inicializa colorama para Windows
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Formatter com cores para console"""

    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
        return super().format(record)


class BotLogger:
    """Logger profissional para o bot"""

    def __init__(self, name: str = "TibiaBot", log_dir: str = "logs", level: str = "INFO"):
        """
        Inicializa logger

        Args:
            name: Nome do logger
            log_dir: Diretório de logs
            level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Remove handlers existentes
        self.logger.handlers = []

        # Cria diretório de logs
        os.makedirs(log_dir, exist_ok=True)

        # Handler de arquivo (rotativo por dia)
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"bot_{today}.log")

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Handler de console (colorido)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def debug(self, msg: str):
        """Log DEBUG"""
        self.logger.debug(msg)

    def info(self, msg: str):
        """Log INFO"""
        self.logger.info(msg)

    def warning(self, msg: str):
        """Log WARNING"""
        self.logger.warning(msg)

    def error(self, msg: str):
        """Log ERROR"""
        self.logger.error(msg)

    def critical(self, msg: str):
        """Log CRITICAL"""
        self.logger.critical(msg)

    def skill_used(self, skill_name: str, hp: int, mana: int):
        """Log de skill usada"""
        self.info(f"Skill: {skill_name} | HP: {hp} | Mana: {mana}")

    def stats(self, uptime: float, skills_used: int, avg_hp: float, avg_mana: float):
        """Log de estatísticas"""
        uptime_str = f"{int(uptime//60)}m {int(uptime%60)}s"
        self.info(
            f"Stats - Uptime: {uptime_str} | Skills: {skills_used} | "
            f"Avg HP: {avg_hp:.0f}% | Avg Mana: {avg_mana:.0f}%"
        )


# Logger global
_global_logger: Optional[BotLogger] = None


def get_logger(name: str = "TibiaBot", **kwargs) -> BotLogger:
    """Retorna logger global (singleton)"""
    global _global_logger
    if _global_logger is None:
        _global_logger = BotLogger(name, **kwargs)
    return _global_logger

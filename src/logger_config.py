import sys
from pathlib import Path

from loguru import logger

try:
    from .config import LOG_PATH
except ImportError:
    from config import LOG_PATH

def setup_logger():
    # ============================================================
    # Configuração de logging centralizado com loguru
    # ============================================================
    log_path = Path(LOG_PATH)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / "motherduck.log"

    # Remover handler padrão (stderr)
    logger.remove()

    # Adicionar handler de arquivo (persistente)
    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="5 MB",  # Rotaciona quando atingir 5MB
        retention=3,  # Mantém 3 backups
        encoding="utf-8",
    )

    # Adicionar handler de console (colorido)
    logger.add(
        sys.stdout,
        format="<level>{time:HH:mm:ss}</level> | <level>{level: <8}</level> | {message}",
        level="INFO",
        colorize=True,
    )

    logger.info("Sistema de logging inicializado")

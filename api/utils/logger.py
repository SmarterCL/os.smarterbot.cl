"""Logger setup."""
import logging
import sys
from pathlib import Path


def setup_logger(name: str = "smarter-food", log_dir: Path = None, level: str = "INFO") -> logging.Logger:
    if log_dir is None:
        log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    fh = logging.FileHandler(log_dir / "app.log")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger

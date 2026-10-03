import logging
import sys


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str = "anpr_backend") -> logging.Logger:
    return logging.getLogger(name)


logger = get_logger("anpr_backend")

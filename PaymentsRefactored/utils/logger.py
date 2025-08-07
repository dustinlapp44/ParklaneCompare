import logging
import sys


def setup_logger(log_to_console=True, log_to_file=True, level=logging.INFO, log_file_path="payments.log"):
    logger = logging.getLogger("payments")

    if logger.handlers:  # Prevent duplicate handlers on reload
        return

    logger.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_to_file:
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

import logging

from logging import Logger


def standard_logger() -> Logger:
    logger = logging.getLogger("standard")
    logger.setLevel(logging.INFO)

    standard_formatter = logging.Formatter("%(levelname)s - %(asctime)s: %(message)s")

    standard_file_handler = logging.FileHandler("logs/err.log")
    standard_file_handler.setFormatter(standard_formatter)
    standard_file_handler.setLevel(logging.ERROR)

    standard_console_handler = logging.StreamHandler()
    standard_console_handler.setFormatter(standard_formatter)

    logger.addHandler(standard_file_handler)
    logger.addHandler(standard_console_handler)

    return logger

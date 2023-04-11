import logging
from logging import Logger, handlers

from typing import Tuple


def create_loggers() -> Tuple[Logger, Logger]:

    daily_logger = logging.getLogger("daily")
    daily_logger.setLevel(logging.INFO)

    daily_formatter = logging.Formatter("%(asctime)s: %(message)s")

    daily_handler = handlers.TimedRotatingFileHandler(
        "logs/daily.log", when="midnight", utc=True, backupCount=7)
    daily_handler.setFormatter(daily_formatter)

    daily_logger.addHandler(daily_handler)

    # =================================================== #

    standard_logger = logging.getLogger("standard")
    standard_logger.setLevel(logging.DEBUG)

    standard_formatter = logging.Formatter(
        "%(levelname)s - %(asctime)s: %(message)s")

    standard_file_handler = logging.FileHandler("logs/debug.log")
    standard_file_handler.setFormatter(standard_formatter)
    standard_file_handler.setLevel(logging.INFO)

    standard_console_handler = logging.StreamHandler()
    standard_console_handler.setFormatter(standard_formatter)

    standard_logger.addHandler(standard_file_handler)
    standard_logger.addHandler(standard_console_handler)

    return (daily_logger, standard_logger)

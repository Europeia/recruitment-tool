#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Configure and return a standard logger with console and file handlers.

This module provides a factory function to create a Logger named "standard"
that logs INFO-level (and above) messages to the console and ERROR-level
(and above) messages to a file at "logs/err.log".
"""

import logging
from logging import Logger, Formatter, FileHandler, StreamHandler


def standard_logger() -> Logger:
    """Create and configure the standard application logger.

    The returned logger is named "standard" and has:
        * A console handler logging INFO and above.
        * A file handler logging ERROR and above to "logs/err.log".

    Returns:
        Logger: Configured logger instance.
    """
    logger = logging.getLogger("standard")
    logger.setLevel(logging.INFO)

    fmt = Formatter("%(levelname)s - %(asctime)s: %(message)s")

    file_handler = FileHandler("logs/err.log")
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(fmt)

    console_handler = StreamHandler()
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

import asyncio
import logging
from logging.handlers import TimedRotatingFileHandler
import signal
import sys
import tempfile
from pathlib import Path

import aiohttp
import aiomysql
from filelock import FileLock, Timeout

from components.config.errors import ConfigError
from components.config.config_model import Environment
from components.bot import Bot
from components.ns_client import NSClient
from components.queue import QueueManager


logger = logging.getLogger("main")

try:
    from components.config.config_manager import configInstance
except ConfigError:
    logger.exception("error loading configuration")
    sys.exit(1)


async def main():
    match configInstance.data.environment:
        case Environment.PRODUCTION:
            log_file = Path(__file__).resolve().parent / "asperta.log"

            formatter = logging.Formatter(
                fmt="%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )

            file_handler = TimedRotatingFileHandler(filename=log_file, when="midnight", backupCount=7, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        case _:
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )

            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

    logger.setLevel(configInstance.data.log_level)
    logger.info("configured %s logging", configInstance.data.environment)

    async with aiohttp.ClientSession() as session:
        async with aiomysql.create_pool(
            host=configInstance.data.db_host,
            port=configInstance.data.db_port,
            user=configInstance.data.db_user,
            password=configInstance.data.db_password,
            db=configInstance.data.db_name,
            autocommit=True,
            init_command="SET SESSION time_zone='+00:00'",
        ) as pool:
            ns = NSClient(session)
            async with QueueManager(pool) as ql:
                async with Bot(ns, ql, pool) as bot:
                    if sys.platform != "win32":
                        loop = asyncio.get_running_loop()

                        def request_shutdown(signame: str):
                            logger.info("Received %s, shutting down.", signame)
                            asyncio.create_task(bot.close())

                        for sig in (signal.SIGINT, signal.SIGTERM):
                            loop.add_signal_handler(sig, request_shutdown, sig.name)

                    await bot.start(configInstance.data.bot_token)


if __name__ == "__main__":
    lock_path = Path(tempfile.gettempdir()) / "asperta.lock"

    lock = FileLock(lock_path, timeout=0)

    try:
        with lock:
            asyncio.run(main())
    except Timeout:
        logger.error("lock held; shutting down")

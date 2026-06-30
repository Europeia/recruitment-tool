import asyncio
import logging
import signal
import sys
import tempfile
from pathlib import Path

import aiohttp
import aiomysql
from filelock import FileLock, Timeout

from components.config.errors import ConfigError

try:
    from components.config.config_manager import configInstance
except ConfigError as e:
    print(f"Error loading configuration: {e}", file=sys.stderr)
    sys.exit(1)

from components.bot import Bot
from components.ns_client import NSClient
from components.queue import QueueManager

logger = logging.getLogger("main")
handler = logging.StreamHandler()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


async def main():
    async with aiohttp.ClientSession() as session:
        pool = await aiomysql.create_pool(
            host=configInstance.data.db_host,
            port=configInstance.data.db_port,
            user=configInstance.data.db_user,
            password=configInstance.data.db_password,
            db=configInstance.data.db_name,
            autocommit=True,
            init_command="SET SESSION time_zone='+00:00'",
        )

        try:
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

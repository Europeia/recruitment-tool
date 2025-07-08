import aiohttp
import aiomysql
import asyncio
import logging

from components.bot import Bot
from components.config.config_manager import configInstance
from components.queue import QueueList

logger = logging.getLogger("main")
hndlr = logging.StreamHandler()
logger.addHandler(hndlr)
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

        async with QueueList(pool) as ql:
            async with Bot(session, ql, pool) as bot:
                await bot.start(configInstance.data.bot_token)


if __name__ == "__main__":
    asyncio.run(main())

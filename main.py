import aiohttp
import aiomysql
import asyncio

from components.bot import Bot
from components.config.config_manager import configInstance


async def main():
    async with aiohttp.ClientSession() as session:
        pool = await aiomysql.create_pool(
            host=configInstance.data.db_host,
            port=configInstance.data.db_port,
            user=configInstance.data.db_user,
            password=configInstance.data.db_password,
            db=configInstance.data.db_name,
            autocommit=True,
            init_command="SET SESSION time_zone='+00:00'"
        )

        async with Bot(session, pool) as bot:
            await bot.start(configInstance.data.bot_token)


if __name__ == '__main__':
    asyncio.run(main())

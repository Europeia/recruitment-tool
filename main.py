#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main entry point for the asynchronous bot application.

This module initializes an aiohttp ClientSession for HTTP requests and an
aiomysql connection pool configured for UTC timezone. It then instantiates
the Bot and starts it with the configured token.

Exported Functions:
    main(): Coroutine that sets up HTTP and DB connections and starts the bot.

Typical usage example:

    python main.py
"""

import asyncio
import aiohttp
import aiomysql

from components.bot import Bot
from components.config.config_manager import configInstance


async def main() -> None:
    """Run the bot: set up HTTP session and MySQL connection pool.

    This coroutine creates an aiohttp ClientSession for HTTP requests
    and an aiomysql connection pool configured for UTC timezone. It
    then instantiates the Bot and starts it with the provided token.

    Raises:
        aiohttp.ClientError: If the HTTP session encounters an error.
        aiomysql.MySQLError: If the MySQL pool cannot be created.
    """
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

        async with Bot(session, pool) as bot:
            await bot.start(configInstance.data.bot_token)


if __name__ == "__main__":
    asyncio.run(main())

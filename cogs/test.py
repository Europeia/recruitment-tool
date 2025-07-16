#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test commands for the NationStates recruitment bot.

Provides simple diagnostic and information commands:
  * get: Fetch and display the full nation name for 'upc'.
  * debug: Show current API rate limit status.
"""

from discord.ext import commands
from discord.ext.commands import Context

from components.bot import Bot


class TestCog(commands.Cog):
    """Cog for basic test and diagnostic commands.

    Args:
        bot (Bot): The bot instance.
    """

    def __init__(self, bot: Bot) -> None:
        """Initialize the TestCog.

        Args:
            bot (Bot): The bot instance.
        """
        self.bot = bot

    @commands.hybrid_command(
        name="get",
        with_app_command=True,
        description="Fetch and display the full nation name for UPC.",
    )
    async def get(self, ctx: Context) -> None:
        """Fetch nation data and reply with the full nation name.

        Sends a GET request to the NationStates API for nation 'upc'
        and replies with the FULLNAME field.

        Args:
            ctx (Context): Invocation context.
        """
        response = await self.bot.request(
            "https://www.nationstates.net/cgi-bin/api.cgi?nation=upc"
        )
        await ctx.reply(response.FULLNAME.text)

    @commands.hybrid_command(
        name="debug",
        with_app_command=True,
        description="Display current API rate limit status.",
    )
    async def debug(self, ctx: Context) -> None:
        """Reply with current rate limit information.

        Shows the total limit, remaining requests, and reset interval.

        Args:
            ctx (Context): Invocation context.
        """
        msg = (
            f"Limit: {self.bot.ratelimit}\n"
            f"Remaining: {self.bot.remaining}\n"
            f"Reset In: {self.bot.reset_in}"
        )
        await ctx.reply(msg)


async def setup(bot: Bot) -> None:
    """Add the TestCog to the bot.

    Args:
        bot (Bot): The bot instance.
    """
    await bot.add_cog(TestCog(bot))

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Base administrative commands for the recruitment bot.

Defines:
    * is_authorized: decorator to restrict commands to bot administrators.
    * Base cog: sync, reload, and kill commands.
"""

from discord.ext import commands

from components.bot import Bot


def is_authorized():
    """Decorator ensuring the invoker is a bot administrator.

    Returns:
        Callable: A decorator for commands.check.

    Raises:
        commands.MissingPermissions: If the user is not an administrator.
    """
    def predicate(ctx: commands.Context) -> bool:
        """Check invocation context for admin permissions.

        Args:
            ctx (commands.Context): The command invocation context.

        Returns:
            bool: True if the user is authorized.

        Raises:
            commands.MissingPermissions: If the user's ID is not in the admin list.
        """
        admin_ids = [230778695713947648, 110600636319440896]
        if ctx.author.id not in admin_ids:
            raise commands.MissingPermissions(["Bot Administrator"])
        return True

    return commands.check(predicate)


class Base(commands.Cog):
    """Administrative commands cog.

    Provides commands to sync slash commands, reload cogs, and shut down the bot.
    """

    def __init__(self, bot: Bot) -> None:
        """Initialize the Base cog.

        Args:
            bot (Bot): The bot instance.
        """
        self.bot = bot

    @commands.command(
        name="sync",
        description="Sync slash commands"
    )
    @is_authorized()
    async def sync(self, ctx: commands.Context) -> None:
        """Sync application (slash) commands with Discord.

        Args:
            ctx (commands.Context): The command invocation context.
        """
        await ctx.defer()
        synced = await self.bot.tree.sync()
        print(synced)
        await ctx.reply("Done!")

    @commands.command(
        name="reload",
        description="Reload a cog"
    )
    @is_authorized()
    async def reload(self, ctx: commands.Context, cog: str) -> None:
        """Reload the specified cog extension.

        Args:
            ctx (commands.Context): The command invocation context.
            cog (str): Name of the cog to reload (without module path).
        """
        await self.bot.reload_extension(f"cogs.{str(cog)}")
        await ctx.reply(f"Reloaded cog: {str(cog)}")

    @commands.command(
        name="kill",
        description="Put the bot to sleep"
    )
    @is_authorized()
    async def kill(self, ctx: commands.Context) -> None:
        """Shut down the bot gracefully.

        Args:
            ctx (commands.Context): The command invocation context.
        """
        await ctx.reply("Goodbye!")
        await self.bot.close()


async def setup(bot: Bot) -> None:
    """Add the Base cog to the bot.

    Args:
        bot (Bot): The bot instance.
    """
    await bot.add_cog(Base(bot))

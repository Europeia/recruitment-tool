#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Global error handling Cog for both prefix and application commands.

This module defines the Error cog, which intercepts errors from both
text commands and slash commands, logs them, and sends user-friendly
responses.
"""

from discord import Interaction
from discord import app_commands
from discord.ext import commands

from components.bot import Bot
from components.errors import WhitelistError


class Error(commands.Cog):
    """Cog for intercepting and handling command errors."""

    def __init__(self, bot: Bot) -> None:
        """Initialize the error handler and register the slash-command error hook.

        Args:
            bot (Bot): The bot instance.
        """
        self.bot = bot
        self.bot.tree.on_error = self.on_app_command_error

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ) -> None:
        """Handle errors raised by prefix (text) commands.

        Logs the error and replies with an appropriate message.

        Args:
            ctx (commands.Context): Invocation context.
            error (commands.CommandError): The exception raised.
        """
        if hasattr(self.bot, "std"):
            self.bot.std.error(f"Error in command {str(ctx.command)}: {str(error)}", exc_info=error) 
        else:
            print(f"Error in command {str(ctx.command)}: {str(error)}")
            print(type(error))

        if isinstance(error, commands.MissingPermissions):
            await ctx.reply(
                "You must be an Admin or Recruit Manager to run this command.",
                ephemeral=True,
            )
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                f"Missing required argument: {str(error.param)}", ephemeral=True
            )
        else:
            await ctx.reply(f"{str(error)}", ephemeral=True)

    @staticmethod
    async def on_app_command_error(
        interaction: Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Handle errors raised by application (slash) commands.

        Sends a user-friendly message based on the error type.

        Args:
            interaction (Interaction): The interaction that failed.
            error (app_commands.AppCommandError): The exception raised.
        """
        # Log to console; slash-command errors can't use ctx
        print(f"Slash command error: {str(error)}")
        print(type(error))

        if isinstance(error, WhitelistError):
            await interaction.response.send_message(
                "This server is not whitelisted for recruitment. "
                "Please contact a bot administrator.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"An error occurred:\n```{str(error)}```", ephemeral=True
            )


async def setup(bot: Bot) -> None:
    """Add the Error cog to the bot.

    Args:
        bot (Bot): The bot instance.
    """
    await bot.add_cog(Error(bot))

import discord
import logging

from discord import app_commands
from discord.ext import commands

from components.bot import Bot
import components.errors as errors

logger = logging.getLogger("main")


class Error(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.tree.on_error = self.on_error

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        logger.error("command error: %s (%s)", error, type(error))

        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("You must be an Admin or Recruit Manager to run this command.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Missing required argument: {error.param}", ephemeral=True)
        else:
            await ctx.reply("an unexpected error occurred, please contact a bot administrator", ephemeral=True)

    @staticmethod
    async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        logger.error("app command error: %s (%s)", error, type(error))

        if isinstance(error, errors.WhitelistError):
            await interaction.response.send_message(
                "This server is not whitelisted for recruitment. Please contact a bot administrator.", ephemeral=True
            )
        else:
            await interaction.response.send_message("an unexpected error occurred, please contact a bot administrator", ephemeral=True)


async def setup(bot: Bot):
    await bot.add_cog(Error(bot))

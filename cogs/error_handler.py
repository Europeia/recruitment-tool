import discord

from discord import app_commands
from discord.ext import commands

from components.bot import Bot
import components.errors as errors


class Error(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.tree.on_error = self.on_error

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # self.bot.std.error(error)
        print(error)
        print(type(error))

        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("You must be an Admin or Recruit Manager to run this command.", ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Missing required argument: {error.param}", ephemeral=True)
        else:
            await ctx.reply(f"{error}\n\n{type(error)}", ephemeral=True)

    @staticmethod
    async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        print(error)
        print(type(error))

        if isinstance(error, errors.WhitelistError):
            await interaction.response.send_message(
                f"This server is not whitelisted for recruitment. Please contact a bot administrator.", ephemeral=True
            )
        else:
            await interaction.response.send_message(f"An error occurred:\n```{error}```\n{type(error)}", ephemeral=True)


async def setup(bot: Bot):
    await bot.add_cog(Error(bot))

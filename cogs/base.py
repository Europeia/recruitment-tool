# from functools import wraps
from discord import app_commands
from discord.ext import commands

from components.bot import RecruitBot
from components.config.config_manager import configInstance

# def guilds_wrapper(f):
#     @wraps(f)
#     def _impl(self, *method_args, **method_kwargs):
#         app_commands.guilds(configInstance.data.guild)
#         return f(*method_args, **method_kwargs)
#     return _impl

class Base(commands.Cog):
    def __init__(self, bot: RecruitBot):
        self.bot = bot

    @commands.hybrid_command(name="reload", with_app_command=True, description="Reload recruitment cog")
    @app_commands.guilds(configInstance.data.guild)
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx: commands.Context, extension: str):
        await ctx.defer()

        if extension not in self.bot.default_cogs:
            await ctx.reply("That is not a valid extension.")
            return

        await self.bot.reload_extension(f"cogs.{extension}")
        self.bot.std.info(f"Reloaded {extension} cog")

        await ctx.reply("Reloaded cog!")

    @commands.hybrid_command(name="sync", with_app_command=True, description="Sync slash commands")
    @app_commands.guilds(configInstance.data.guild)
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context):
        await ctx.defer()

        await self.bot.tree.sync(guild=configInstance.data.guild)
        self.bot.std.info(f"Synced slash commands for {self.bot.user}")

        await ctx.reply("Done!")

    @commands.hybrid_command(name="kill", with_app_command=True, description="Put the bot to sleep")
    @app_commands.guilds(configInstance.data.guild)
    @commands.has_permissions(administrator=True)
    async def kill(self, ctx: commands.Context):
        await ctx.defer()

        await ctx.reply("Goodbye!")
        self.bot.std.info(f"Bot shutdown initiated by {ctx.author}")
        await self.bot.close()


async def setup(bot: RecruitBot):
    await bot.add_cog(Base(bot))

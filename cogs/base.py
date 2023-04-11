from discord import app_commands
from discord.ext import commands

import config
from components.bot import RecruitBot


class Base(commands.Cog):
    def __init__(self, bot: RecruitBot):
        self.bot = bot

    @commands.hybrid_command(name="reload", with_app_command=True, description="Reload recruitment cog")
    @app_commands.guilds(config.SERVER)
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
    @app_commands.guilds(config.SERVER)
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context):
        await ctx.defer()

        await self.bot.tree.sync(guild=config.SERVER)
        self.bot.std.info(f"Synced slash commands for {self.bot.user}")

        await ctx.reply("Done!")

    @commands.hybrid_command(name="kill", with_app_command=True, description="Put the bot to sleep")
    @app_commands.guilds(config.SERVER)
    @commands.has_permissions(administrator=True)
    async def kill(self, ctx: commands.Context):
        await ctx.defer()

        await ctx.reply("Goodbye!")
        self.bot.std.info(f"Bot shutdown initiated by {ctx.author}")
        await self.bot.close()


async def setup(bot: RecruitBot):
    await bot.add_cog(Base(bot))

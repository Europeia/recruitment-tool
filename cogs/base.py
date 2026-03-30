from discord.ext import commands

from components.bot import Bot
from components.checks import is_global_admin_text


class Base(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="sync", description="Sync slash commands")
    @commands.check(is_global_admin_text)
    async def sync(self, ctx: commands.Context):
        await ctx.defer()

        await self.bot.tree.sync()
        await ctx.reply("Done!")

    @commands.command(name="reload", description="Reload a cog")
    @commands.check(is_global_admin_text)
    async def reload(self, ctx: commands.Context, cog: str):
        await self.bot.reload_extension(f"cogs.{cog}")
        await ctx.reply(f"Reloaded cog: {cog}")

    @commands.command(name="kill", description="Put the bot to sleep")
    @commands.check(is_global_admin_text)
    async def kill(self, ctx: commands.Context):
        await ctx.reply("Goodbye!")
        await self.bot.close()


async def setup(bot: Bot):
    await bot.add_cog(Base(bot))

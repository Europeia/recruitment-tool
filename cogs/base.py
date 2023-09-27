from discord.ext import commands

from components.bot import Bot


class Base(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(name="sync", with_app_command=True, description="Sync slash commands")
    async def sync(self, ctx: commands.Context):
        await ctx.defer()

        await self.bot.tree.sync()

        await ctx.reply("Done!")

    @commands.hybrid_command(name="load", with_app_command=True, description="Load a cog")
    async def load(self, ctx: commands.Context):
        await ctx.reply("TODO")

    @commands.hybrid_command(name="reload", with_app_command=True, description="Reload a cog")
    async def reload(self, ctx: commands.Context, cog: str):
        await self.bot.reload_extension(f"cogs.{cog}")
        await ctx.reply(f"Reloaded cog: {cog}")

    @commands.hybrid_command(name="kill", with_app_command=True, description="Put the bot to sleep")
    async def kill(self, ctx: commands.Context):
        await ctx.reply("Goodbye!")
        await self.bot.close()


async def setup(bot: Bot):
    await bot.add_cog(Base(bot))

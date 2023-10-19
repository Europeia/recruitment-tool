import discord

from discord.ext import commands

from components.bot import Bot


def is_authorized():
    def predicate(ctx: commands.Context):
        if not (discord.utils.get(ctx.author.roles, name="Admin") or discord.utils.get(ctx.author.roles, name="Recruit Manager")):
            raise commands.MissingPermissions(["Admin", "Recruit Manager"])

        return True

    return commands.check(predicate)


class Base(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(name="sync", with_app_command=True, description="Sync slash commands")
    @is_authorized()
    async def sync(self, ctx: commands.Context):
        await ctx.defer()

        await self.bot.tree.sync()

        await ctx.reply("Done!")

    @commands.hybrid_command(name="reload", with_app_command=True, description="Reload a cog")
    @is_authorized()
    async def reload(self, ctx: commands.Context, cog: str):
        await self.bot.reload_extension(f"cogs.{cog}")
        await ctx.reply(f"Reloaded cog: {cog}")

    @commands.hybrid_command(name="kill", with_app_command=True, description="Put the bot to sleep")
    @is_authorized()
    async def kill(self, ctx: commands.Context):
        await ctx.reply("Goodbye!")
        await self.bot.close()


async def setup(bot: Bot):
    await bot.add_cog(Base(bot))

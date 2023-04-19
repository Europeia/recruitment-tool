from discord.ext import commands

from components.bot import RecruitBot
from components.errors import *


class Error(commands.Cog):
    def __init__(self, bot: RecruitBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        print(error)
        if isinstance(error, NotRecruiter):
            await ctx.reply("You need the recruiter role to perform this command!")
        elif isinstance(error, NotRegistered):
            await ctx.reply("You need to register to perform this command! Use /register")
        elif isinstance(error, EmptyQueue):
            await ctx.reply("The queue is empty!")
        elif isinstance(error, LastRecruitTooRecent):
            await ctx.reply(f"Last recruitment too recent! Please try again in {error.retry_in:.2f} seconds")
        elif isinstance(error, SessionAlreadyStarted):
            await ctx.reply("You are already in a recruitment session!")
        elif isinstance(error, ActiveSession):
            await ctx.reply("You cannot use /recruit while in a recruitment session!")
        elif isinstance(error, NotRecruitmentChannel):
            pass
        else:
            await ctx.reply(error)


async def setup(bot: RecruitBot):
    await bot.add_cog(Error(bot))

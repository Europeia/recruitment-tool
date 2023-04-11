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
        elif isinstance(error, NotRecruitmentChannel):
            pass
        else:
            await ctx.reply(error)


async def setup(bot: RecruitBot):
    await bot.add_cog(Error(bot))

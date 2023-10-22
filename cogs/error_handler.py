from discord.ext import commands

from components.bot import Bot


class Error(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        self.bot.std.error(error)

        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("You must be an Admin or Recruit Manager to run this command.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Missing required argument: {error.param}")
        else:
            await ctx.reply(f"{error}\n\n{type(error)}")


async def setup(bot: Bot):
    await bot.add_cog(Error(bot))

from discord.ext import commands

from components.bot import Bot


class TestCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(name="get", with_app_command=True, description="Get nation info")
    async def get(self, ctx: commands.Context):
        text = await self.bot.request("https://www.nationstates.net/cgi-bin/api.cgi?nation=upc")

        await ctx.reply(text.FULLNAME.text)

    @commands.hybrid_command(name="debug", with_app_command=True, description="See ratelimit compliance bullshit")
    async def debug(self, ctx: commands.Context):
        await ctx.reply(f"Limit: {self.bot.ratelimit}\nRemaining: {self.bot.remaining}\nReset In: {self.bot.reset_in}")

    # group = app_commands.Group(name="parent", description="this is a description")
    #
    # @app_commands.command(name="top")
    # async def top(self, interaction: discord.Interaction):
    #     await interaction.response.send_message("this is a top")
    #
    # @group.command(name="bottom")
    # async def bottom(self, interaction: discord.Interaction):
    #     await interaction.response.send_message("this is a bottom")


async def setup(bot: Bot):
    await bot.add_cog(TestCog(bot))

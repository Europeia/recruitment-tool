import re

from discord.ext import commands, tasks

from components.bot import Bot
from components.config.config_manager import configInstance
from components.recruitment import RecruitView


class Recruit(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.pattern = re.compile(r'^\d+_|_\d+$')

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.update_loop.is_running():
            self.bot.std.info("Starting update loop")
            self.update_loop.start()

    @commands.command(name="init", description="Send an empty message to be used for the recruitment home page")
    @commands.has_permissions(administrator=True)
    async def init(self, ctx: commands.Context):
        await ctx.send("Hello, world!", view=RecruitView(self.bot.pool, self.bot.std))

    @tasks.loop(seconds=15)
    async def update_loop(self):
        try:
            await self.update_queue()
        except Exception as e:
            self.bot.std.error(f"Error in update_loop: {e}")

    async def update_queue(self):
        self.bot.std.info("Updating queue")

        new_nations = await self.bot.request("https://www.nationstates.net/cgi-bin/api.cgi?q=newnationdetails")
        valid_nations = []
        current_nations = self.bot.queue.get_nation_names()
        last_update = int(self.bot.queue.last_updated.timestamp())

        for nation in reversed(new_nations.find_all("NEWNATION")):
            nation_name = nation.attrs["name"]
            if nation_name not in current_nations \
                    and nation.REGION.text not in configInstance.data.recruitment_exceptions \
                    and int(nation.FOUNDEDTIME.text) > last_update \
                    and not self.pattern.search(nation_name):
                valid_nations.append(nation_name)

        self.bot.queue.update(valid_nations)
        await self.bot.update_status()


async def setup(bot: Bot):
    await bot.add_cog(Recruit(bot))

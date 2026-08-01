from discord.ext import commands, tasks


class SessionCog(commands.Cog):
    def __init__(self, bot):
        self._bot = bot

    @tasks.loop(seconds=15)
    async def _run(self):
        pass

    async def cog_load(self):
        self._run.start()

    async def cog_unload(self):
        self._run.stop()

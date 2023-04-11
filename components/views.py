from discord.ui import View


class RecruitView(View):
    def __init__(self):
        super().__init__(timeout=120)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        await self.message.edit(view=None)
        self.stop()

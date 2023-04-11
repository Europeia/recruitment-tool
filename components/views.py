from discord import Message
from discord.ui import View


class RecruitView(View):
    message: Message
    
    def __init__(self):
        super().__init__()

    async def on_timeout(self):
        self.value = None
        for child in self.children:
            child.disabled = True

        await self.message.edit(view=self)
        self.stop()

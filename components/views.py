import discord

from discord import Message
from discord.ui import View


class RecruitView(View):
    message: Message

    def __init__(self):
        super().__init__(timeout=45)

    async def on_timeout(self):
        # for child in self.children:
        #    child.disabled = True

        await self.message.edit(view=None)
        self.stop()


class SessionView(View):
    message: Message
    # session: Session

    def __init__(self, session):
        from components.session import Session
        super().__init__(timeout=session.interval)
        self.session: Session = session

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        self.session.strikes += 1
        await self.message.edit(view=self)
        self.stop()

    @discord.ui.button(label="✓", style=discord.ButtonStyle.green)
    async def ack_callback(self, interaction: discord.Interaction, button):
        from components.recruitment import RecruitType, get_recruit_embed

        if interaction.user.id != self.session.user.id:
            await interaction.response.send_message("You canot interact with another user's session.")
            return

        self.session.strikes = 0

        for child in self.children:
            child.disabled = True

        embed, link_button = get_recruit_embed(self.session.user, self.session.bot, RecruitType.SESSION)

        self.add_item(link_button)

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="❌", style=discord.ButtonStyle.red)
    async def cancel_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.session.user.id:
            await interaction.response.send_message("You canot interact with another user's session.")
            return

        self.session.test.cancel()
        self.session.bot.rusers.get(self.session.user).active_session = False

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(content="Session ended", view=self)
        self.stop()

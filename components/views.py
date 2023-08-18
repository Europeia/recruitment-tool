import discord

from discord import Message
from discord.ui import View

from components.errors import EmptyQueue, LastRecruitTooRecent


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
    # bot: RecruitBot
    message: Message

    # session: Session

    def __init__(self, session, bot):
        from components.bot import RecruitBot
        from components.session import Session
        super().__init__(timeout=session.interval)
        self.session: Session = session
        self.bot: RecruitBot = bot

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
            await interaction.response.send_message("You cannot interact with another user's session.", ephemeral=True)
            return

        self.session.strikes = 0

        for child in self.children:
            child.disabled = True

        try:
            embed, link_button = get_recruit_embed(self.session.user, self.session.bot, RecruitType.SESSION)
        except EmptyQueue:
            await interaction.response.edit_message(content="Received user acknowledgement, but queue is empty.",
                                                    view=self)
        except LastRecruitTooRecent:
            await interaction.response.edit_message(
                content="Received user acknowledgement, but last recruitment was too recent.", view=self)
        else:
            self.add_item(link_button)

            await interaction.response.edit_message(embed=embed, view=self)
        finally:
            self.stop()

    @discord.ui.button(label="✗", style=discord.ButtonStyle.red)
    async def cancel_callback(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.session.user.id:
            await interaction.response.send_message("You canot interact with another user's session.")
            return

        self.session.recruit_loop.cancel()
        self.bot.sessions.pop(self.session.user.id)
        self.session.bot.rusers.get(self.session.user).active_session = False

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(content="Session ended", view=self)
        self.stop()

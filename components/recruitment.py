import discord

from datetime import datetime, timezone
from discord.ui import Modal, View

from components.bot import Bot
from components.errors import NotRegistered


class RegistrationModal(Modal, title="Registration"):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    nation = discord.ui.TextInput(
        label="Nation",
        placeholder="Enter your nation name",
        min_length=3,
        max_length=40,
    )

    recruitment_template = discord.ui.TextInput(
        label="Recruitment Template",
        placeholder="Enter your recruitment template",
        min_length=10,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                nation = self.nation.value.strip().lower().replace(" ", "_")
                template = self.recruitment_template.value.replace("%", "")
                recruiter = await self.bot.get_recruiter(interaction.user.id)

                if recruiter:
                    await cur.execute('UPDATE users SET nation = %s, recruitTemplate = %s WHERE discordId = %s;',
                                      (nation, template, recruiter.discord_id))
                else:
                    await cur.execute('INSERT INTO users (discordId, nation, recruitTemplate) VALUES (%s, %s, %s);',
                                      (interaction.user.id, nation, template))

                # await conn.commit()
                await interaction.response.send_message("Registration complete!", ephemeral=True, delete_after=10)

    async def on_error(self, interation: discord.Interaction, error: Exception):
        await interation.followup.send(f"An error occurred: {error}", ephemeral=True)


class RecruitView(View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label='Recruit', style=discord.ButtonStyle.blurple, custom_id='recruitment_view:recruit')
    async def recruit(self, interaction: discord.Interaction, _button: discord.ui.button):
        embed, view = await create_recruitment_response(interaction.user, self.bot)
        view.message = await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=30)
        await self.bot.update_status()

    @discord.ui.button(label='Register', style=discord.ButtonStyle.blurple, custom_id='recruitment_view:register')
    async def register(self, interaction: discord.Interaction, _button: discord.ui.button):
        await interaction.response.send_modal(RegistrationModal(self.bot))

    async def on_error(self, interaction: discord.Interaction, error: Exception, _item: discord.ui.Item):
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


class TelegramView(View):
    message: discord.Message

    def __init__(self):
        super().__init__(timeout=30)

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)
        self.stop()


async def create_recruitment_response(user: discord.User, bot: Bot):
    recruiter = await bot.get_recruiter(user.id)

    if not recruiter:
        raise NotRegistered(user)
    else:
        nations = bot.queue.get_nations(user=user)

        embed = discord.Embed(title=f"Recruit", color=int("2d0001", 16))
        embed.add_field(name="Nations", value="\n".join([f"https://www.nationstates.net/nation={nation}" for nation in nations]))
        embed.add_field(name="Template", value=f"```{recruiter.template}```", inline=False)
        embed.set_footer(text=f"Initiated by {recruiter.nation} at {datetime.now(timezone.utc).strftime('%H:%M:%S')}")

        view = TelegramView()
        view.add_item(discord.ui.Button(label="Open Telegram", style=discord.ButtonStyle.link,
                                        url=f"https://www.nationstates.net/page=compose_telegram?tgto={','.join(nations)}&message=%25{recruiter.template}%25"))

        return embed, view

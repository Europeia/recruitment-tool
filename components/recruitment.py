import discord

from datetime import datetime, timezone
from discord.ui import Modal, View

from components.bot import Bot
from components.errors import LastRecruitmentTooRecent, NotRecruitManager


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

    session_length = discord.ui.TextInput(
        label="Session Length (in seconds)",
        placeholder="Session length (45 - 600 seconds)",
        default='60',
        min_length=1,
        max_length=3,
    )

    async def on_submit(self, interaction: discord.Interaction):
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                nation = self.nation.value.strip().lower().replace(" ", "_")
                template = self.recruitment_template.value.replace("%", "")

                try:
                    session_length = int(self.session_length.value)
                except ValueError:
                    raise Exception("Session length must be a number")

                if session_length < 45 or session_length > 600:
                    raise Exception("Session length must be between 45 and 600 seconds")

                recruiter_id = await self.bot.get_recruiter_id(interaction.user)

                if recruiter_id:
                    await cur.execute('UPDATE users SET nation = %s, recruitTemplate = %s, sessionLength = %s WHERE id = %s;',
                                      (nation, template, session_length, recruiter_id))
                else:
                    await cur.execute('INSERT INTO users (discordId, nation, recruitTemplate, sessionLength) VALUES (%s, %s, %s, %s);',
                                      (interaction.user.id, nation, template, session_length))

                # await conn.commit()
                await interaction.response.send_message("Registration complete!", ephemeral=True, delete_after=10)

    async def on_error(self, interation: discord.Interaction, error: Exception):
        self.bot.std.error(error)
        await interation.response.send_message(f"An error occurred: {error}", ephemeral=True)


class ReportModal(Modal, title="Recruitment Report"):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    start_time = discord.ui.TextInput(
        label="Start Time",
        placeholder="YYYY-MM-DD HH:MM:SS",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        min_length=10,
        max_length=19,
    )

    end_time = discord.ui.TextInput(
        label="End Time",
        placeholder="YYYY-MM-DD HH:MM:SS",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        min_length=10,
        max_length=19,
    )

    async def on_submit(self, interaction: discord.Interaction):
        start_time = datetime.fromisoformat(self.start_time.value).replace(tzinfo=timezone.utc)
        end_time = datetime.fromisoformat(self.end_time.value).replace(tzinfo=timezone.utc)

        if start_time > end_time:
            raise Exception("Start time must be before end time")

        result = await self.bot.get_telegrams(start_time, end_time)

        resp = "\n".join([f"{nation}: {count}" for nation, count in result])
        await interaction.response.send_message(
            f"Recruitment Report: <t:{int(start_time.timestamp())}:f> to <t:{int(end_time.timestamp())}:f>\n```{resp}```", ephemeral=True
        )

    async def on_error(self, interation: discord.Interaction, error: Exception):
        self.bot.std.error(error)
        await interation.response.send_message(f"An error occurred: {error}", ephemeral=True)


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

    @discord.ui.button(label='Report', style=discord.ButtonStyle.blurple, custom_id='recruitment_view:report')
    async def report(self, interaction: discord.Interaction, _button: discord.ui.button):
        # check if the user has the 'Recruit Manager' role
        if not discord.utils.get(interaction.user.roles, name="Recruit Manager"):
            raise NotRecruitManager(interaction.user)

        await interaction.response.send_modal(ReportModal(self.bot))

    async def on_error(self, interaction: discord.Interaction, error: Exception, _item: discord.ui.Item):
        self.bot.std.error(error)
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
    recruiter = await bot.get_recruiter(user)

    current_time = datetime.utcnow()

    if recruiter.next_recruitment_at > current_time:
        print(recruiter.next_recruitment_at, current_time)
        reset_in = (recruiter.next_recruitment_at - current_time).total_seconds()
        raise LastRecruitmentTooRecent(user, reset_in)

    nations = bot.queue.get_nations(user=user)

    await bot.set_next_recruitment_at(user, len(nations))
    await bot.update_telegram_count(user, len(nations))

    embed = discord.Embed(title=f"Recruit", color=int("2d0001", 16))
    embed.add_field(name="Nations", value="\n".join([f"https://www.nationstates.net/nation={nation}" for nation in nations]))
    embed.add_field(name="Template", value=f"```{recruiter.template}```", inline=False)
    embed.set_footer(text=f"Initiated by {recruiter.nation} at {datetime.now(timezone.utc).strftime('%H:%M:%S')}")

    view = TelegramView()
    view.add_item(discord.ui.Button(label="Open Telegram", style=discord.ButtonStyle.link,
                                    url=f"https://www.nationstates.net/page=compose_telegram?tgto={','.join(nations)}&message=%25{recruiter.template}%25"))

    return embed, view

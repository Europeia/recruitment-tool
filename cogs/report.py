import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord.ui import Modal

from components.bot import Bot
from models.db import Streak

logger = logging.getLogger("main")


class ReportModal(Modal, title="Recruitment Report"):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    r_type = discord.ui.Label(
        text="Report Type",
        component=discord.ui.RadioGroup(
            options=[
                discord.RadioGroupOption(label="Default", value="default", description="Telegram count with days active", default=True),
                discord.RadioGroupOption(label="Count Only", value="count_only", description="Telegram count only"),
                discord.RadioGroupOption(label="Streaks", value="streaks", description="Active recruitment streaks"),
            ],
            required=True,
        ),
    )

    start_time = discord.ui.Label(
        text="Start Time",
        component=discord.ui.TextInput(
            placeholder="YYYY-MM-DD HH:MM:SS", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), min_length=10, max_length=19
        ),
    )

    end_time = discord.ui.Label(
        text="End Time",
        component=discord.ui.TextInput(
            placeholder="YYYY-MM-DD HH:MM:SS", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"), min_length=10, max_length=19
        ),
    )

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.r_type.component, discord.ui.RadioGroup)
        assert isinstance(self.start_time.component, discord.ui.TextInput)
        assert isinstance(self.end_time.component, discord.ui.TextInput)

        start_time = datetime.fromisoformat(self.start_time.component.value).replace(tzinfo=timezone.utc)
        end_time = datetime.fromisoformat(self.end_time.component.value).replace(tzinfo=timezone.utc)
        report_type = self.r_type.component.value

        if report_type == "streaks":
            result = await self.bot.db.get_streaks(start_time, end_time, interaction.channel_id)

            if result:
                resp = "\n".join([f"{streak.nation}: {streak.streak} day{'s' if streak.streak != 1 else ''}" for streak in result])
            else:
                resp = "No active streaks"
            await interaction.response.send_message(
                f"Recruitment Streaks: <t:{int(start_time.timestamp())}:f> to <t:{int(end_time.timestamp())}:f>\n```{resp}```",
                ephemeral=True,
            )
            return

        result = await self.bot.get_telegrams(start_time, end_time, interaction.channel_id)

        if report_type == "count_only":
            resp = "\n".join([f"{nation}: {count}" for nation, count, _days in result])
        else:
            resp = "\n".join([f"{nation}: {count} ({days}d)" for nation, count, days in result])
        await interaction.response.send_message(
            f"Recruitment Report: <t:{int(start_time.timestamp())}:f> to <t:{int(end_time.timestamp())}:f>\n```{resp}```", ephemeral=True
        )

    async def on_error(self, interation: discord.Interaction, error: Exception):
        logger.error(error)
        await interation.response.send_message(f"An error occurred: {error}", ephemeral=True)


class ReportCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


async def setup(bot: Bot):
    await bot.add_cog(ReportCog(bot))

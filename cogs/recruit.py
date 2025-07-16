#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recruitment commands and UI for the asynchronous NationStates bot.

This module provides:
    * Modals for registering recruitment channels and recruiters.
    * A modal for generating recruitment reports.
    * The RecruitView UI for recruiting, registering, and reporting.
    * A TelegramView that times out recruit buttons.
    * The RecruitmentCog with slash commands and a background update loop.
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Modal, View, Button, Item

from components.bot import Bot
from components.errors import WhitelistError, NationNotFound
from components.queue import Nation


class RegisterRecruitmentChannelModal(Modal, title="Register Recruitment Channel"):
    """Modal to register the current channel for recruitment.

    Prompts the user for a region name, creates the RecruitView,
    and persists the channel and exception to the database.
    """

    def __init__(self, bot: Bot) -> None:
        """Initialize with a reference to the bot."""
        super().__init__(timeout=None)
        self.bot = bot

    region = discord.ui.TextInput(
        label="Region",
        min_length=1,
        max_length=40,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle the modal submission.

        Args:
            interaction (discord.Interaction): The interaction context.

        Raises:
            ValueError: If the region is empty.
            Exception: On database insertion error.
        """
        region_value = self.region.value.strip()
        if not region_value:
            raise ValueError("Region cannot be empty")

        region_key = region_value.lower().replace(" ", "_")
        message = await interaction.channel.send(view=RecruitView(self.bot))

        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        "INSERT INTO recruitment_channels (serverId, channelId, messageId) "
                        "VALUES (%s, %s, %s);",
                        (interaction.guild.id, interaction.channel.id, message.id),
                    )
                    await cur.execute(
                        "INSERT INTO exceptions (channelId, region) VALUES ("
                        "(SELECT id FROM recruitment_channels WHERE channelId = %s), %s);",
                        (interaction.channel.id, region_key),
                    )
                    self.bot.queue_list.add_channel(interaction.channel.id, [region_key])
                except Exception:
                    await message.delete()
                    raise
                else:
                    await interaction.response.send_message(
                        f"Registered channel for region: {region_key}", ephemeral=True
                    )

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Handle errors during modal interaction."""
        self.bot.std.error(error)
        await interaction.response.send_message(f"An error occurred:\n\n{error}", ephemeral=True)


class RegisterRecruiterModal(Modal, title="Register Recruiter"):
    """Modal to register or update a recruiter in the current channel."""

    def __init__(self, bot: Bot) -> None:
        """Initialize with a reference to the bot."""
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
        placeholder="Session length (45–600 seconds)",
        default="60",
        min_length=1,
        max_length=3,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle the modal submission.

        Args:
            interaction (discord.Interaction): The interaction context.

        Raises:
            ValueError: If session length is invalid.
            NationNotFound: If the nation cannot be found via the API.
        """
        nation_key = self.nation.value.strip().lower().replace(" ", "_")
        template = self.recruitment_template.value.replace("%", "")

        try:
            session_len = int(self.session_length.value)
        except ValueError:
            raise ValueError("Session length must be a number")

        if session_len < 45 or session_len > 600:
            raise ValueError("Session length must be between 45 and 600 seconds")

        api_resp = await self.bot.request(
            f"https://www.nationstates.net/cgi-bin/api.cgi?nation={nation_key}&q=foundedtime"
        )
        try:
            ts = int(api_resp.find("FOUNDEDTIME").text)
            founded_time = datetime.fromtimestamp(ts, timezone.utc)
        except Exception:
            raise NationNotFound(interaction.user, nation_key)

        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                recruiter_id = await self.bot.get_recruiter_id(
                    interaction.user, interaction.channel_id
                )
                if recruiter_id:
                    await cur.execute(
                        "UPDATE users SET nation=%s, recruitTemplate=%s, sessionLength=%s, "
                        "foundedTime=%s WHERE id=%s;",
                        (nation_key, template, session_len, founded_time, recruiter_id),
                    )
                else:
                    await cur.execute(
                        "INSERT INTO users (discordId, nation, recruitTemplate, sessionLength, "
                        "foundedTime, channelId) VALUES (%s, %s, %s, %s, %s, "
                        "(SELECT id FROM recruitment_channels WHERE channelId=%s));",
                        (
                            interaction.user.id,
                            nation_key,
                            template,
                            session_len,
                            founded_time,
                            interaction.channel_id,
                        ),
                    )

        await interaction.response.send_message(
            "Registration complete!", ephemeral=True, delete_after=10
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Handle errors during modal interaction."""
        self.bot.std.error(error)
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


class ReportModal(Modal, title="Recruitment Report"):
    """Modal to generate a recruitment report over a time interval."""

    def __init__(self, bot: Bot) -> None:
        """Initialize with a reference to the bot."""
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

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle the modal submission and send the report."""
        start = datetime.fromisoformat(self.start_time.value).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(self.end_time.value).replace(tzinfo=timezone.utc)
        results = await self.bot.get_telegrams(start, end, interaction.channel_id)
        lines = [f"{nation}: {count}" for nation, count in results]
        report = "\n".join(lines)
        await interaction.response.send_message(
            f"Recruitment Report: <t:{int(start.timestamp())}:f> to <t:{int(end.timestamp())}:f>\n"
            f"```{report}```",
            ephemeral=True,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Handle errors during modal interaction."""
        self.bot.std.error(error)
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


class RecruitView(View):
    """View with buttons for recruitment flow: recruit, register, report."""

    def __init__(self, bot: Bot) -> None:
        """Initialize with a reference to the bot."""
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Recruit",
        style=discord.ButtonStyle.blurple,
        custom_id="recruitment_view:recruit",
    )
    async def recruit(self, interaction: discord.Interaction, button: Button) -> None:
        """Handle the recruit button: send embed, start cooldown, update status."""
        embed, view, cooldown = await self.bot.create_recruitment_response(
            interaction.user, interaction.channel_id
        )
        message = await interaction.response.send_message(
            embed=embed, view=view, ephemeral=True, delete_after=3 + cooldown
        )
        view.message = message
        await self.bot.update_status_embeds(interaction.channel_id)

    @discord.ui.button(
        label="Register",
        style=discord.ButtonStyle.blurple,
        custom_id="recruitment_view:register",
    )
    async def register(self, interaction: discord.Interaction, button: Button) -> None:
        """Handle the register button: open the recruiter registration modal."""
        await interaction.response.send_modal(RegisterRecruiterModal(self.bot))

    @discord.ui.button(
        label="Report",
        style=discord.ButtonStyle.blurple,
        custom_id="recruitment_view:report",
    )
    async def report(self, interaction: discord.Interaction, button: Button) -> None:
        """Handle the report button: open the recruitment report modal."""
        await interaction.response.send_modal(ReportModal(self.bot))

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: Item) -> None:
        """Handle errors that occur within this view."""
        self.bot.std.error(error)
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


class TelegramView(View):
    """View for a single 'Open Telegram' button with an auto-timeout."""

    def __init__(self, cooldown: int) -> None:
        """Initialize the view with a timeout based on recruitment cooldown.

        Args:
            cooldown (int): Cooldown in seconds before the view times out.
        """
        super().__init__(timeout=3 + cooldown)
        self.message: Optional[discord.Message] = None

    async def on_timeout(self) -> None:
        """Remove the view from the message when the timeout expires."""
        if self.message:
            await self.message.edit(view=None)
        self.stop()


class RecruitmentCog(commands.Cog):
    """Cog containing slash commands and background update loop for recruitment."""

    def __init__(self, bot: Bot) -> None:
        """Initialize with a reference to the bot and regex pattern."""
        self.bot = bot
        self.pattern = re.compile(r"^\d+|\d+$")

    @app_commands.command(name="register", description="Register a channel for recruitment")
    @commands.has_permissions(administrator=True)
    async def register_recruitment_channel(self, interaction: discord.Interaction) -> None:
        """Slash command to register the current channel for recruitment.

        Validates that the guild is whitelisted before opening the registration modal.

        Args:
            interaction (discord.Interaction): The interaction context.

        Raises:
            WhitelistError: If the server is not whitelisted.
        """
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id FROM whitelist WHERE serverId=%s;", (interaction.guild.id,)
                )
                if not await cur.fetchone():
                    raise WhitelistError(interaction.user, interaction.guild)

        await interaction.response.send_modal(RegisterRecruitmentChannelModal(self.bot))

    @app_commands.command(
        name="whitelist", description="Modify this channel's recruitment whitelist"
    )
    @commands.has_permissions(administrator=True)
    @app_commands.choices(
        action=[
            app_commands.Choice(name="add", value="add"),
            app_commands.Choice(name="remove", value="remove"),
            app_commands.Choice(name="list", value="list"),
        ]
    )
    async def whitelist(
        self, interaction: discord.Interaction, action: str, region: Optional[str] = None
    ) -> None:
        """Slash command to add, remove, or list whitelisted regions for this channel.

        Args:
            interaction (discord.Interaction): The interaction context.
            action (str): One of "add", "remove", or "list".
            region (Optional[str]): Region to add or remove (required for add/remove).

        Raises:
            ValueError: If region is empty when required.
        """
        if action == "add":
            if not region:
                raise ValueError("Region cannot be empty")
            region_key = region.strip().lower().replace(" ", "_")
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        INSERT INTO exceptions (channelId, region)
                        VALUES (
                          (SELECT id FROM recruitment_channels WHERE channelId=%s),
                          %s
                        );""",
                        (interaction.channel.id, region_key),
                    )
            self.bot.queue_list.channel(interaction.channel.id).add_to_whitelist(region_key)
            await interaction.response.send_message(
                f"Added region {region_key} to whitelist", ephemeral=True
            )
        elif action == "remove":
            if not region:
                raise ValueError("Region cannot be empty")
            region_key = region.strip().lower().replace(" ", "_")
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        DELETE FROM exceptions
                        WHERE region=%s
                          AND channelId=(
                            SELECT id FROM recruitment_channels WHERE channelId=%s
                          );""",
                        (region_key, interaction.channel.id),
                    )
            self.bot.queue_list.channel(interaction.channel.id).remove_from_whitelist(region_key)
            await interaction.response.send_message(
                f"Removed region {region_key} from whitelist", ephemeral=True
            )
        else:  # list
            whitelist = self.bot.queue_list.channel(interaction.channel.id).whitelist
            regions = "\n".join(whitelist) or "No regions whitelisted"
            await interaction.response.send_message(
                f"Whitelisted regions:\n{regions}", ephemeral=True
            )

    @tasks.loop(seconds=15)
    async def update_loop(self) -> None:
        """Background task to fetch new nations and update queues periodically."""
        try:
            await self.update_queue()
        except Exception as e:
            self.bot.std.error(f"Error in update_loop: {e}")

    async def update_queue(self) -> None:
        """Fetch new nations from the API and update all queues and embeds."""
        self.bot.std.info("Updating queue")
        feed = await self.bot.request(
            "https://www.nationstates.net/cgi-bin/api.cgi?q=newnationdetails"
        )
        new_nations: list[Nation] = []
        for raw in reversed(feed.find_all("NEWNATION")):
            name = raw.attrs["name"]
            if self.pattern.search(name):
                continue
            founded_ts = int(raw.FOUNDEDTIME.text)
            founded_time = datetime.fromtimestamp(founded_ts, timezone.utc)
            if founded_time.timestamp() <= self.bot.queue_list.last_update.timestamp():
                continue
            new_nations.append(
                Nation(name=name, region=raw.REGION.text, founding_time=founded_time)
            )
        self.bot.queue_list.update(new_nations)
        await self.bot.update_status_embeds()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Start the update loop when the bot is ready."""
        if not self.update_loop.is_running():
            self.bot.std.info("Starting update loop")
            self.update_loop.start()

    @commands.Cog.listener()
    async def on_cog_load(self) -> None:
        """Ensure the update loop is running when the cog is loaded."""
        if not self.update_loop.is_running():
            self.bot.std.info("Starting update loop")
            self.update_loop.start()

    @commands.Cog.listener()
    async def on_cog_unload(self) -> None:
        """Stop the update loop when the cog is unloaded."""
        if self.update_loop.is_running():
            self.bot.std.info("Stopping update loop")
            self.update_loop.stop()


async def setup(bot: Bot) -> None:
    """Add the RecruitmentCog to the bot.

    Args:
        bot (Bot): The bot instance.
    """
    await bot.add_cog(RecruitmentCog(bot))

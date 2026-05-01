import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Modal, View

from components.bot import Bot
from components.checks import is_global_admin, is_global_admin_text
from components.errors import NationNotFound, WhitelistError

logger = logging.getLogger("main")


class RegisterRecruitmentChannelModal(Modal, title="Register Recruitment Channel"):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    region = discord.ui.Label(
        text="Region", component=discord.ui.TextInput(placeholder="Enter your region name", min_length=1, max_length=40)
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.is_finished() and self.region.value == "":
            raise ValueError("Region cannot be empty")

        assert isinstance(self.region.component, discord.ui.TextInput)

        region = self.region.component.value.strip().lower().replace(" ", "_")

        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id, disabled FROM recruitment_channels WHERE channelId = %s;", (interaction.channel.id,))
                existing = await cur.fetchone()

                if existing and not existing[1]:
                    if interaction.channel.id not in self.bot.queue_manager._queues:
                        await cur.execute(
                            """SELECT region
                               FROM exceptions
                                        JOIN recruitment_channels ON recruitment_channels.id = exceptions.channelId
                               WHERE recruitment_channels.channelId = %s;""",
                            (interaction.channel.id,),
                        )
                        regions = [r[0] for r in await cur.fetchall()]
                        self.bot.queue_manager.add_channel(interaction.channel.id, regions)
                        await interaction.response.send_message(
                            f"Channel was already registered but not loaded. Reloaded with regions: {', '.join(regions)}", ephemeral=True
                        )
                    else:
                        await interaction.response.send_message(
                            "This channel is already registered as a recruitment channel.", ephemeral=True
                        )
                    return

                message = await interaction.channel.send(view=RecruitView(self.bot))

                try:
                    if existing:
                        await cur.execute(
                            """UPDATE recruitment_channels
                               SET disabled  = FALSE,
                                   serverId  = %s,
                                   messageId = %s
                               WHERE channelId = %s;""",
                            (interaction.guild.id, message.id, interaction.channel.id),
                        )
                        await cur.execute(
                            """INSERT IGNORE INTO exceptions (channelId, region)
                               VALUES ((SELECT id FROM recruitment_channels WHERE channelId = %s), %s);""",
                            (interaction.channel.id, region),
                        )
                        await cur.execute(
                            """SELECT region
                               FROM exceptions
                                   JOIN recruitment_channels ON recruitment_channels.id = exceptions.channelId
                               WHERE recruitment_channels.channelId = %s;""",
                            (interaction.channel.id,),
                        )
                        regions = [r[0] for r in await cur.fetchall()]
                        self.bot.queue_manager.add_channel(interaction.channel.id, regions)
                        await interaction.response.send_message(f"Re-enabled channel for region: {region}.", ephemeral=True)
                    else:
                        await cur.execute(
                            "INSERT INTO recruitment_channels (serverId, channelId, messageId) VALUES (%s, %s, %s);",
                            (interaction.guild.id, interaction.channel.id, message.id),
                        )
                        await cur.execute(
                            "INSERT INTO exceptions (channelId, region) VALUES ("
                            "(SELECT id FROM recruitment_channels WHERE channelId = %s), %s);",
                            (interaction.channel.id, region),
                        )
                        self.bot.queue_manager.add_channel(interaction.channel.id, [region])
                        await interaction.response.send_message(f"Registered channel for region: {region}", ephemeral=True)

                except Exception as e:
                    await message.delete()
                    raise e

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        logger.exception(error)
        await interaction.response.send_message(f"An error occurred:\n\n{error}", ephemeral=True)


class RegisterRecruiterModal(Modal, title="Registration"):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    nation = discord.ui.Label(
        text="Nation", component=discord.ui.TextInput(placeholder="Enter your nation name", min_length=3, max_length=40)
    )

    recruitment_template = discord.ui.Label(
        text="Recruitment Template",
        component=discord.ui.TextInput(placeholder="Enter your recruitment template", min_length=10, max_length=20),
    )

    session_length = discord.ui.Label(
        text="Session Length (in seconds)",
        component=discord.ui.TextInput(placeholder="Session length (45 - 600 seconds)", default="60", min_length=1, max_length=3),
    )

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.nation.component, discord.ui.TextInput)
        assert isinstance(self.recruitment_template.component, discord.ui.TextInput)
        assert isinstance(self.session_length.component, discord.ui.TextInput)

        nation = self.nation.component.value.strip().lower().replace(" ", "_")
        template = self.recruitment_template.component.value.replace("%", "")

        try:
            session_length = int(self.session_length.component.value)
        except ValueError:
            raise Exception("Session length must be a number")
        else:
            if session_length < 45 or session_length > 600:
                raise Exception("Session length must be between 45 and 600 seconds")

        try:
            founded_time = datetime.fromtimestamp(
                int(
                    (await self.bot.request(f"https://www.nationstates.net/cgi-bin/api.cgi?nation={nation}&q=foundedtime"))
                    .find("FOUNDEDTIME")
                    .text
                )
            )
        except AttributeError:
            raise NationNotFound(interaction.user, nation)

        recruiter_id = await self.bot.get_recruiter_id(interaction.user, interaction.channel_id)

        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                if recruiter_id:
                    await cur.execute(
                        "UPDATE users SET nation = %s, recruitTemplate = %s, sessionLength = %s, foundedTime = %s WHERE id = %s;",
                        (nation, template, session_length, founded_time, recruiter_id),
                    )
                else:
                    await cur.execute(
                        "INSERT INTO users (discordId, nation, recruitTemplate, sessionLength, foundedTime, "
                        "channelId) VALUES (%s, %s, %s, %s, %s, (SELECT id FROM recruitment_channels WHERE "
                        "channelId = %s));",
                        (interaction.user.id, nation, template, session_length, founded_time, interaction.channel_id),
                    )

                # await conn.commit()
                await interaction.response.send_message("Registration complete!", ephemeral=True, delete_after=10)

    async def on_error(self, interation: discord.Interaction, error: Exception):
        logger.error(error)
        await interation.response.send_message(f"An error occurred: {error}", ephemeral=True)


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
            result = await self.bot.get_streaks(start_time, end_time, interaction.channel_id)

            if result:
                resp = "\n".join([f"{nation}: {days} day{'s' if days != 1 else ''}" for nation, days in result])
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


class RecruitView(View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Recruit", style=discord.ButtonStyle.blurple, custom_id="recruitment_view:recruit")
    async def recruit(self, interaction: discord.Interaction, _button: discord.ui.button):
        embed, view, delete_after = await self.bot.create_recruitment_response(interaction.user, interaction.channel_id)
        view.message = await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=3 + delete_after)
        await self.bot.update_status_embed(interaction.channel_id)

    @discord.ui.button(label="Register", style=discord.ButtonStyle.blurple, custom_id="recruitment_view:register")
    async def register(self, interaction: discord.Interaction, _button: discord.ui.button):
        await interaction.response.send_modal(RegisterRecruiterModal(self.bot))

    @discord.ui.button(label="Report", style=discord.ButtonStyle.blurple, custom_id="recruitment_view:report")
    async def report(self, interaction: discord.Interaction, _button: discord.ui.button):
        await interaction.response.send_modal(ReportModal(self.bot))

    async def on_error(self, interaction: discord.Interaction, error: Exception, _item: discord.ui.Item):
        logger.error(error)
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


class TelegramView(View):
    message: discord.Message

    def __init__(self, cooldown: int | float):
        super().__init__(timeout=3 + cooldown)

    async def on_timeout(self):
        self.stop()


class RecruitmentCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def cog_load(self):
        self.refresh_embeds.start()

    async def cog_unload(self):
        self.refresh_embeds.stop()

    @tasks.loop(seconds=15)
    async def refresh_embeds(self):
        try:
            await self.bot.update_status_embeds()
        except Exception:
            logger.exception("error in embed refresh task")

    @app_commands.command(name="register", description="Register a channel for recruitment")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def register_recruitment_channel(self, interaction: discord.Interaction):
        guild = interaction.guild

        if not guild:
            raise app_commands.AppCommandError("command must be run in a server")

        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id FROM whitelist WHERE serverId = %s;", (interaction.guild.id,))

                if not await cur.fetchone():
                    raise WhitelistError(interaction.user, guild)

        await interaction.response.send_modal(RegisterRecruitmentChannelModal(self.bot))

    whitelist_command_group = app_commands.Group(
        name="whitelist", description="commands for managing this channel's recruitment ignore list", guild_only=True
    )

    @whitelist_command_group.command(name="add", description="add a region to this channel's ignore list")
    @app_commands.checks.has_permissions(administrator=True)
    async def add(self, interaction: discord.Interaction, region: str):
        if not interaction.channel_id:
            raise app_commands.AppCommandError("command must be run in a channel")

        await self.bot.queue_manager.add_to_channel_whitelist(interaction.channel_id, region)

        await interaction.response.send_message(f"region: {region} added to whitelist", ephemeral=True)

    @whitelist_command_group.command(name="remove", description="remove a region from this channel's ignore list")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction, region: str):
        if not interaction.channel_id:
            raise app_commands.AppCommandError("command must be run in a channel")

        await self.bot.queue_manager.remove_from_channel_whitelist(interaction.channel_id, region)

        await interaction.response.send_message(f"region: {region} removed from whitelist", ephemeral=True)

    @whitelist_command_group.command(name="view", description="view this channel's ignore list")
    @app_commands.checks.has_permissions(administrator=True)
    async def view(self, interaction: discord.Interaction):
        if not interaction.channel_id:
            raise app_commands.AppCommandError("command must be run in a channel")

        global_whitelist, local_whitelist = map("\n".join, self.bot.queue_manager.list_whitelist(interaction.channel_id))

        await interaction.response.send_message(
            f"""**Global**\n```{global_whitelist}```\n**Local**\n```{local_whitelist}```""", ephemeral=True
        )

    admin_command_group = app_commands.Group(name="admin", description="global bot administrator commands")

    @admin_command_group.command(name="ignore", description="add a region to the global ignore list")
    @app_commands.check(is_global_admin)
    async def ignore(self, interaction: discord.Interaction, region: str):
        await self.bot.queue_manager.add_to_global_whitelist(region)

        await interaction.response.send_message("all set!", ephemeral=True)

    @admin_command_group.command(name="unignore", description="remove a region from the global ignore list")
    @app_commands.check(is_global_admin)
    async def unignore(self, interaction: discord.Interaction, region: str):
        await self.bot.queue_manager.remove_from_global_whitelist(region)

        await interaction.response.send_message("all set!", ephemeral=True)

    filter_command_group = app_commands.Group(name="filter", description="commands for managing global puppet filters")

    @filter_command_group.command(name="add", description="add a global name filter")
    @app_commands.check(is_global_admin)
    async def add_filter(self, interaction: discord.Interaction, pattern: str):
        pattern = pattern.lower()

        await self.bot.queue_manager.add_global_filter(pattern)

        await interaction.response.send_message(f"Added global filter: ``{pattern}``.", ephemeral=True)

    @filter_command_group.command(name="remove", description="remove a global name filter")
    @app_commands.check(is_global_admin)
    async def remove_filter(self, interaction: discord.Interaction, pattern: str):
        pattern = pattern.lower()

        await self.bot.queue_manager.remove_global_filter(pattern)

        await interaction.response.send_message(f"Removed global filter: ``{pattern}``.", ephemeral=True)

    @filter_command_group.command(name="test", description="list global filters that match a nation name")
    @app_commands.check(is_global_admin)
    async def test_filter(self, interaction: discord.Interaction, nation: str):
        nation = nation.strip().lower().replace(" ", "_")

        matches = self.bot.queue_manager.matching_filters(nation)

        if not matches:
            await interaction.response.send_message(f"No global filters match ``{nation}``.", ephemeral=True)
            return

        formatted = "\n".join(f"- ``{p}``" for p in matches)
        await interaction.response.send_message(f"Filters matching ``{nation}``:\n{formatted}", ephemeral=True)

    @commands.command(name="disable", description="Disable a recruitment channel by ID")
    @commands.check(is_global_admin_text)
    async def disable(self, ctx: commands.Context, channel_id: int):
        message_id = await self.bot.deregister_recruitment_channel(channel_id)

        if message_id is None:
            await ctx.reply(f"Channel {channel_id} is not a registered recruitment channel.")
            return

        # Removes channel from memory; bot.deregister call drops from DB
        self.bot.queue_manager.remove_channel(channel_id)

        channel = await self.bot.resolve_channel(channel_id)
        if channel is not None:
            try:
                message = await channel.fetch_message(message_id)
                await message.delete()
            except discord.NotFound:
                pass
            except discord.HTTPException as e:
                await ctx.reply(f"Deregistered channel {channel_id}, but failed to delete the status embed: {e}")
                return

        await ctx.reply(f"Deregistered channel {channel_id}.")


async def setup(bot: Bot):
    await bot.add_cog(RecruitmentCog(bot))

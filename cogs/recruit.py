import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Modal, View

from cogs.report import ReportModal
from components.bot import Bot
from components.checks import is_global_admin, is_global_admin_text
from components.errors import ActiveSessionError, NationNotFound, WhitelistError, EmptyQueue, NotRegistered
from components.session import Session

logger = logging.getLogger("main")


class RegisterRecruitmentChannelModal(Modal, title="Register Recruitment Channel"):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    region = discord.ui.Label(
        text="Region", component=discord.ui.TextInput(placeholder="Enter your region name", min_length=1, max_length=40)
    )

    def _validate_channel(self, interaction: discord.Interaction) -> discord.TextChannel | discord.Thread | None:
        channel = interaction.channel

        if not channel:
            logger.warning("_reactivate_recruitment_channel channel is None")
            return None

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            logger.warning("_reactivate_recruitment_channel run in something other than a text channel or thread (id: %d)", channel.id)
            return None

        return channel

    async def _retrieve_recruitment_message(self, channel_id: int) -> discord.Message | None:
        channel = await self.bot.resolve_channel(channel_id)

        if not channel:
            logger.warning("_retrieve_recruitment_message: could not resolve channel with id %d", channel_id)
            return None

        message_id = await self.bot.db.get_recruitment_message_id(channel_id)

        if not message_id:
            logger.warning("_retrieve_recruitment_message: could not get message id from database for channel with id %d", channel_id)
            return None

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound, discord.Forbidden, discord.HTTPException:
            logger.warning("_retrieve_recruitment_message: could not retrieve recrutiment message with id: %d", message_id)
            return None

        return message

    async def _reactivate_recruitment_channel(self, channel: discord.TextChannel | discord.Thread) -> str:
        # check if channel is registered but not loaded
        if not self.bot.queue_manager.has_channel(channel.id):
            channel_whitelist = await self.bot.db.get_channel_whitelist(channel.id)

            self.bot.queue_manager.add_channel(channel.id, channel_whitelist)

        # try to use old recruitment message
        message = await self._retrieve_recruitment_message(channel.id)

        if not message:
            message = await channel.send(view=RecruitView(self.bot))

        await self.bot.db.update_recruitment_message_id(channel.id, message.id)

        await self.bot.db.enable_recruitment_channel(channel.id)

        return "Reregistered channel"

    async def _register_recruitment_channel(self, channel: discord.TextChannel | discord.Thread, region: str) -> str:
        recruitment_message = await channel.send(view=RecruitView(self.bot))

        try:
            await self.bot.db.register_recruitment_channel(channel.guild.id, channel.id, recruitment_message.id)
            await self.bot.db.add_to_channel_whitelist(channel.id, region)

            self.bot.queue_manager.add_channel(channel.id, [region])
        except Exception as e:
            await recruitment_message.delete()
            raise e

        return f"Registered channel for region: {region}"

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.region.component, discord.ui.TextInput)

        if self.is_finished() and self.region.component.value == "":
            raise ValueError("Region cannot be empty")

        channel = self._validate_channel(interaction)
        if not channel:
            raise ValueError("command must be run in a text channel or thread")

        region = self.region.component.value.strip().lower().replace(" ", "_")

        is_registered = await self.bot.db.is_registered_recruitment_channel(channel.id)

        if not is_registered:
            message = await self._register_recruitment_channel(channel, region)
        else:
            message = await self._reactivate_recruitment_channel(channel)

        await interaction.response.send_message(message, ephemeral=True)

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
            founded_time = datetime.fromtimestamp(int((await self.bot.ns.get(nation=nation, q="foundedtime")).find("FOUNDEDTIME").text))
        except AttributeError:
            raise NationNotFound(interaction.user, nation)

        if interaction.channel_id is None:
            raise ValueError("interaction.channel_id can't be none")

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


class StartSessionModal(Modal, title="Start"):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self._bot = bot

    batch_size = discord.ui.Label(
        text="Batch Size",
        description="The minimum number of nations in a batch.",
        component=discord.ui.Select(
            options=[
                discord.SelectOption(label="1", value="1"),
                discord.SelectOption(label="2", value="2"),
                discord.SelectOption(label="3", value="3"),
                discord.SelectOption(label="4", value="4"),
                discord.SelectOption(label="5", value="5"),
                discord.SelectOption(label="6", value="6"),
                discord.SelectOption(label="7", value="7"),
                discord.SelectOption(label="8", value="8"),
            ]
        ),
    )

    cooldown = discord.ui.Label(
        text="Cooldown",
        description="The minimum time (excluding recruitment cooldown) between session pings.",
        component=discord.ui.Select(
            options=[
                discord.SelectOption(label="No cooldown", value="0"),
                discord.SelectOption(label="One Minute", value="60"),
                discord.SelectOption(label="Two Minutes", value="120"),
                discord.SelectOption(label="Three Minutes", value="180"),
                discord.SelectOption(label="Four Minutes", value="240"),
                discord.SelectOption(label="Five Minutes", value="360"),
            ]
        ),
    )

    shutdown_after = discord.ui.Label(
        text="Shutdown After",
        description="How long an inactive session should continue.",
        component=discord.ui.Select(
            options=[
                discord.SelectOption(label="10 Minutes", value="10"),
                discord.SelectOption(label="20 Minutes", value="20"),
                discord.SelectOption(label="30 Minutes", value="30"),
                discord.SelectOption(label="40 Minutes", value="40"),
                discord.SelectOption(label="50 Minutes", value="50"),
                discord.SelectOption(label="60 Minutes", value="60"),
            ]
        ),
    )

    async def on_submit(self, interaction: discord.Interaction):
        assert isinstance(self.batch_size.component, discord.ui.Select)
        assert isinstance(self.cooldown.component, discord.ui.Select)
        assert isinstance(self.shutdown_after.component, discord.ui.Select)

        batch_size = int(self.batch_size.component.values[0])
        cooldown = int(self.cooldown.component.values[0])
        shutdown_after = int(self.shutdown_after.component.values[0])

        if interaction.channel_id is None:
            raise ValueError("interaction.channel_id can't be none")

        recruiter = await self._bot.get_recruiter(interaction.user, interaction.channel_id)

        session = self._bot.session_manager.get_session_by_id(interaction.user.id)

        if session and session.channel_id == interaction.channel_id:
            new_session = Session(recruiter, batch_size, cooldown, shutdown_after)

            self._bot.session_manager.remove_session(interaction.user.id)
            self._bot.session_manager.add_session(new_session)

            await interaction.response.send_message("Session updated!", ephemeral=True)
        elif session and session.channel_id != interaction.channel_id:
            await interaction.response.send_message("Session active in another recruitment channel!", ephemeral=True)

        if not session:
            session = Session(recruiter, batch_size, cooldown, shutdown_after)

            self._bot.session_manager.add_session(session)

            await interaction.response.send_message("Session started!", ephemeral=True)

    async def on_error(self, interation: discord.Interaction, error: Exception):
        logger.error(error)
        await interation.response.send_message(f"An error occurred: {error}", ephemeral=True)


class ModifyOrEndSessionView(View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self._bot = bot
        self._message = None

    @discord.ui.button(label="Modify Session", style=discord.ButtonStyle.blurple)
    async def modify(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_modal(StartSessionModal(self._bot))

    @discord.ui.button(label="End Session", style=discord.ButtonStyle.danger)
    async def end(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self._disable_buttons()
        self._bot.session_manager.remove_session(interaction.user.id)
        await interaction.response.send_message("session ended!", ephemeral=True)

    @property
    def message(self) -> discord.InteractionMessage | None:
        return self._message

    @message.setter
    def message(self, message: discord.InteractionMessage):
        self._message = message

    async def _disable_buttons(self):
        self.modify.disabled = True
        self.end.disabled = True

        if self._message:
            await self._message.edit(view=self)


class RecruitView(View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Recruit", style=discord.ButtonStyle.blurple, custom_id="recruitment_view:recruit")
    async def recruit(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.bot.session_manager.get_session_by_id(interaction.user.id):
            raise ActiveSessionError(interaction.user)

        if interaction.channel_id is None:
            raise ValueError("interaction.channel_id can't be none")

        embed, view, delete_after = await self.bot.create_recruitment_response(interaction.user, interaction.channel_id)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=3 + delete_after)

        await self.bot.update_status_embed(interaction.channel_id)

    @discord.ui.button(label="Session", style=discord.ButtonStyle.blurple, custom_id="recruitment_view:session")
    async def session(self, interaction: discord.Interaction, _button: discord.ui.Button):
        if self.bot.session_manager.get_session_by_id(interaction.user.id):
            view = ModifyOrEndSessionView(self.bot)

            message = (
                await interaction.response.send_message("Would you like to modify or end your current session?", view=view, ephemeral=True)
            ).resource

            if not isinstance(message, discord.InteractionMessage):
                logger.warning("session modify or end: unexpectedly returned a discord.InteractionCallBackActivityInstance")
                return

            view.message = message

            return

        await interaction.response.send_modal(StartSessionModal(self.bot))

    @discord.ui.button(label="Register", style=discord.ButtonStyle.blurple, custom_id="recruitment_view:register")
    async def register(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_modal(RegisterRecruiterModal(self.bot))

    @discord.ui.button(label="Report", style=discord.ButtonStyle.blurple, custom_id="recruitment_view:report")
    async def report(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.send_modal(ReportModal(self.bot))

    async def on_error(self, interaction: discord.Interaction, error: Exception, _item: discord.ui.Item):
        if isinstance(error, EmptyQueue):
            await interaction.response.send_message("the queue is empty", ephemeral=True)
        elif isinstance(error, NotRegistered):
            await interaction.response.send_message("you must be registered to recruit", ephemeral=True)
        else:
            logger.error(error)
            await interaction.response.send_message("an unexpected error occurred, please contact a bot administrator", ephemeral=True)


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
                await cur.execute("SELECT id FROM whitelist WHERE serverId = %s;", (guild.id,))

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
        message_id = await self.bot.db.deactivate_recruitment_channel(channel_id)

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

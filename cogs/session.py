import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import discord
from discord import Interaction
from discord.ext import commands, tasks
from discord.ui import Item, View

from components.bot import Bot
from components.session import Session

logger = logging.getLogger("main")


class SessionRecruitView(View):
    def __init__(self, bot: Bot, user_id: int, recruitment_channel_id: int, timeout: int = 60):
        super().__init__(timeout=timeout)
        self._bot = bot
        self._user_id = user_id
        self._recruitment_channel_id = recruitment_channel_id
        self.message: discord.Message = None

    @discord.ui.button(label="Recruit", style=discord.ButtonStyle.blurple)
    async def recruit(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self._disable_buttons()
        embed, view, delete_after = await self._bot.create_recruitment_response(interaction.user, self._recruitment_channel_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=3 + delete_after)

    @discord.ui.button(label="End Session", style=discord.ButtonStyle.danger)
    async def end_session(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self._disable_buttons()
        self._bot.session_manager.remove_session(self._user_id)
        await interaction.response.send_message("session ended!", ephemeral=True)

    async def _disable_buttons(self):
        self.recruit.disabled = True
        self.end_session.disabled = True

        await self.message.edit(view=self)

    async def on_error(self, interaction: Interaction, error: Exception, _item: discord.ui.Item) -> None:
        logger.error("%s", error)
        await interaction.response.send_message(f"an error occurred: {error}", ephemeral=True)


class SessionKeepAliveView(View):
    def __init__(self, bot: Bot, user_id: int, timeout: int = 60) -> None:
        super().__init__(timeout=timeout)
        self._bot = bot
        self._user_id = user_id
        self.message: discord.Message = None

    @discord.ui.button(label="Keep Alive", style=discord.ButtonStyle.blurple)
    async def keep_alive(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self._disable_buttons()
        self._bot.session_manager.get_session_by_id(interaction.user.id).last_activity = datetime.now(timezone.utc)
        await interaction.response.send_message("activity confirmed, session continuing!", ephemeral=True)

    @discord.ui.button(label="End Session", style=discord.ButtonStyle.danger)
    async def end_session(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self._disable_buttons()
        self._bot.session_manager.remove_session(self._user_id)
        await interaction.response.send_message("session ended!", ephemeral=True)

    async def _disable_buttons(self):
        self.keep_alive.disabled = True
        self.end_session.disabled = True

        await self.message.edit(view=self)

    async def on_error(self, interaction: Interaction, error: Exception, _item: discord.ui.Item) -> None:
        logger.error("%s", error)
        await interaction.response.send_message(f"an error occurred: {error}", ephemeral=True)


class SessionCog(commands.Cog):
    def __init__(self, bot: Bot):
        self._bot = bot
        self._channels: list[int] = []
        """list of channels in which a session has been triggered during this loop; if multiple sessions are active in one channel, they don't all need to be pinged for the same nation at the same time"""
        self._users: dict[int, discord.User] = dict()

    @tasks.loop(seconds=15)
    async def _run(self):
        self._channels = []

        try:
            for session in self._bot.session_manager:
                logger.debug(f"Checking session {session.recruiter_id}")
                if session.channel_id in self._channels:
                    continue

                if self._session_out_of_time(session):
                    logger.debug("terminating session: %s due to inactivity", session.recruiter_id)

                    await self._try_confirm_session_end(session)

                    self._clear_session(session)

                    continue

                nation_count = self._bot.queue_manager.get_nation_count(session.channel_id)

                if nation_count >= session.min_batch_size and session.is_eligible():
                    logger.debug("session: %s is eligible", session.recruiter_id)
                    await self._try_send_session_message(session)
                    continue

                if session.is_eligible() and self._session_ending_soon(session):
                    logger.debug("session: %s is ending soon", session.recruiter_id)
                    await self._try_confirm_session_active(session)
        except:
            logger.exception("session error")

    async def cog_load(self):
        self._run.start()

    async def cog_unload(self):
        self._run.stop()

    async def _get_user(self, user_id: int) -> discord.User | None:
        if user_id in self._users:
            return self._users[user_id]

        user = await self._bot.resolve_user(user_id)

        if user:
            self._users[user_id] = user
            return user

        return None

    @staticmethod
    def _session_out_of_time(session: Session) -> bool:
        if (
            session.last_activity is None and session.started_at + timedelta(minutes=session.shutdown_after) < datetime.now(timezone.utc)
        ) or (
            session.last_activity is not None
            and session.last_activity + timedelta(minutes=session.shutdown_after) < datetime.now(timezone.utc)
        ):
            return True

        return False

    @staticmethod
    def _session_ending_soon(session: Session) -> bool:
        if (
            session.last_activity is None
            and session.started_at + timedelta(minutes=session.shutdown_after) < datetime.now(timezone.utc) + timedelta(minutes=5)
        ) or (
            session.last_activity is not None
            and session.last_activity + timedelta(minutes=session.shutdown_after) < datetime.now(timezone.utc) + timedelta(minutes=5)
        ):
            return True

        return False

    async def _try_send_session_message(self, session: Session):
        if session.recruiter_id not in self._users:
            user = await self._bot.resolve_user(session.recruiter_id)

            if not user:
                logger.warning("could not find user with id: %s", session.recruiter_id)
                return

            self._users[session.recruiter_id] = user

        try:
            embed = discord.Embed(title="Session")
            embed.add_field(name="Queue Length", value=f"{self._bot.queue_manager.get_nation_count(session.channel_id)}", inline=False)
            embed.set_footer(text=f"As of {datetime.now(timezone.utc).strftime('%H:%M:%S')}")

            view = SessionRecruitView(self._bot, session.recruiter_id, session.channel_id)

            view.message = await self._users[session.recruiter_id].send(embed=embed, view=view, delete_after=60)
            session.set_last_ping(datetime.now(timezone.utc))
            self._channels.append(session.channel_id)
        except discord.Forbidden:
            logger.error("unable to send messages to user: %s", session.recruiter_id)
            self._clear_session(session)
        except discord.NotFound:
            logger.error("user not found: %s", session.recruiter_id)
            self._clear_session(session)
        except discord.HTTPException:
            logger.exception("http error")

    async def _try_confirm_session_active(self, session: Session):
        user = await self._get_user(session.recruiter_id)

        if not user:
            logger.warning("could not find user with id: %s", session.recruiter_id)
            return

        try:
            view = SessionKeepAliveView(self._bot, session.recruiter_id, 60)

            view.message = await self._users[session.recruiter_id].send(view=view, delete_after=60)
            session.set_last_ping(datetime.now(timezone.utc))
        except discord.Forbidden:
            logger.error("unable to send messages to user: %s", session.recruiter_id)
            self._clear_session(session)
        except discord.NotFound:
            logger.error("user not found: %s", session.recruiter_id)
            self._clear_session(session)
        except discord.HTTPException:
            logger.exception("http error")

    async def _try_confirm_session_end(self, session: Session):
        user = await self._get_user(session.recruiter_id)

        if not user:
            logger.warning("could not find user with id: %s", session.recruiter_id)
            return

        try:
            await self._users[session.recruiter_id].send(content="session ended!", delete_after=60)
        except discord.Forbidden:
            logger.error("unable to send messages to user: %s", session.recruiter_id)
        except discord.NotFound:
            logger.error("user not found: %s", session.recruiter_id)
        except discord.HTTPException:
            logger.exception("http error")

    def _clear_session(self, session: Session):
        self._bot.session_manager.remove_session(session.recruiter_id)
        del self._users[session.recruiter_id]


async def setup(bot: Bot):
    await bot.add_cog(SessionCog(bot))

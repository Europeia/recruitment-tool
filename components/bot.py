import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import aiohttp
import aiomysql
import discord
from bs4 import BeautifulSoup as bs
from discord.ext import commands

from components.config.config_manager import configInstance
from components.database import Database
from components.errors import LastRecruitmentTooRecent, NotRegistered, TooManyRequests
from components.queue import QueueManager
from components.recruiter import Recruiter

logger = logging.getLogger("main")


class Bot(commands.Bot):
    @property
    def headers(self) -> dict:
        return self._headers

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def pool(self) -> aiomysql.Pool:
        return self._pool

    @property
    def db(self) -> Database:
        return self._db

    @property
    def ratelimit(self) -> Optional[int]:
        """The number of requests that NS will accept in within one bucket"""
        return self._ratelimit

    @property
    def policy(self) -> Optional[int]:
        """The length of an NS API bucket in seconds"""
        return self._policy

    @property
    def remaining(self) -> Optional[int]:
        """The number of requests remaining in the current NS API bucket"""
        return self._remaining

    @property
    def reset_in(self) -> Optional[int]:
        """The number of seconds until the current NS API bucket is reset"""
        return self._reset_in

    @property
    def request_timestamps(self) -> List[datetime]:
        """A list of timestamps for each request made in the current NS API bucket"""
        return self._request_timestamps

    @property
    def queue_manager(self) -> QueueManager:
        """The recruitment queue"""
        return self._queue_list

    def __init__(self, session: aiohttp.ClientSession, ql: QueueManager, pool: aiomysql.Pool):
        intents = discord.Intents.default()

        super().__init__(command_prefix="!", intents=intents)

        self._headers = {"User-Agent": f"Aperta Recruitment Bot, developed by nation=upc, run by {configInstance.data.operator}"}
        self._session = session
        self._pool = pool
        self._db = Database(pool)
        self._ratelimit = None
        self._policy = None
        self._remaining = None
        self._reset_in = None
        self._request_timestamps = []
        self._queue_list = ql

    async def setup_hook(self):
        import cogs.recruit

        recruitment_views = await self._db.fetch_all(
            "SELECT channelId, messageId FROM recruitment_channels WHERE disabled = FALSE;"
        )

        for _, message_id in recruitment_views:
            self.add_view(cogs.recruit.RecruitView(self), message_id=message_id)

        default_cogs = ["base", "recruit", "report", "error_handler"]

        for cog in default_cogs:
            await self.load_extension(f"cogs.{cog}")
            print(f"Loaded cog: {cog}")

    async def register_recruitment_channel(self, server_id: int, channel_id: int, message_id: int):
        try:
            await self._db.execute(
                "INSERT INTO recruitment_channels (serverId, channelId, messageId) VALUES (%s, %s, %s);",
                (server_id, channel_id, message_id),
            )
        except aiomysql.IntegrityError:
            # TODO make this into a custom exception!
            raise Exception("Channel already registered")

    async def deregister_recruitment_channel(self, channel_id: int) -> Optional[int]:
        """Disable a recruitment channel and return its status embed message id, or None if not actively registered."""
        row = await self._db.fetch_one(
            "SELECT messageId FROM recruitment_channels WHERE channelId = %s AND disabled = FALSE;",
            (channel_id,),
        )

        if row is None:
            return None

        await self._db.execute(
            "UPDATE recruitment_channels SET disabled = TRUE WHERE channelId = %s;",
            (channel_id,),
        )

        return row[0]

    async def request(self, url: str) -> bs:
        current_time = datetime.now(timezone.utc)

        if self._ratelimit:
            # Check if we are exceeding the user defined maximum number of requests in a bucket
            while len(self._request_timestamps) >= configInstance.data.period_max:
                elapsed = (current_time - self._request_timestamps[0]).total_seconds()

                if elapsed > self._policy:
                    del self._request_timestamps[0]
                else:
                    raise TooManyRequests(self._policy - elapsed)

            # Check if we are exceeding the NS defined maximum number of requests in a bucket
            if self._remaining and self._remaining <= 1:
                raise TooManyRequests(self.reset_in if self.reset_in else 30)

        async with self._session.get(url, headers=self._headers) as resp:
            self._ratelimit = int(resp.headers["RateLimit-limit"])
            self._policy = int(resp.headers["RateLimit-policy"].split(";w=")[1])
            self._remaining = int(resp.headers["RateLimit-remaining"])
            self._reset_in = int(resp.headers["RateLimit-reset"])
            self._request_timestamps.append(current_time)

            text = await resp.text()

            return bs(text, "xml")

    async def get_recruiter_id(self, user: discord.User, channel_id: int) -> Optional[int]:
        row = await self._db.fetch_one(
            """SELECT users.id
               FROM users
                        JOIN recruitment_channels ON recruitment_channels.id = users.channelId
               WHERE users.discordId = %s
                 AND recruitment_channels.channelId = %s
                 AND recruitment_channels.disabled = FALSE;""",
            (user.id, channel_id),
        )

        return row[0] if row else None

    async def get_recruiter(self, user: discord.User, channel_id: int):
        row = await self._db.fetch_one(
            """SELECT users.id, nation, recruitTemplate, allowRecruitmentAt, foundedTime
               FROM users
                        JOIN recruitment_channels ON recruitment_channels.id = users.channelId
               WHERE users.discordId = %s
                 AND recruitment_channels.channelId = %s
                 AND recruitment_channels.disabled = FALSE;
            """,
            (user.id, channel_id),
        )

        if row is None:
            raise NotRegistered(user)

        (dbid, nation, template, allow_recruitment_at, founded_time) = row

        return Recruiter(
            dbid,
            nation,
            template,
            user.id,
            channel_id,
            allow_recruitment_at.replace(tzinfo=timezone.utc),
            founded_time.replace(tzinfo=timezone.utc),
        )

    async def set_next_recruitment_at(self, recruiter: Recruiter, nation_count: int) -> int | float:
        cooldown = recruiter.get_cooldown(nation_count)

        next_recruitment_timestamp = datetime.now(timezone.utc) + timedelta(seconds=cooldown)

        await self._db.execute(
            """UPDATE users
               SET allowRecruitmentAt = %s
               WHERE id = %s;
            """,
            (next_recruitment_timestamp, recruiter.id),
        )

        return cooldown

    async def update_telegram_count(self, recruiter: Recruiter, nation_count: int):
        await self._db.execute(
            """INSERT INTO telegrams (recruiterId, nationCount, channelId)
               VALUES (%s, %s, (SELECT id
                                FROM recruitment_channels
                                WHERE channelId = %s));
            """,
            (recruiter.id, nation_count, recruiter.channel_id),
        )

    async def get_telegrams(self, start_time: datetime, end_time: datetime, channel_id: int):
        if start_time > end_time:
            raise Exception("Start time must be before end time")

        return await self._db.fetch_all(
            """SELECT users.nation,
                      SUM(nationCount) AS 'tgcount', COUNT(DISTINCT DATE (telegrams.timestamp)) AS 'days'
               FROM telegrams
                        JOIN users ON users.id = telegrams.recruiterId
                        JOIN recruitment_channels ON recruitment_channels.id = telegrams.channelId
               WHERE telegrams.timestamp BETWEEN %s AND %s
                 AND recruitment_channels.channelId = %s
               GROUP BY users.id
               ORDER BY tgcount DESC
               LIMIT 40;
            """,
            (start_time, end_time, channel_id),
        )

    async def get_streaks(self, start_time: datetime, end_time: datetime, channel_id: int):
        if start_time > end_time:
            raise Exception("Start time must be before end time")

        return await self._db.fetch_all(
            """WITH daily AS (SELECT telegrams.recruiterId, DATE (telegrams.timestamp) AS dt
               FROM telegrams
                   JOIN users
               ON users.id = telegrams.recruiterId
                   JOIN recruitment_channels ON recruitment_channels.id = telegrams.channelId
               WHERE recruitment_channels.channelId = %s
               GROUP BY telegrams.recruiterId, DATE (telegrams.timestamp)),
                   islands AS (
               SELECT recruiterId, dt, DATE_SUB(dt, INTERVAL
                   ROW_NUMBER() OVER (PARTITION BY recruiterId ORDER BY dt)
                   DAY) AS island
               FROM daily)
            SELECT users.nation, COUNT(*) AS streak_days
            FROM islands
                     JOIN users ON users.id = islands.recruiterId
            GROUP BY islands.recruiterId, islands.island
            HAVING streak_days >= 3
               AND MAX(dt) >= %s
               AND MIN(dt) <= %s
            ORDER BY streak_days DESC LIMIT 40;
            """,
            (channel_id, start_time, end_time),
        )

    async def create_recruitment_response(self, user: discord.User, channel_id: int):
        from cogs.recruit import TelegramView

        recruiter = await self.get_recruiter(user, channel_id)

        current_time = datetime.now(timezone.utc)

        if recruiter.next_recruitment_at > current_time:
            reset_in = (recruiter.next_recruitment_at - current_time).total_seconds()
            raise LastRecruitmentTooRecent(user, reset_in)

        nations = self._queue_list.get_nations(user, channel_id)

        cooldown = await self.set_next_recruitment_at(recruiter, len(nations))

        await self.update_telegram_count(recruiter, len(nations))

        embed = discord.Embed(title="Recruit", color=int("2d0001", 16))
        embed.add_field(name="Nations", value="\n".join([f"https://www.nationstates.net/nation={nation}" for nation in nations]))
        embed.add_field(name="Template", value=f"```{recruiter.template}```", inline=False)
        embed.set_footer(text=f"Initiated by {recruiter.nation} at {datetime.now(timezone.utc).strftime('%H:%M:%S')}")

        view = TelegramView(cooldown=cooldown)
        view.add_item(
            discord.ui.Button(
                label="Open Telegram",
                style=discord.ButtonStyle.link,
                url=f"https://nationstates.net/page=compose_telegram?tgto={','.join(nations)}&message=%25{recruiter.template}%25&generated_by=Asperta+Recruitment+Bot",
            )
        )

        return embed, view, cooldown

    async def resolve_channel(self, id: int) -> discord.TextChannel | discord.Thread | None:
        channel = self.get_channel(id)

        if channel:
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                logger.warning("unexpected type for channel %d: %s", id, type(channel))
                return None

            return channel

        try:
            channel = await self.fetch_channel(id)
        except Exception:
            logger.warning("unable to retrieve channel %d", id)
        else:
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                logger.warning("unexpected type for channel %d: %s", id, type(channel))
                return None

            return channel

        return None

    async def update_status_embed(self, channel_id: int):
        logger.info("updating status embed for channel %d", channel_id)

        embed = discord.Embed(title="Recruitment Queue")
        embed.add_field(name="Nations in Queue", value=self._queue_list.get_nation_count(channel_id))
        embed.add_field(name="Last Updated", value=f"<t:{int(self._queue_list.channel(channel_id).last_updated.timestamp())}:R>")

        row = await self._db.fetch_one(
            "SELECT messageId FROM recruitment_channels WHERE channelId = %s AND disabled = FALSE;",
            (channel_id,),
        )

        if row is None:
            logger.warning("no active recruitment channel row for channel %d", channel_id)
            return

        message_id = row[0]

        if type(message_id) is not int:
            logger.warning("invalid type for message_id: %d", type(message_id))
            return

        channel = await self.resolve_channel(channel_id)

        if not channel:
            logger.warning("unable to resolve channel %d", channel_id)
            return

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            logger.warning("message: %d not found, skipping", message_id)
            return
        except Exception as e:
            logger.warning("unspecified error while retrieving message %d: %s", message_id, e)
            return

        from cogs.recruit import RecruitView

        try:
            await message.edit(embed=embed, view=RecruitView(self))
        except discord.HTTPException as e:
            logger.warning("Failed to edit message %d in channel %d: %s", message_id, channel_id, e)

    async def update_status_embeds(self):
        channels = await self._db.fetch_all("SELECT channelId FROM recruitment_channels WHERE disabled = FALSE;")

        for channel in channels:
            if type(channel_id := channel[0]) is not int:
                logger.warning("Invalid type for channel_id: %s", type(channel_id))
                continue

            try:
                await self.update_status_embed(channel_id)
            except Exception as e:
                logger.error("Failed to update status embed for channel %d: %s", channel_id, e)

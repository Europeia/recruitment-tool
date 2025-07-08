from datetime import datetime, timedelta, timezone
from logging import Logger
from typing import List, Optional

import aiohttp
import aiomysql
import discord
from bs4 import BeautifulSoup as bs
from discord.ext import commands

from components.config.config_manager import configInstance
from components.errors import LastRecruitmentTooRecent, NotRegistered, TooManyRequests
from components.logger import standard_logger
from components.queue import QueueList
from components.recruiter import Recruiter


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
    def std(self) -> Logger:
        return self._std

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
        return self.request_timestamps

    @property
    def queue_list(self) -> QueueList:
        """The recruitment queue"""
        return self._queue_list

    def __init__(self, session: aiohttp.ClientSession, ql: QueueList, pool: aiomysql.Pool):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        self._headers = {"User-Agent": f"Aperta Recruitment Bot, developed by nation=upc, run by {configInstance.data.operator}"}
        self._session = session
        self._pool = pool
        self._std = standard_logger()
        self._ratelimit = None
        self._policy = None
        self._remaining = None
        self._reset_in = None
        self._request_timestamps = []
        self._queue_list = ql

    async def setup_hook(self):
        import cogs.recruit

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT channelId, messageId FROM recruitment_channels;")
                recruitment_views = await cur.fetchall()

                for channel_id, message_id in recruitment_views:
                    self.add_view(cogs.recruit.RecruitView(self), message_id=message_id)

        default_cogs = ["base", "recruit", "error_handler"]

        for cog in default_cogs:
            await self.load_extension(f"cogs.{cog}")
            print(f"Loaded cog: {cog}")

    async def register_recruitment_channel(self, server_id: int, channel_id: int, message_id: int):
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        "INSERT INTO recruitment_channels (serverId, channelId, messageId) VALUES (%s, %s, %s);",
                        (server_id, channel_id, message_id),
                    )
                except aiomysql.IntegrityError:
                    # TODO make this into a custom exception!!
                    raise Exception("Channel already registered")

            # await conn.commit()

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
            if self._remaining <= 1:
                raise TooManyRequests(self.reset_in)

        async with self._session.get(url, headers=self._headers) as resp:
            self._ratelimit = int(resp.headers["RateLimit-limit"])
            self._policy = int(resp.headers["RateLimit-policy"].split(";w=")[1])
            self._remaining = int(resp.headers["RateLimit-remaining"])
            self._reset_in = int(resp.headers["RateLimit-reset"])
            self._request_timestamps.append(current_time)

            text = await resp.text()

            return bs(text, "xml")

    async def get_recruiter_id(self, user: discord.User, channel_id: int) -> Optional[int]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                num = await cur.execute(
                    """SELECT id 
                    FROM users 
                    WHERE discordId = %s 
                    AND channelId = (
                        SELECT id FROM recruitment_channels WHERE channelId = %s
                    );""",
                    (user.id, channel_id),
                )

                if num == 0:
                    return None
                else:
                    return (await cur.fetchone())[0]

    async def get_recruiter(self, user: discord.User, channel_id: int):
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                num = await cur.execute(
                    """SELECT id, nation, recruitTemplate, allowRecruitmentAt, foundedTime
                    FROM users
                    WHERE discordId = %s
                    AND channelId = (
                        SELECT id FROM recruitment_channels WHERE channelId = %s
                    );
                    """,
                    (user.id, channel_id),
                )

                if num == 0:
                    raise NotRegistered(user)
                else:
                    (dbid, nation, template, allow_recruitment_at, founded_time) = await cur.fetchone()

                    return Recruiter(
                        dbid, nation, template, user.id, channel_id, allow_recruitment_at, founded_time.replace(tzinfo=timezone.utc)
                    )

    async def set_next_recruitment_at(self, recruiter: Recruiter, nation_count: int) -> int:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                cooldown = recruiter.get_cooldown(nation_count)

                next_recruitment_timestamp = datetime.now(timezone.utc) + timedelta(seconds=cooldown)

                await cur.execute(
                    """UPDATE users
                    SET allowRecruitmentAt = %s
                    WHERE id = %s;
                    """,
                    (next_recruitment_timestamp, recruiter.id),
                )
                return cooldown

    async def update_telegram_count(self, recruiter: Recruiter, nation_count: int):
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO telegrams (recruiterId, nationCount, channelId)
                    VALUES (%s, %s, (
                        SELECT id FROM recruitment_channels WHERE channelId = %s
                    ));
                    """,
                    (recruiter.id, nation_count, recruiter.channel_id),
                )

    async def get_telegrams(self, start_time: datetime, end_time: datetime, channel_id: int):
        if start_time > end_time:
            raise Exception("Start time must be before end time")

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT users.nation, SUM(nationCount) AS 'tgcount'
                    FROM telegrams
                    JOIN users on users.id = telegrams.recruiterId
                    WHERE telegrams.timestamp BETWEEN %s AND %s
                    AND telegrams.channelId = (
                        SELECT id FROM recruitment_channels WHERE channelId = %s
                    )
                    GROUP BY users.id 
                    ORDER BY tgcount DESC;
                    """,
                    (start_time, end_time, channel_id),
                )

                return await cur.fetchall()

    async def create_recruitment_response(self, user: discord.User, channel_id: int):
        from cogs.recruit import TelegramView

        recruiter = await self.get_recruiter(user, channel_id)

        current_time = datetime.utcnow()

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
                url=f"https://www.nationstates.net/page=compose_telegram?tgto={','.join(nations)}&message=%25{recruiter.template}%25&generated_by=Asperta+Recruitment+Bot",
            )
        )

        return embed, view, cooldown

    async def update_status_embeds(self, channel_id: int = None):
        """Update status embeds. If channel_id is provided, only update the embed for that channel"""

        self._std.info("Updating status embeds")

        if channel_id:
            embed = discord.Embed(title="Recruitment Queue")
            embed.add_field(name="Nations in Queue", value=self._queue_list.get_nation_count(channel_id))
            embed.add_field(name="Last Updated", value=f"<t:{int(self._queue_list.channel(channel_id).last_updated.timestamp())}:R>")

            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT messageId FROM recruitment_channels WHERE channelId = %s;", channel_id)

                    message_id = (await cur.fetchone())[0]

                    channel: discord.TextChannel = self.get_channel(channel_id)
                    message = await channel.fetch_message(message_id)

                    await message.edit(embed=embed)

        else:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT channelId, messageId FROM recruitment_channels;")
                    recruitment_views = await cur.fetchall()

                    for channel_id, message_id in recruitment_views:
                        embed = discord.Embed(title="Recruitment Queue")
                        embed.add_field(name="Nations in Queue", value=self._queue_list.get_nation_count(channel_id))
                        embed.add_field(
                            name="Last Updated", value=f"<t:{int(self._queue_list.channel(channel_id).last_updated.timestamp())}:R>"
                        )

                        try:
                            channel: discord.TextChannel = self.get_channel(channel_id)

                            message = await channel.fetch_message(message_id)

                            await message.edit(embed=embed)
                        except Exception as e:
                            self._std.error("Error updating channel id: " + str(channel_id))
                            self._std.error(f"Error in update_loop: {e}")

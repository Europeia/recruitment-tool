import aiohttp

import aiomysql
import discord

from bs4 import BeautifulSoup as bs
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from logging import Logger
from typing import List, Optional

from components.config.config_manager import configInstance
from components.errors import TooManyRequests, NotRegistered
from components.logger import standard_logger
from components.queue import Queue
from components.recruiter import Recruiter


# components.recruitment is imported in the bot's setup_hook
# it can't be imported here bc it would create a circular import

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
    def queue(self) -> Queue:
        """The recruitment queue"""
        return self._queue

    def __init__(self, session: aiohttp.ClientSession, pool: aiomysql.Pool):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix='!', intents=intents)

        self._headers = {
            'User-Agent': f'Asperta Recruitment Bot, run by {configInstance.data.operator}'
        }
        self._session = session
        self._pool = pool
        self._std = standard_logger()
        self._ratelimit = None
        self._policy = None
        self._remaining = None
        self._reset_in = None
        self._request_timestamps = []
        self._queue = Queue()

    async def setup_hook(self):
        import components.recruitment

        default_cogs = ['base', 'recruit', 'test', 'error_handler']

        for cog in default_cogs:
            await self.load_extension(f"cogs.{cog}")
            self.std.info(f'Loaded cog: {cog}')

        self.add_view(components.recruitment.RecruitView(self))

    async def get_recruiter(self, user: discord.User) -> Recruiter:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                num = await cur.execute('SELECT nation, recruitTemplate, allowRecruitmentAt FROM users WHERE discordId = %s;', (user.id,))

                # await conn.commit()

                if num == 0:
                    raise NotRegistered(user)
                else:
                    (nation, template, allow_recruitment_at) = await cur.fetchone()

                    return Recruiter(nation, template, user.id, allow_recruitment_at)

    async def get_recruiter_id(self, user: discord.User) -> Optional[int]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                num = await cur.execute('SELECT id FROM users WHERE discordId = %s;', (user.id,))

                # await conn.commit()

                if num == 0:
                    return None
                else:
                    return (await cur.fetchone())[0]

    async def set_next_recruitment_at(self, user: discord.User, nation_count: int):
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                next_recruitment_timestamp = datetime.now(timezone.utc) + timedelta(seconds=12 * nation_count)

                await cur.execute('UPDATE users SET allowRecruitmentAt = %s WHERE discordId = %s;', (next_recruitment_timestamp, user.id))

    async def update_telegram_count(self, user: discord.User, nation_count: int):
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    'INSERT INTO telegrams (recruiterId, nationCount) VALUES ((SELECT id FROM users WHERE discordId = %s), %s)',
                    (user.id, nation_count)
                )

    async def get_telegrams(self, start_time: datetime, end_time: datetime):
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    '''SELECT users.nation, SUM(nationCount) AS 'telegrams' \
                    FROM telegrams \
                    JOIN users on users.id = telegrams.recruiterId \
                    WHERE timestamp BETWEEN %s AND %s \
                    GROUP BY recruiterId \
                    ORDER BY telegrams DESC;
                    ''',
                    (start_time, end_time)
                )

                return await cur.fetchall()

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
            self._ratelimit = int(resp.headers['RateLimit-limit'])
            self._policy = int(resp.headers['RateLimit-policy'].split(';w=')[1])
            self._remaining = int(resp.headers['RateLimit-remaining'])
            self._reset_in = int(resp.headers['RateLimit-reset'])
            self._request_timestamps.append(current_time)

            text = await resp.text()

            return bs(text, 'xml')

    async def update_status(self):
        self.std.info("Updating status embed")

        channel: discord.TextChannel = self.get_channel(configInstance.data.recruit_channel_id)
        message = await channel.fetch_message(configInstance.data.status_message_id)

        embed = discord.Embed(title="Recruitment Queue")
        embed.add_field(name="Nations in Queue", value=self.queue.get_nation_count())
        embed.add_field(name="Last Updated", value=f"<t:{int(self.queue.last_updated.timestamp())}:R>")

        await message.edit(content=None, embed=embed)

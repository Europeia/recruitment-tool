#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""Discord bot for managing asynchronous NationStates recruitments.

This module defines the Bot class, which extends discord.ext.commands.Bot to
handle HTTP requests with rate limiting, MySQL interactions, dynamic loading
of UI views, and recruitment commands.
"""

from datetime import datetime, timezone, timedelta
from logging import Logger
from typing import List, Optional, Tuple

import aiohttp
import aiomysql
from bs4 import BeautifulSoup as bs
import discord
from discord.ext import commands

from components.config.config_manager import configInstance
from components.errors import LastRecruitmentTooRecent, NotRegistered, TooManyRequests
from components.logger import standard_logger
from components.queue import QueueList
from components.recruiter import Recruiter


class Bot(commands.Bot):
    """Discord bot for managing NationStates recruitments.

    Args:
        session (aiohttp.ClientSession): HTTP session for API requests.
        pool (aiomysql.Pool): MySQL connection pool.

    Attributes:
        headers (dict): HTTP headers for NationStates API requests.
        session (aiohttp.ClientSession): Shared HTTP session.
        pool (aiomysql.Pool): Database connection pool.
        std (Logger): Standard logger instance.
        ratelimit (Optional[int]): Max requests per NS API bucket.
        policy (Optional[int]): NS API bucket window in seconds.
        remaining (Optional[int]): Remaining requests in current bucket.
        reset_in (Optional[int]): Seconds until bucket reset.
        request_timestamps (List[datetime]): Timestamps of recent requests.
        queue_list (QueueList): Recruitment queue manager.
    """

    @property
    def headers(self) -> dict:
        """HTTP request headers for NationStates API."""
        return self._headers

    @property
    def session(self) -> aiohttp.ClientSession:
        """Shared aiohttp ClientSession."""
        return self._session

    @property
    def pool(self) -> aiomysql.Pool:
        """MySQL connection pool."""
        return self._pool

    @property
    def std(self) -> Logger:
        """Standard logger instance."""
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

    def __init__(self, session: aiohttp.ClientSession, pool: aiomysql.Pool) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)

        self._headers = {
            'User-Agent': (
                f'Aperta Recruitment Bot, developed by nation=upc, '
                f'run by {configInstance.data.operator}'
            )
        }
        self._session = session
        self._pool = pool
        self._std = standard_logger()
        self._ratelimit: Optional[int] = None
        self._policy: Optional[int] = None
        self._remaining: Optional[int] = None
        self._reset_in: Optional[int] = None
        self._request_timestamps: List[datetime] = []
        self._queue_list = QueueList(pool)

    async def setup_hook(self):
        """Initialize dynamic views and load default cogs."""
        import cogs.recruit  # noqa: F401

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT channelId, messageId FROM recruitment_channels;"
                )
                rows = await cur.fetchall()

                for channel_id, message_id in rows:
                    self.add_view(
                        cogs.recruit.RecruitView(self),
                        message_id=message_id,
                    )

        await self._queue_list.init()

        for cog in ['base', 'recruit', 'error_handler']:
            await self.load_extension(f'cogs.{str(cog)}')
            print(f'Loaded cog: {str(cog)}')

    async def register_recruitment_channel(
        self, server_id: int, channel_id: int, message_id: int
    ) -> None:
        """Register a channel and message for recruitment views.

        Args:
            server_id (int): Discord guild ID.
            channel_id (int): Discord channel ID.
            message_id (int): Discord message ID.

        Raises:
            ValueError: If the channel is already registered.
        """
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        "INSERT INTO recruitment_channels "
                        "(serverId, channelId, messageId) VALUES (%s, %s, %s);",
                        (server_id, channel_id, message_id),
                    )
                except aiomysql.IntegrityError:
                    raise ValueError("Channel already registered")

    async def request(self, url: str) -> bs:
        """Perform a rate-limited GET request and parse XML response.

        Args:
            url (str): URL to request.

        Returns:
            bs: Parsed XML as a BeautifulSoup object.

        Raises:
            TooManyRequests: If API rate limits are exceeded.
        """
        now = datetime.now(timezone.utc)
        if self._ratelimit:
            while len(self._request_timestamps) >= configInstance.data.period_max:
                elapsed = (now - self._request_timestamps[0]).total_seconds()
                if elapsed > (self._policy or 0):
                    del self._request_timestamps[0]
                else:
                    raise TooManyRequests((self._policy or 0) - elapsed)

            if self._remaining is not None and self._remaining <= 1:
                raise TooManyRequests(self.reset_in)

        async with self._session.get(url, headers=self._headers) as resp:
            self._ratelimit = int(resp.headers.get('RateLimit-limit', 0))
            policy = resp.headers.get('RateLimit-policy', '')
            self._policy = (
                int(policy.split(';w=')[1]) if ';w=' in policy else None
            )
            self._remaining = int(resp.headers.get('RateLimit-remaining', 0))
            self._reset_in = int(resp.headers.get('RateLimit-reset', 0))
            self._request_timestamps.append(now)
            text = await resp.text()
            return bs(text, 'xml')

    async def get_recruiter_id(
        self, user: discord.User, channel_id: int
    ) -> Optional[int]:
        """Retrieve recruiter database ID for a user in a channel.

        Args:
            user (discord.User): Discord user.
            channel_id (int): Recruitment channel ID.

        Returns:
            Optional[int]: Recruiter ID if registered, otherwise None.
        """
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                count = await cur.execute(
                    """
                    SELECT id FROM users
                    WHERE discordId = %s
                      AND channelId = (
                          SELECT id FROM recruitment_channels
                          WHERE channelId = %s
                      );
                    """,
                    (user.id, channel_id),
                )
                if count == 0:
                    return None
                row = await cur.fetchone()
                return row[0] if row else None

    async def get_recruiter(
        self, user: discord.User, channel_id: int
    ) -> Recruiter:
        """Fetch a Recruiter instance for a registered user.

        Args:
            user (discord.User): Discord user.
            channel_id (int): Recruitment channel ID.

        Returns:
            Recruiter: Recruiter model.

        Raises:
            NotRegistered: If the user is not registered.
        """
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                count = await cur.execute(
                    """
                    SELECT id, nation, recruitTemplate, allowRecruitmentAt,
                           foundedTime
                    FROM users
                    WHERE discordId = %s
                      AND channelId = (
                          SELECT id FROM recruitment_channels
                          WHERE channelId = %s
                      );
                    """,
                    (user.id, channel_id),
                )
                if count == 0:
                    raise NotRegistered(user)
                dbid, nation, template, allow_at, founded = await cur.fetchone()
                return Recruiter(
                    dbid,
                    nation,
                    template,
                    user.id,
                    channel_id,
                    allow_at,
                    founded.replace(tzinfo=timezone.utc),
                )

    async def set_next_recruitment_at(
        self, recruiter: Recruiter, nation_count: int
    ) -> int:
        """Calculate and update the next recruitment timestamp in the database.

        Args:
            recruiter (Recruiter): Recruiter instance.
            nation_count (int): Number of nations recruited.

        Returns:
            int: Cooldown in seconds until next recruitment.
        """
        cooldown = recruiter.get_cooldown(nation_count)
        next_ts = datetime.now(timezone.utc) + timedelta(seconds=cooldown)
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE users
                    SET allowRecruitmentAt = %s
                    WHERE id = %s;
                    """,
                    (next_ts, recruiter.id),
                )
        return cooldown

    async def update_telegram_count(
        self, recruiter: Recruiter, nation_count: int
    ) -> None:
        """Record a recruitment action in the telegrams table.

        Args:
            recruiter (Recruiter): Recruiter instance.
            nation_count (int): Number of nations recruited.
        """
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO telegrams (recruiterId, nationCount, channelId)
                    VALUES (%s, %s, (
                        SELECT id FROM recruitment_channels
                        WHERE channelId = %s
                    ));
                    """,
                    (recruiter.id, nation_count, recruiter.channel_id),
                )

    async def get_telegrams(
        self, start_time: datetime, end_time: datetime, channel_id: int
    ) -> List[Tuple[str, int]]:
        """Aggregate telegram counts per nation in a time range.

        Args:
            start_time (datetime): Start of interval.
            end_time (datetime): End of interval.
            channel_id (int): Recruitment channel ID.

        Returns:
            List[Tuple[str, int]]: (nation, telegram_count) tuples sorted descending.

        Raises:
            ValueError: If start_time is after end_time.
        """
        if start_time > end_time:
            raise ValueError("Start time must be before end time")

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT users.nation, SUM(nationCount) AS tgcount
                    FROM telegrams
                    JOIN users ON users.id = telegrams.recruiterId
                    WHERE telegrams.timestamp BETWEEN %s AND %s
                      AND telegrams.channelId = (
                          SELECT id FROM recruitment_channels
                          WHERE channelId = %s
                      )
                    GROUP BY users.id
                    ORDER BY tgcount DESC;
                    """,
                    (start_time, end_time, channel_id),
                )
                return await cur.fetchall()

    async def create_recruitment_response(
        self, user: discord.User, channel_id: int
    ) -> Tuple[discord.Embed, discord.ui.View, int]:
        """Generate embed, view, and cooldown for a recruitment action.

        Args:
            user (discord.User): Discord user initiating recruitment.
            channel_id (int): Recruitment channel ID.

        Returns:
            Tuple[discord.Embed, discord.ui.View, int]:
                - Embed: Recruitment details.
                - View: UI view with Telegram button.
                - int: Cooldown until next recruitment.

        Raises:
            LastRecruitmentTooRecent: If recruiting too soon.
        """
        from cogs.recruit import TelegramView  # noqa: F811

        recruiter = await self.get_recruiter(user, channel_id)
        now = datetime.now(timezone.utc)
        if recruiter.next_recruitment_at > now:
            reset_in = (recruiter.next_recruitment_at - now).total_seconds()
            raise LastRecruitmentTooRecent(user, reset_in)

        nations = self._queue_list.get_nations(user, channel_id)
        cooldown = await self.set_next_recruitment_at(recruiter, len(nations))
        await self.update_telegram_count(recruiter, len(nations))

        embed = discord.Embed(title="Recruit", color=int("2d0001", 16))
        embed.add_field(
            name="Nations",
            value="\n".join(f"https://www.nationstates.net/nation={n}" for n in nations),
        )
        embed.add_field(name="Template", value=f"```{recruiter.template}```", inline=False)
        embed.set_footer(
            text=f"Initiated by {recruiter.nation} at {now.strftime('%H:%M:%S')}"
        )

        view = TelegramView(cooldown=cooldown)
        view.add_item(
            discord.ui.Button(
                label="Open Telegram",
                style=discord.ButtonStyle.link,
                url=(
                    f"https://www.nationstates.net/page=compose_telegram?"
                    f"tgto={','.join(nations)}&message=%25"
                    f"{recruiter.template}%25&generated_by=Asperta+Recruitment+Bot"
                ),
            )
        )
        return embed, view, cooldown

    async def update_status_embeds(self, channel_id: int = None):
        """Update status embeds. If channel_id is provided, only update the embed for that channel.
        
        Args:
            channel_id (Optional[int]): Specific channel to update; updates all if None.
        """
        self._std.info("Updating status embeds")
        if channel_id is not None:
            embed = discord.Embed(title="Recruitment Queue")
            embed.add_field(
                name="Nations in Queue",
                value=self._queue_list.get_nation_count(channel_id),
            )
            embed.add_field(
                name="Last Updated",
                value=f"<t:{int(self._queue_list.channel(channel_id).last_updated.timestamp())}:R>",
            )
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT messageId FROM recruitment_channels WHERE channelId = %s;",
                        (channel_id,),
                    )
                    message_id = (await cur.fetchone())[0]
                    channel = self.get_channel(channel_id)
                    message = await channel.fetch_message(message_id)
                    await message.edit(embed=embed)
        else:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT channelId, messageId FROM recruitment_channels;")
                    rows = await cur.fetchall()

            for cid, mid in rows:
                embed = discord.Embed(title="Recruitment Queue")
                embed.add_field(
                    name="Nations in Queue",
                    value=self._queue_list.get_nation_count(cid),
                )
                embed.add_field(
                    name="Last Updated",
                    value=f"<t:{int(self._queue_list.channel(cid).last_updated.timestamp())}:R>",
                )
                try:
                    channel = self.get_channel(cid)
                    message = await channel.fetch_message(mid)
                    await message.edit(embed=embed)
                except Exception as e:
                    self._std.error(f"Error updating channel id: {str(cid)}")
                    self._std.error(f"Error in update_loop: {str(e)}")

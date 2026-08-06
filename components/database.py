from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple

import aiomysql

from components.recruiter import Recruiter
from models.db import RecruitmentStats, Streak


class Database:
    def __init__(self, pool: aiomysql.Pool):
        self._pool = pool

    async def _execute(self, sql: str, args: Optional[Sequence[Any]] = None) -> int:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                return await cur.execute(sql, args)

    async def execute(self, sql: str, args: Optional[Sequence[Any]] = None) -> int:
        return await self._execute(sql, args)

    async def _fetch_one(self, sql: str, args: Optional[Sequence[Any]] = None) -> Optional[Tuple]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                return await cur.fetchone()

    async def fetch_one(self, sql: str, args: Optional[Sequence[Any]] = None) -> Optional[Tuple]:
        return await self._fetch_one(sql, args)

    async def _fetch_all(self, sql: str, args: Optional[Sequence[Any]] = None) -> List[Tuple]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                return await cur.fetchall()

    async def fetch_all(self, sql: str, args: Optional[Sequence[Any]] = None) -> List[Tuple]:
        return await self._fetch_all(sql, args)

    async def get_streaks(self, start_time: datetime, end_time: datetime, channel_id: int) -> List[Streak]:
        if start_time > end_time:
            raise Exception("start time must be before end time")

        result = await self._fetch_all(
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

        response = [Streak(nation, days) for (nation, days) in result]

        response.sort(key=lambda x: x.streak, reverse=True)

        return response

    async def get_telegrams(self, start_time: datetime, end_time: datetime, channel_id: int) -> List[RecruitmentStats]:
        if start_time > end_time:
            raise Exception("start time must be before end time")

        result = await self._fetch_all(
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

        response = [RecruitmentStats(nation, count, days) for (nation, count, days) in result]

        response.sort(key=lambda x: x.count, reverse=True)

        return response

    async def get_recruiter(self, user_id: int, channel_id: int) -> Recruiter | None:
        row = await self._fetch_one(
            """SELECT users.id, nation, recruitTemplate, lastRecruitmentAt, foundedTime
               FROM users
                        JOIN recruitment_channels ON recruitment_channels.id = users.channelId
               WHERE users.discordId = %s
                 AND recruitment_channels.channelId = %s
                 AND recruitment_channels.disabled = FALSE;
            """,
            (user_id, channel_id),
        )

        if not row:
            return None

        return Recruiter(
            dbid=row[0],
            nation=row[1],
            template=row[2],
            discord_id=user_id,
            channel_id=channel_id,
            last_recruitment_at=row[3].replace(tzinfo=timezone.utc) if row[3] else None,
            founded_time=row[4].replace(tzinfo=timezone.utc),
        )

    async def record_recruitment(self, time: datetime, recruiter: Recruiter, nation_count: int) -> None:
        await self._execute(
            """UPDATE users
               SET lastRecruitmentAt = %s
               WHERE id = %s;
            """,
            (time, recruiter.id),
        )

        await self._update_telegram_count(recruiter, nation_count)

    async def _update_telegram_count(self, recruiter: Recruiter, nation_count: int):
        await self._execute(
            """INSERT INTO telegrams (recruiterId, nationCount, channelId)
               VALUES (%s, %s, (SELECT id
                                FROM recruitment_channels
                                WHERE channelId = %s));
            """,
            (recruiter.id, nation_count, recruiter.channel_id),
        )

    async def get_channel_whitelist(self, channel_id: int) -> List[str]:
        result = await self._fetch_all(
            """SELECT region
                    FROM exceptions
                        JOIN recruitment_channels ON recruitment_channels.id = exceptions.channelId
                   WHERE recruitment_channels.channelId = %s;""",
            (channel_id,),
        )

        return [row[0] for row in result]

    async def is_registered_recruitment_channel(self, channel_id: int) -> bool:
        result = await self._fetch_one("""SELECT disabled FROM recruitment_channels WHERE channelId = %s;""", (channel_id,))

        if not result:
            return False

        return result[0]

    async def get_recruitment_message_id(self, channel_id: int) -> Optional[int]:
        result = await self._fetch_one("""SELECT messageId FROM recruitment_channels WHERE channelId = %s;""", (channel_id,))

        if not result:
            return None

        return result[0]

    async def update_recruitment_message_id(self, channel_id: int, message_id: int):
        await self._execute(
            """UPDATE recruitment_channels rc
                   JOIN recruitment_channels rc2
                       ON rc.id = rc2.id
                       SET rc.messageId = %s
                   WHERE rc2.channelId = %s;""",
            (message_id, channel_id),
        )

    async def register_recruitment_channel(self, server_id: int, channel_id: int, message_id: int):
        try:
            await self._execute(
                """INSERT INTO recruitment_channels (serverId, channelId, messageId) VALUES (%s, %s, %s);""",
                (server_id, channel_id, message_id),
            )
        except aiomysql.IntegrityError:
            # TODO: make into a custom exception
            raise Exception("Channel already registered")

    async def enable_recruitment_channel(self, channel_id: int) -> Optional[int]:
        result = await self._fetch_one(
            """SELECT messageId FROM recruitment_channels WHERE channelId = %s AND disabled = TRUE;""", (channel_id,)
        )

        if not result:
            return None

        await self._execute("""UPDATE recruitment_channels SET disabled = FALSE WHERE channelId = %s;""", (channel_id,))

        return result[0]

    async def deactivate_recruitment_channel(self, channel_id: int) -> Optional[int]:
        """Disable a recruitment channel and return its status embed message id, or None if not actively registered."""

        result = await self._fetch_one(
            """SELECT messageId FROM recruitment_channels WHERE channelId = %s AND disabled = FALSE;""", (channel_id,)
        )

        if not result:
            return None

        await self._execute("""UPDATE recruitment_channels SET disabled = TRUE WHERE channelId = %s;""", (channel_id,))

        return result[0]

    async def add_to_channel_whitelist(self, channel_id: int, region: str):
        await self._execute(
            """INSERT INTO exceptions (channelId, region) VALUES ((SELECT id FROM recruitment_channels WHERE channelId = %s), %s);""",
            (channel_id, region),
        )

    async def remove_from_channel_whitelist(self, channel_id: int, region: str):
        await self._execute(
            """DELETE FROM exceptions WHERE channelId = (SELECT id FROM recruitment_channels WHERE channelId = %s) AND region = %s;""",
            (channel_id, region),
        )

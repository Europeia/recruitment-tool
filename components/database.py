from datetime import datetime, timedelta
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

    async def set_next_recruitment_at(self, recruiter: Recruiter, nation_count: int) -> int | float:
        cooldown = recruiter.get_cooldown(nation_count)

        next_recruitment_timestamp = datetime.now() + timedelta(seconds=cooldown)

        await self._execute(
            """UPDATE users
               SET allowRecruitmentAt = %s
               WHERE id = %s;
            """,
            (next_recruitment_timestamp, recruiter.id),
        )

        return cooldown

    async def update_telegram_count(self, recruiter: Recruiter, nation_count: int):
        await self._execute(
            """INSERT INTO telegrams (recruiterId, nationCount, channelId)
               VALUES (%s, %s, (SELECT id
                                FROM recruitment_channels
                                WHERE channelId = %s));
            """,
            (recruiter.id, nation_count, recruiter.channel_id),
        )

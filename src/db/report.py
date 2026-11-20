import aiomysql
from datetime import datetime
from typing import List

from models.db import RecruitmentStats, Streak
from .model import DatabaseConnection


class ReportRepository(DatabaseConnection):
    def __init__(self, pool: aiomysql.Pool):
        super().__init__(pool)

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

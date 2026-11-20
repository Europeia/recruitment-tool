import aiomysql
from datetime import datetime, timezone

from .model import DatabaseConnection
from components.recruiter import Recruiter


class RecruiterRepository(DatabaseConnection):
    def __init__(self, pool: aiomysql.Pool):
        super().__init__(pool)

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

    async def _update_telegram_count(self, recruiter: Recruiter, nation_count: int):
        await self._execute(
            """INSERT INTO telegrams (recruiterId, nationCount, channelId)
                   VALUES (%s, %s, (SELECT id
                                    FROM recruitment_channels
                                    WHERE channelId = %s));
                """,
            (recruiter.id, nation_count, recruiter.channel_id),
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

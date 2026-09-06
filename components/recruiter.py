from datetime import datetime, timedelta, timezone


class Recruiter:
    def __init__(
        self,
        dbid: int,
        nation: str,
        template: str,
        discord_id: int,
        channel_id: int,
        last_recruitment_at: datetime | None,
        founded_time: datetime,
    ):
        self._id = dbid
        self._nation = nation
        self._template = template
        self._discord_id = discord_id
        self._channel_id = channel_id
        self._last_recruitment_at = last_recruitment_at
        self._last_recruitment_count = 0
        self._founded_time = founded_time

    @property
    def id(self):
        return self._id

    @property
    def nation(self):
        return self._nation

    @property
    def template(self):
        return self._template

    @property
    def discord_id(self):
        return self._discord_id

    @property
    def channel_id(self):
        return self._channel_id

    def next_recruitment_at(self) -> datetime | None:
        if self._last_recruitment_at is None:
            return None

        return self._last_recruitment_at + timedelta(seconds=self.get_cooldown(self._last_recruitment_count))

    @property
    def last_recruitment_at(self):
        return self._last_recruitment_at

    def record_recruitment(self, dt: datetime, count: int) -> None:
        self._last_recruitment_at = dt
        self._last_recruitment_count = count

    @property
    def founded_time(self):
        return self._founded_time

    def get_cooldown(self, nation_count: int = 8):
        # cooldown per nation starts at approximately 14 seconds and decreases linearly until it is 5 seconds
        # when the nation is 18 months old
        seconds = (datetime.now(timezone.utc) - self.founded_time).days / 60

        if seconds > 9:
            return 5 * nation_count
        elif seconds < 0:
            return 14 * nation_count
        else:
            return 5 + (9 - seconds) * nation_count

from datetime import datetime, timedelta, timezone

from components.recruiter import Recruiter


class Session:
    def __init__(self, recruiter: Recruiter, min_batch_size: int, cooldown: int, shutdown_after: int):
        self._recruiter = recruiter
        self._min_batch_size = min_batch_size
        self._cooldown = cooldown
        self._shutdown_after = shutdown_after
        self._last_ping: datetime | None = None
        self._started_at: datetime = datetime.now(timezone.utc)
        self._last_activity: datetime | None = None

    def is_eligible(self) -> bool:
        """whether the nation is eligible for a session ping, based on their `next_recruitment_at` and `cooldown` values"""
        next_recruitment_at = self._recruiter.next_recruitment_at()
        current_time = datetime.now(timezone.utc)

        if not next_recruitment_at:
            # means this user has never recruited, we can short circuit and assume yes
            return True

        if self._last_ping:
            return current_time > next_recruitment_at and current_time > self._last_ping + timedelta(seconds=self._cooldown)
        else:
            return current_time > next_recruitment_at

    def set_last_ping(self, dt: datetime):
        self._last_ping = dt

    @property
    def recruiter_id(self) -> int:
        return self._recruiter.discord_id

    @property
    def channel_id(self) -> int:
        return self._recruiter.channel_id

    @property
    def recruiter(self) -> Recruiter:
        return self._recruiter

    @property
    def min_batch_size(self) -> int:
        return self._min_batch_size

    @property
    def last_ping(self) -> datetime | None:
        return self._last_ping

    @property
    def shutdown_after(self) -> int:
        return self._shutdown_after

    @property
    def started_at(self) -> datetime:
        return self._started_at

    @property
    def last_activity(self) -> datetime | None:
        return self._last_activity

    @last_activity.setter
    def last_activity(self, dt: datetime) -> None:
        self._last_activity = dt


class SessionManager:
    def __init__(self):
        self._sessions: list[Session] = []

    def __iter__(self):
        return iter(self._sessions)

    def get_session_by_id(self, discord_id: int) -> Session | None:
        for session in self._sessions:
            if session.recruiter_id == discord_id:
                return session

        return None

    def get_sessions_by_channel_id(self, channel_id: int) -> list[Session]:
        return [session for session in self._sessions if session.channel_id == channel_id]

    def add_session(self, session: Session) -> int | None:
        if session.recruiter_id not in self._sessions:
            self._sessions.append(session)

            return session.recruiter_id

        return None

    def remove_session(self, discord_id: int) -> Session | None:
        for session in self._sessions:
            if session.recruiter_id == discord_id:
                self._sessions.remove(session)

                return session

        return None

    def end_all(self):
        self._sessions.clear()

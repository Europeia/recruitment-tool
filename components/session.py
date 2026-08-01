from datetime import datetime, timedelta

from components.recruiter import Recruiter


class Session:
    def __init__(self, recruiter: Recruiter, min_batch_size: int, cooldown: int, shutdown_after: int):
        self._recruiter = recruiter
        self._min_batch_size = min_batch_size
        self._cooldown = cooldown
        self._shutdown_after = shutdown_after
        self._last_ping: datetime | None = None

    def is_eligible(self) -> bool:
        """whether the nation is eligible for a session ping, based on their `next_recruitment_at` and `cooldown` values"""
        if self._last_ping:
            return datetime.now() > self._recruiter.next_recruitment_at and datetime.now() > self._last_ping + timedelta(
                seconds=self._cooldown
            )
        else:
            return datetime.now() > self._recruiter.next_recruitment_at

    def set_last_ping(self, dt: datetime):
        self._last_ping = dt

    @property
    def recruiter_id(self) -> int:
        return self._recruiter.discord_id

    @property
    def channel_id(self) -> int:
        return self._recruiter.channel_id


class SessionManager:
    def __init__(self):
        self._sessions = []

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

from dataclasses import dataclass


@dataclass
class Streak:
    def __init__(self, nation: str, streak: int):
        self._nation = nation
        self._streak = streak

    @property
    def nation(self) -> str:
        return self._nation

    @property
    def streak(self) -> int:
        """Streak length in days"""
        return self._streak


@dataclass
class RecruitmentStats:
    def __init__(self, nation: str, count: int, days: int):
        self._nation = nation
        self._count = count
        self._days = days

    @property
    def nation(self) -> str:
        return self._nation

    @property
    def count(self) -> int:
        """Number of telegrams sent during the report period"""
        return self._count

    @property
    def days(self) -> int:
        """Number of active days sent during the report period"""
        return self._days

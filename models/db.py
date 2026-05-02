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

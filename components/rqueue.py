import discord

from bs4 import ResultSet
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List

from components.errors import EmptyQueue

# how long to keep nations in queue (in seconds)
PRUNE_TIME: int = 3600


@dataclass
class Nation:
    name: str
    time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Queue:
    queue_type: str
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    nations: list[Nation] = field(default_factory=list)

    def update(self, new_nations: List[str]):
        for nation_name in new_nations:
            self.nations.insert(0, Nation(nation_name))

        self.last_update = datetime.now(timezone.utc)

    def get_nation_count(self) -> int:
        return len(self.nations)

    def get_nations(self, user: discord.User, return_count: int = 8) -> List[str]:
        if self.queue_type != "welcome":
            self.prune()

        resp = [nation.name for nation in self.nations][:return_count]

        self.nations = self.nations[return_count:]

        if resp:
            return resp
        else:
            raise EmptyQueue(user=user)

    def prune(self):
        current_time = datetime.now(timezone.utc)

        self.nations = [nation for nation in self.nations if
                        ((current_time - nation.time).total_seconds() < PRUNE_TIME)]

    def purge(self):
        self.nations = []

import discord

from bs4 import BeautifulSoup as bs
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from components.errors import EmptyQueue


@dataclass
class Nation:
    name: str
    founding_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Queue:
    nations: list[Nation] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update(self, new_nations: List[str]):
        for nation_name in new_nations:
            self.nations.insert(0, Nation(nation_name))

        self.last_updated = datetime.now(timezone.utc)

    def get_nation_count(self) -> int:
        return len(self.nations)

    def get_nations(self, user: discord.User, return_count: int = 8) -> List[str]:
        self.prune()

        if self.get_nation_count() == 0:
            raise EmptyQueue(user)

        resp = [nation.name for nation in self.nations][:return_count]

        self.nations = self.nations[return_count:]

        return resp

    def get_nation_names(self) -> List[str]:
        return [nation.name for nation in self.nations]

    def prune(self):
        current_time = datetime.now(timezone.utc)

        self.nations = [nation for nation in self.nations if (current_time - nation.founding_time).total_seconds() < 3600]

    def purge(self):
        self.nations = []

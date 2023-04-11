from dataclasses import dataclass, field
from datetime import datetime, timezone

# how long to keep nations in queue (in seconds)
PRUNE_TIME: int = 3600


@dataclass
class Nation:
    name: str
    time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Queue:
    nations: list[Nation] = field(default_factory=list)

    def add(self, name: str):
        nation = Nation(name)

        self.nations.insert(0, nation)

    def get_nations(self):
        self.prune()

        resp = [nation.name for nation in self.nations[:8]]

        self.nations = [nation for nation in self.nations if nation.name not in resp]

        return resp

    def prune(self):
        current_time = datetime.now(timezone.utc)

        self.nations = [nation for nation in self.nations if (
                current_time - nation.time).total_seconds() < PRUNE_TIME]

    def purge(self):
        self.nations = []

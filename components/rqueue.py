from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

# how long to keep nations in queue (in seconds)
PRUNE_TIME: int = 3600


@dataclass
class Nation:
    name: str
    time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recruited: bool = False

    def calculate_age(self, now: int = datetime.now(timezone.utc)):
        return (now - self.time).total_seconds()


@dataclass
class Queue:
    nations: list[Nation] = field(default_factory=list)

    def update(self, new_nations: List[str]):
        for idx, nation in enumerate(self.nations):
            if nation.name in new_nations:
                new_nations.remove(nation.name)

                if nation.recruited:
                    self.nations[idx] = Nation(name=nation.name, recruited=True)

        for nation_name in reversed(new_nations):
            nation = Nation(nation_name)

            self.nations.insert(0, nation)

    def get_nations(self):
        self.prune()

        resp = [nation.name for nation in self.nations if not nation.recruited][:8]

        for nation in self.nations:
            if nation.name in resp:
                nation.recruited = True

        return resp

    def prune(self):
        now = datetime.now(timezone.utc)

        self.nations = [nation for nation in self.nations if (not nation.recruited and (
            nation.calculate_age(now) < PRUNE_TIME) or (nation.recruited and nation.calculate_age(now) < 30))]


    def purge(self):
        self.nations = []

    def unrecruit(self, batch: list[Nation]):
        # Mark the nations as unrecruited
        for nat in batch:
            nat.recruited = False
            # Unprune the nation if necessary
            if nat.calculate_age() > PRUNE_TIME:
                self.nations.append(nat)

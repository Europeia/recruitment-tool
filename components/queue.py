import aiomysql
import discord

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from components.errors import EmptyQueue


@dataclass
class Nation:
    name: str
    region: str
    founding_time: datetime


@dataclass
class Queue:
    whitelist: list[str]
    nations: list[Nation]
    last_updated: datetime

    def __init__(self, whitelist: list[str] = None):
        self.nations = []
        self.whitelist = whitelist if whitelist else []
        self.last_updated = datetime.now(timezone.utc)

    def __repr__(self):
        return f"<Queue nations={len(self.nations)} last_updated={self.last_updated}>"

    def update(self, new_nations: List[Nation]):
        for nation in new_nations:
            if nation.region not in self.whitelist:
                self.nations.insert(0, nation)

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

    def add_to_whitelist(self, region: str):
        self.whitelist.append(region)

    def remove_from_whitelist(self, region: str):
        self.whitelist.remove(region)


@dataclass
class QueueList:
    last_update: datetime
    pool: aiomysql.Pool
    queues: dict[int, Queue] = field(default_factory=dict)

    def __init__(self, pool: aiomysql.Pool):
        self.pool = pool
        self.queues = {}
        self.last_update = datetime.now(timezone.utc)

    def __repr__(self):
        return f"<QueueList queues={self.queues}>"

    async def init(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT channelId FROM recruitment_channels;")
                channels: List[int] = [channel[0] for channel in await cur.fetchall()]

                for channel in channels:
                    await cur.execute(
                        "SELECT region FROM exceptions WHERE channelId = (SELECT id FROM recruitment_channels WHERE channelId = %s);",
                        (channel,),
                    )

                    regions = [region[0] for region in await cur.fetchall()]

                    self.queues[channel] = Queue(whitelist=regions)

    def channel(self, channel_id: int) -> Queue:
        return self.queues[channel_id]

    def add_channel(self, channel_id: int, regions: List[str]):
        self.queues[channel_id] = Queue(whitelist=regions)

    def update(self, new_nations: List[Nation]):
        new_nations = [nation for nation in new_nations if nation.region != "europeia"]

        for queue in self.queues.values():
            queue.update(new_nations)
            queue.prune()

        if not new_nations:
            return

        self.last_update = new_nations[-1].founding_time

    def get_nations(self, user: discord.User, channel_id: int, return_count: int = 8) -> List[str]:
        return self.queues[channel_id].get_nations(user, return_count)

    def get_nation_count(self, channel_id: int) -> int:
        return self.queues[channel_id].get_nation_count()

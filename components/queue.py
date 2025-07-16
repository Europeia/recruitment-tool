import aiomysql
import asyncio
import discord
import json
import logging
import re
import requests
import sseclient
import threading

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Self

from components.errors import EmptyQueue


logger = logging.getLogger("main")

PUPPET_REGEX = re.compile(r"^\d+_[a-z0-9_]+|[a-z0-9_]+_\d+$|^[a-z0-9_]+_m{0,4}(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})$")
FOUNDING_REGEX = re.compile("^@@([a-z0-9_]+)@@ was founded in %%([a-z0-9_]+)%%.?$")
MOVE_REGEX = re.compile("^@@([a-z0-9_]+)@@ relocated from %%([a-z0-9_]+)%% to %%([a-z0-9_]+)%%.?$")


@dataclass
class Event:
    id: str
    htmlstr: str
    str: str
    timestamp: int

    @classmethod
    def from_json(cls, dct) -> Self:
        return cls(dct["id"], dct["htmlStr"], dct["str"], dct["time"])

    def __repr__(self):
        return f"<Event id={self.id} data={self.str}>"


@dataclass
class FoundingEvent:
    nation: str
    region: str
    timestamp: datetime


@dataclass
class MoveEvent:
    nation: str
    moved_from: str
    moved_to: str
    timestamp: datetime


@dataclass
class Nation:
    name: str
    region: str
    founding_time: datetime


class Queue:
    _whitelist: list[str]
    "list of regions that the region associated with this queue will not recruit from"
    _nations: List[Nation]

    def __init__(self, whitelist: List[str] = []):
        self._nations = []
        self._whitelist = whitelist

    def __repr__(self):
        return f"<Queue nations={len(self._nations)}>"

    def update(self, nation: Nation):
        if nation.region not in self._whitelist:
            self._nations.insert(0, nation)

    def get_nation_count(self) -> int:
        return len(self._nations)

    def get_nations(self, user: discord.User, return_count: int = 8) -> List[str]:
        self.prune()

        if self.get_nation_count() == 0:
            raise EmptyQueue(user)

        resp = [nation.name for nation in self._nations][:return_count]

        self._nations = self._nations[return_count:]

        return resp

    def get_nation_names(self) -> List[str]:
        return [nation.name for nation in self._nations]

    def prune(self):
        current_time = datetime.now(timezone.utc)

        self._nations = [nation for nation in self._nations if (current_time - nation.founding_time).total_seconds() < 3600]

    def purge(self):
        self._nations = []

    def add_to_whitelist(self, region: str):
        self._whitelist.append(region)

    def remove_from_whitelist(self, region: str):
        self._whitelist.remove(region)

    def handle_move(self, nation_name: str, destination: str):
        for idx, nation in enumerate(self._nations):
            if nation.name == nation_name:
                if destination in self._whitelist:
                    del self._nations[idx]
                return

    def handle_founding(self, nation: Nation):
        if nation.region not in self._whitelist:
            self._nations.insert(0, nation)

    @property
    def whitelist(self):
        return self._whitelist


class QueueManager:
    _whitelist: List[str]
    _pool: aiomysql.Pool
    _queues: dict[int, Queue] = field(default_factory=dict)
    _queue_lock: threading.Lock
    _update_thread: threading.Thread
    _running: bool

    def __init__(self, pool: aiomysql.Pool):
        self._whitelist = []
        self._pool = pool
        self._queues = {}
        self._queue_lock = threading.Lock()
        self._running = True

    def __repr__(self):
        return f"<QueueList queues={self._queues}>"

    async def __aenter__(self):
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT channelId FROM recruitment_channels;")
                channels: List[int] = [channel[0] for channel in await cur.fetchall()]

                for channel in channels:
                    await cur.execute(
                        "SELECT region FROM exceptions WHERE channelId = (SELECT id FROM recruitment_channels WHERE channelId = %s);",
                        (channel,),
                    )

                    regions = [region[0] for region in await cur.fetchall()]

                    self.add_channel(channel, regions)

        self._update_thread = threading.Thread(target=self._update, daemon=True)

        self._update_thread.start()

        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        self._running = False

    @property
    def global_whitelist(self):
        return self._whitelist

    def add_to_global_whitelist(self, region: str):
        if region not in self._whitelist:
            self._whitelist.append(region)

    def remove_from_global_whitelist(self, region: str):
        try:
            self._whitelist.remove(region)
        except ValueError:
            logger.warning("tried to remove nonexistent value: %s from global whitelist", region)

    async def add_to_channel_whitelist(self, channel_id: int, region: str):
        region = region.strip().lower().replace(" ", "_")

        if region in self._whitelist:
            return

        if region in self._queues[channel_id].whitelist:
            return

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO exceptions (channelId, region) VALUES (
                        (SELECT id FROM recruitment_channels WHERE channelId = %s), %s
                    );""",
                    (channel_id, region),
                )

        self._queues[channel_id].whitelist.append(region)

    async def remove_from_channel_whitelist(self, channel_id: int, region: str):
        region = region.strip().lower().replace(" ", "_")

        if region not in self._queues[channel_id].whitelist:
            return

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """DELETE FROM exceptions WHERE region = %s AND channelId = (
                        SELECT id FROM recruitment_channels WHERE channelId = %s
                    );""",
                    (region, channel_id),
                )

        self._queues[channel_id].whitelist.remove(region)

    def list_whitelist(self, channel_id: int):
        return (self._whitelist, self._queues[channel_id].whitelist)

    def channel(self, channel_id: int) -> Queue:
        with self._queue_lock:
            return self._queues[channel_id]

    def add_channel(self, channel_id: int, regions: List[str]):
        with self._queue_lock:
            self._queues[channel_id] = Queue(whitelist=regions)

    def get_nations(self, user: discord.User, channel_id: int, return_count: int = 8) -> List[str]:
        with self._queue_lock:
            return self._queues[channel_id].get_nations(user, return_count)

    def get_nation_count(self, channel_id: int) -> int:
        with self._queue_lock:
            return self._queues[channel_id].get_nation_count()

    def _handle_founding(self, event: FoundingEvent):
        if PUPPET_REGEX.match(event.nation):
            logger.debug("likely puppet founding found; skipping: %s", event.nation)
            return

        if event.region in self._whitelist:
            logger.debug("founding in whitelisted region; skipping %s", event.nation)
            return

        with self._queue_lock:
            for _, queue in self._queues.items():
                queue.handle_founding(Nation(event.nation, event.region, event.timestamp))

    def _handle_move(self, event: MoveEvent):
        if PUPPET_REGEX.match(event.nation):
            logger.debug("likely puppet move found; skipping: %s", event.nation)
            return

        if event.moved_to in self._whitelist:
            logger.debug("move to whitelisted region; skipping %s", event.nation)
            return

        with self._queue_lock:
            for _, queue in self._queues.items():
                queue.handle_move(event.nation, event.moved_to)

    def _handle_events(self):
        for event in sseclient.SSEClient(requests.get("https://www.nationstates.net/api/founding+move", stream=True)).events():  # type: ignore
            data: Event = json.loads(event.data, object_hook=Event.from_json)

            logger.debug("event: %s", data.str)

            if match := FOUNDING_REGEX.match(data.str):
                self._handle_founding(FoundingEvent(match[1], match[2], datetime.fromtimestamp(data.timestamp)))
            elif match := MOVE_REGEX.match(data.str):
                self._handle_move(MoveEvent(match[1], match[2], match[3], datetime.fromtimestamp(data.timestamp)))

            if not self._running:
                raise asyncio.CancelledError()

    def _update(self):
        logger.info("starting update thread")

        while self._running:
            try:
                self._handle_events()
            except asyncio.CancelledError:
                logger.info("terminating update thread")
                return
            except Exception:
                logger.exception("error in update loop")

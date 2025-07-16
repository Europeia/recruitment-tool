#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Queue management for the asynchronous recruitment bot.

This module defines:
  * Nation: a data class representing a nation entry.
  * Queue: a per-channel queue that applies a region whitelist and prunes old entries.
  * QueueList: manager for multiple Queue instances backed by a MySQL pool.

Example:
    qlist = QueueList(pool)
    await qlist.init()
    qlist.update(new_nations)
    names = qlist.get_nations(user, channel_id)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Dict

import aiomysql
import discord

from components.errors import EmptyQueue


@dataclass
class Nation:
    """Data for a nation entry.

    Attributes:
        name (str): Nation name.
        region (str): Nation's region.
        founding_time (datetime): UTC timestamp when the nation was founded.
    """
    name: str
    region: str
    founding_time: datetime


@dataclass
class Queue:
    """Per-channel queue of nations for recruitment.

    Maintains a list of incoming nations, applies a region whitelist,
    and prunes entries older than one hour.
    """
    whitelist: List[str] = field(default_factory=list)
    nations: List[Nation] = field(init=False)
    last_updated: datetime = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the queue state."""
        self.nations = []
        self.last_updated = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<Queue nations={len(self.nations)} last_updated={self.last_updated.isoformat()}>"

    def update(self, new_nations: List[Nation]) -> None:
        """Add new nations not in the whitelist and update timestamp.

        Args:
            new_nations (List[Nation]): New nation entries to enqueue.
        """
        for nation in new_nations:
            if nation.region not in self.whitelist:
                self.nations.insert(0, nation)
        self.last_updated = datetime.now(timezone.utc)

    def get_nation_count(self) -> int:
        """Return the number of nations in the queue."""
        return len(self.nations)

    def get_nations(self, user: discord.User, return_count: int = 8) -> List[str]:
        """Retrieve up to `return_count` nation names and dequeue them.

        Args:
            user (discord.User): The user requesting nations.
            return_count (int): Maximum number of names to return.

        Returns:
            List[str]: List of nation names.

        Raises:
            EmptyQueue: If there are no nations available.
        """
        self.prune()
        if not self.nations:
            raise EmptyQueue(user)

        names = [nation.name for nation in self.nations[:return_count]]
        self.nations = self.nations[return_count:]
        return names

    def get_nation_names(self) -> List[str]:
        """Return all queued nation names without dequeuing."""
        return [nation.name for nation in self.nations]

    def prune(self) -> None:
        """Remove nations older than one hour from the queue."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=3600)
        self.nations = [
            nation for nation in self.nations
            if nation.founding_time > cutoff
        ]

    def purge(self) -> None:
        """Clear all queued nations."""
        self.nations.clear()

    def add_to_whitelist(self, region: str) -> None:
        """Add a region to the whitelist."""
        if region not in self.whitelist:
            self.whitelist.append(region)

    def remove_from_whitelist(self, region: str) -> None:
        """Remove a region from the whitelist."""
        if region in self.whitelist:
            self.whitelist.remove(region)


@dataclass
class QueueList:
    """Manager for multiple per-channel Queue instances.

    Loads channel configurations from the database and distributes updates
    and pruning across all queues.
    """
    pool: aiomysql.Pool
    queues: Dict[int, Queue] = field(init=False)
    last_update: datetime = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the queue list state."""
        self.queues = {}
        self.last_update = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<QueueList queues={list(self.queues.keys())}>"

    async def init(self) -> None:
        """Load registered channels and their whitelists from the database.

        Populates `self.queues` with a Queue for each channel ID.
        """
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT channelId FROM recruitment_channels;")
                channel_ids = [row[0] for row in await cur.fetchall()]

                for cid in channel_ids:
                    await cur.execute(
                        """
                        SELECT region
                        FROM exceptions
                        WHERE channelId = (
                            SELECT id FROM recruitment_channels WHERE channelId = %s
                        );
                        """,
                        (cid,),
                    )
                    regions = [row[0] for row in await cur.fetchall()]
                    self.queues[cid] = Queue(whitelist=regions)

    def channel(self, channel_id: int) -> Queue:
        """Get the Queue for a specific channel.

        Args:
            channel_id (int): Discord channel ID.

        Returns:
            Queue: The queue instance for that channel.
        """
        return self.queues[channel_id]

    def add_channel(self, channel_id: int, regions: List[str]) -> None:
        """Create a new Queue for a channel with the given whitelist.

        Args:
            channel_id (int): Discord channel ID.
            regions (List[str]): Regions to whitelist.
        """
        self.queues[channel_id] = Queue(whitelist=regions)

    def update(self, new_nations: List[Nation]) -> None:
        """Distribute new nations to all queues, exclude 'europeia', and prune.

        Args:
            new_nations (List[Nation]): New nation entries to distribute.
        """
        filtered = [n for n in new_nations if n.region.lower() != "europeia"]
        for queue in self.queues.values():
            queue.update(filtered)
            queue.prune()
        if filtered:
            self.last_update = filtered[-1].founding_time

    def get_nations(
        self, user: discord.User, channel_id: int, return_count: int = 8
    ) -> List[str]:
        """Retrieve queued nation names for a user in a channel.

        Args:
            user (discord.User): The requesting user.
            channel_id (int): Discord channel ID.
            return_count (int, optional): Max names to return. Defaults to 8.

        Returns:
            List[str]: Nation names.
        """
        return self.queues[channel_id].get_nations(user, return_count)

    def get_nation_count(self, channel_id: int) -> int:
        """Get the number of nations in the queue for a channel.

        Args:
            channel_id (int): Discord channel ID.

        Returns:
            int: Number of queued nations.
        """
        return self.queues[channel_id].get_nation_count()

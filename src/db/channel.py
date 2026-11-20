import aiomysql
from typing import List, Optional, Tuple

from .model import DatabaseConnection


class RecruitmentChannelRepository(DatabaseConnection):
    def __init__(self, pool: aiomysql.Pool):
        super().__init__(pool)

    async def get_all_recruitment_channels(self) -> List[Tuple[int, int]]:
        result = await self._fetch_all("""SELECT serverId, channelId FROM recruitment_channels WHERE disabled = FALSE;""")

        return [(row[0], row[1]) for row in result]

    async def get_whitelist(self, channel_id: int) -> List[str]:
        result = await self._fetch_all(
            """SELECT region
                    FROM exceptions
                        JOIN recruitment_channels ON recruitment_channels.id = exceptions.channelId
                    WHERE recruitment_channels.channelId = %s;
                """,
            (channel_id,),
        )

        return [row[0] for row in result]

    async def is_registered(self, channel_id: int) -> bool:
        """check if a channel is registered for recruitment"""
        result = await self._fetch_one("""SELECT disabled FROM recruitment_channels WHERE channelId = %s;""", (channel_id,))

        if not result:
            return False

        return result[0]

    async def get_recruitment_message_id(self, channel_id: int) -> Optional[int]:
        result = await self._fetch_one("""SELECT messageId FROM recruitment_channels WHERE channelId = %s;""", (channel_id,))

        if not result:
            return None

        return result[0]

    async def update_recruitment_message_id(self, channel_id: int, message_id: int):
        await self._execute(
            """UPDATE recruitment_channels rc
                    JOIN recruitment_channels rc2
                        ON rc.id = rc2.id
                        SET rc.messageId = %s
                    WHERE rc2.channelId = %s;
                """,
            (message_id, channel_id),
        )

    async def register(self, server_id: int, channel_id: int, message_id: int):
        """register a channel for recruitment"""
        try:
            await self._execute(
                """INSERT INTO recruitment_channels (serverId, channelId, messageId) VALUES (%s, %s, %s);""",
                (server_id, channel_id, message_id),
            )
        except aiomysql.IntegrityError:
            # TODO: make into a custom exception
            raise Exception("Channel already registered")

    async def enable(self, channel_id: int) -> Optional[int]:
        """reenable a previosly disabled recruitment channel and return its status embed message id, or None if not actively registered."""
        result = await self._fetch_one(
            """SELECT messageId FROM recruitment_channels WHERE channelId = %s AND disabled = TRUE;""", (channel_id,)
        )

        if not result:
            return None

        await self._execute("""UPDATE recruitment_channels SET disabled = FALSE WHERE channelId = %s;""", (channel_id,))

        return result[0]

    async def disable(self, channel_id: int) -> Optional[int]:
        """disable a recruitment channel and return its status embed message id, or None if not actively registered."""
        result = await self._fetch_one(
            """SELECT messageId FROM recruitment_channels WHERE channelId = %s AND disabled = FALSE;""", (channel_id,)
        )

        if not result:
            return None

        await self._execute("""UPDATE recruitment_channels SET disabled = TRUE WHERE channelId = %s;""", (channel_id,))

        return result[0]

    async def add_region_to_whitelist(self, channel_id: int, region: str):
        await self._execute(
            """INSERT INTO exceptions (channelId, region) VALUES ((SELECT id FROM recruitment_channels WHERE channelId = %s), %s);""",
            (channel_id, region),
        )

    async def remove_region_from_whitelist(self, channel_id: int, region: str):
        await self._execute(
            """DELETE FROM exceptions WHERE channelId = (SELECT id FROM recruitment_channels WHERE channelId = %s) AND region = %s;""",
            (channel_id, region),
        )

    async def allow_server_registration(self, server_id: int) -> bool:
        """check if a server is allowed to register recruitment channels"""
        result = await self._fetch_one("SELECT id FROM whitelist WHERE serverId = %s;", (server_id,))

        return result is not None

from typing import Any, List, Optional, Sequence, Tuple

import aiomysql


class Database:
    def __init__(self, pool: aiomysql.Pool):
        self._pool = pool

    async def execute(self, sql: str, args: Optional[Sequence[Any]] = None) -> int:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                return await cur.execute(sql, args)

    async def fetch_one(self, sql: str, args: Optional[Sequence[Any]] = None) -> Optional[Tuple]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                return await cur.fetchone()

    async def fetch_all(self, sql: str, args: Optional[Sequence[Any]] = None) -> List[Tuple]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                return await cur.fetchall()
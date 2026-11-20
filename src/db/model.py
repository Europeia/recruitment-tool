import aiomysql

from typing import Any, Optional, Sequence


class DatabaseConnection:
    def __init__(self, pool: aiomysql.Pool):
        self._pool = pool

    async def _execute(self, sql: str, args: Optional[Sequence[Any]] = None) -> int:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                return await cur.execute(sql, args)

    async def _fetch_one(self, sql: str, args: Optional[Sequence[Any]] = None) -> Optional[tuple]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                return await cur.fetchone()

    async def _fetch_all(self, sql: str, args: Optional[Sequence[Any]] = None) -> list:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, args)
                return await cur.fetchall()

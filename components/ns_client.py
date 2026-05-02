from datetime import datetime, timezone
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup as bs

from components.config.config_manager import configInstance
from components.errors import TooManyRequests

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"


class NSClient:
    @property
    def headers(self) -> dict:
        return self._headers

    @property
    def ratelimit(self) -> Optional[int]:
        """The number of requests that NS will accept in within one bucket"""
        return self._ratelimit

    @property
    def policy(self) -> Optional[int]:
        """The length of an NS API bucket in seconds"""
        return self._policy

    @property
    def remaining(self) -> Optional[int]:
        """The number of requests remaining in the current NS API bucket"""
        return self._remaining

    @property
    def reset_in(self) -> Optional[int]:
        """The number of seconds until the current NS API bucket is reset"""
        return self._reset_in

    @property
    def request_timestamps(self) -> List[datetime]:
        """A list of timestamps for each request made in the current NS API bucket"""
        return self._request_timestamps

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session
        self._headers = {"User-Agent": f"Asperta Recruitment Bot, developed by nation=upc, run by {configInstance.data.operator}"}
        self._ratelimit: Optional[int] = None
        self._policy: Optional[int] = None
        self._remaining: Optional[int] = None
        self._reset_in: Optional[int] = None
        self._request_timestamps: List[datetime] = []

    async def get(self, **params: str) -> bs:
        current_time = datetime.now(timezone.utc)

        if self._ratelimit:
            # Check if we are exceeding the user defined maximum number of requests in a bucket
            while len(self._request_timestamps) >= configInstance.data.period_max:
                elapsed = (current_time - self._request_timestamps[0]).total_seconds()

                if self._policy is not None and elapsed > self._policy:
                    del self._request_timestamps[0]
                else:
                    raise TooManyRequests((self._policy or 0) - elapsed)

            # Check if we are exceeding the NS defined maximum number of requests in a bucket
            if self._remaining and self._remaining <= 1:
                raise TooManyRequests(self._reset_in if self._reset_in else 30)

        async with self._session.get(API_URL, headers=self._headers, params=params) as resp:
            self._ratelimit = int(resp.headers["RateLimit-limit"])
            self._policy = int(resp.headers["RateLimit-policy"].split(";w=")[1])
            self._remaining = int(resp.headers["RateLimit-remaining"])
            self._reset_in = int(resp.headers["RateLimit-reset"])
            self._request_timestamps.append(current_time)

            text = await resp.text()

            return bs(text, "xml")
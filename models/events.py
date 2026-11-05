import logging

from dataclasses import dataclass
from datetime import datetime
from typing import Self

logger = logging.getLogger("main")


@dataclass
class Event:
    id: str
    htmlstr: str
    str: str
    timestamp: int

    @classmethod
    def from_json(cls, dct: dict[str, str]) -> Self | None:
        try:
            return cls(dct["id"], dct["htmlStr"], dct["str"], int(dct["time"]))
        except KeyError:
            logger.warning(
                "failed to create event; one or more expected values missing (id: %s, htmlstr: %s, str: %s, time: %s)",
                dct.get("id"),
                dct.get("htmlStr"),
                dct.get("str"),
                dct.get("time"),
            )
            return None
        except ValueError:
            logger.warning("failed to create event; timestamp could not be converted to int (timestamp: %s)", dct.get("time"))
            return None

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

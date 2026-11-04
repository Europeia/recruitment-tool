from dataclasses import dataclass
from datetime import datetime


@dataclass
class Nation:
    name: str
    region: str
    founding_time: datetime

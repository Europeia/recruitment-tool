from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Recruiter:
    nation: str
    template: str
    discord_id: int
    next_recruitment_at: datetime

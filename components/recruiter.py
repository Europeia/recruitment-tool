from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Recruiter:
    nation: str
    template: str
    discord_id: int
    next_recruitment_at: datetime
    founded_time: datetime

    def get_cooldown(self, nation_count: int = 8):
        # cooldown per nation starts at approximately 14 seconds and decreases linearly until it is 5 seconds
        # when the nation is 18 months old
        seconds = (datetime.now(timezone.utc) - self.founded_time).days / 60

        if seconds > 9:
            return 5 * nation_count
        elif seconds < 0:
            return 14 * nation_count
        else:
            return 5 + (9 - seconds) * nation_count

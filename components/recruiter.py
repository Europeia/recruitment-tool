#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

"""Data model for a recruiter in the NationStates recruitment bot."""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class Recruiter:
    """Represents a registered recruiter and their cooldown state.

    Attributes:
        id (int): Database ID of the recruiter.
        nation (str): NationStates nation name.
        template (str): Recruitment message template.
        discord_id (int): Discord user ID.
        channel_id (int): Discord channel ID where recruitment occurs.
        next_recruitment_at (datetime): UTC timestamp when the next recruitment is allowed.
        founded_time (datetime): UTC timestamp when the account was founded.
    """
    id: int
    nation: str
    template: str
    discord_id: int
    channel_id: int
    next_recruitment_at: datetime
    founded_time: datetime

    def get_cooldown(self, nation_count: int = 8) -> int:
        """Calculate cooldown based on nation's age and count.

        The cooldown per nation starts at approximately 14 seconds and
        decreases linearly until it reaches 5 seconds when the nation
        is about 18 months old.

        Args:
            nation_count (int): Number of nations to recruit (default is 8).

        Returns:
            int: Total cooldown in seconds.
        """
        months = (datetime.now(timezone.utc) - self.founded_time).days / 60  # Approximate "age in months" from days

        if months > 9:
            return 5 * nation_count  # Mature account: 5 seconds per nation
        if months < 0:
            return 14 * nation_count  # Future date anomaly: fallback to max cooldown

        per_nation = 5 + (9 - months)  # Linear decrease from 14 to 5 seconds per nation over 0–9 months
        return int(per_nation * nation_count)

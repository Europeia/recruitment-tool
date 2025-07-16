#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Configuration data model for the recruitment bot.

Defines the ConfigData class, which holds all bot settings and provides
a factory method for loading from a dictionary (e.g., JSON).
"""

from typing import Any, Dict, List, Optional, Type, TypeVar

import discord

T = TypeVar('T', bound='ConfigData')


class ConfigData:
    """Holds configuration settings for the recruitment bot.

    Attributes:
        db_host (str): MySQL host.
        db_port (int): MySQL port.
        db_user (str): MySQL user.
        db_password (str): MySQL password.
        db_name (str): MySQL database name.
        operator (str): NationStates operator identifier for API calls.
        guild (discord.Object): Discord guild in which the bot operates.
        recruit_channel_id (int): Discord channel ID for recruitment commands.
        recruit_role_id (int): Discord role ID required to recruit.
        report_channel_id (int): Discord channel ID for recruitment reports.
        status_message_id (int): Discord message ID for status embeds.
        polling_rate (int): Interval in seconds between recruitment polls.
        period_max (int): Max API requests per configured rate-limit window.
        bot_token (str): Discord bot token.
        recruitment_exceptions (List[str]): Regions to exclude from recruitment.
    """

    @property
    def db_host(self) -> str:
        """MySQL host."""
        return self._db_host

    @property
    def db_port(self) -> int:
        """MySQL port."""
        return self._db_port

    @property
    def db_user(self) -> str:
        """MySQL user."""
        return self._db_user

    @property
    def db_password(self) -> str:
        """MySQL password."""
        return self._db_password

    @property
    def db_name(self) -> str:
        """MySQL database name."""
        return self._db_name

    @property
    def operator(self) -> str:
        """Identifier for NationStates API (nation name or email)."""
        return self._operator

    @property
    def guild(self) -> discord.Object:
        """Discord server (guild) where the bot runs."""
        return self._guild

    @property
    def recruit_channel_id(self) -> int:
        """Discord channel ID for recruitment commands."""
        return self._recruit_channel_id

    @property
    def recruit_role_id(self) -> int:
        """Discord role ID required to recruit."""
        return self._recruit_role_id

    @property
    def report_channel_id(self) -> int:
        """Discord channel ID for recruitment reports."""
        return self._report_channel_id

    @property
    def status_message_id(self) -> int:
        """Discord message ID used for status embeds."""
        return self._status_message_id

    @property
    def polling_rate(self) -> int:
        """Seconds between polls for new nations."""
        return self._polling_rate

    @property
    def period_max(self) -> int:
        """Max requests allowed in a single rate-limit window."""
        return self._period_max

    @property
    def bot_token(self) -> str:
        """Discord bot authentication token."""
        return self._bot_token

    @property
    def recruitment_exceptions(self) -> List[str]:
        """List of region codes to exclude from recruitment."""
        return self._recruitment_exceptions

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Instantiate ConfigData from a dictionary of settings.

        Args:
            data (Dict[str, Any]): Mapping of configuration keys to values.

        Returns:
            ConfigData: A new instance populated with the provided data.
        """
        return cls(
            dbHost=data['dbHost'],
            dbPort=data['dbPort'],
            dbUser=data['dbUser'],
            dbPassword=data['dbPassword'],
            dbName=data['dbName'],
            operator=data['operator'],
            guildId=data['guildId'],
            recruitChannelId=data['recruitChannelId'],
            recruitRoleId=data['recruitRoleId'],
            reportChannelId=data['reportChannelId'],
            statusMessageId=data['statusMessageId'],
            pollingRate=data['pollingRate'],
            periodMax=data['periodMax'],
            botToken=data['botToken'],
            recruitmentExceptions=data.get('recruitmentExceptions', []),
        )

    def __init__(
        self,
        dbHost: str = "",
        dbPort: int = 0,
        dbUser: str = "",
        dbPassword: str = "",
        dbName: str = "",
        operator: str = "",
        guildId: int = 0,
        recruitChannelId: int = 0,
        recruitRoleId: int = 0,
        reportChannelId: int = 0,
        statusMessageId: int = 0,
        pollingRate: int = 0,
        periodMax: int = 0,
        botToken: str = "",
        recruitmentExceptions: Optional[List[str]] = None,
    ) -> None:
        """Initialize all configuration fields.

        Args:
            dbHost (str): MySQL host.
            dbPort (int): MySQL port.
            dbUser (str): MySQL user.
            dbPassword (str): MySQL password.
            dbName (str): MySQL database name.
            operator (str): NationStates operator identifier.
            guildId (int): Discord guild ID.
            recruitChannelId (int): Recruitment channel ID.
            recruitRoleId (int): Recruitment role ID.
            reportChannelId (int): Report channel ID.
            statusMessageId (int): Status message ID.
            pollingRate (int): Polling interval in seconds.
            periodMax (int): Max API requests per window.
            botToken (str): Discord bot token.
            recruitmentExceptions (Optional[List[str]]): Regions to exclude.
        """
        self._db_host = dbHost
        self._db_port = dbPort
        self._db_user = dbUser
        self._db_password = dbPassword
        self._db_name = dbName
        self._operator = operator
        self._guild = discord.Object(id=guildId)
        self._recruit_channel_id = recruitChannelId
        self._recruit_role_id = recruitRoleId
        self._report_channel_id = reportChannelId
        self._status_message_id = statusMessageId
        self._polling_rate = pollingRate
        self._period_max = periodMax
        self._bot_token = botToken
        self._recruitment_exceptions = recruitmentExceptions or []

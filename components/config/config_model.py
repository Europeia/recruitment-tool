from datetime import datetime
from typing import Dict, Type, TypeVar
import discord
from cron_converter import Cron

T = TypeVar('T', bound='ConfigData')


class ConfigData:
    @property
    def operator(self) -> str:
        return self._operator

    @property
    def guild(self) -> discord.Object:
        return self._guild

    @property
    def recruit_channel_id(self) -> int:
        return self._recruit_channel_id

    @property
    def recruit_role_id(self) -> int:
        return self._recruit_role_id

    @property
    def report_channel_id(self) -> int:
        return self._report_channel_id

    @property
    def polling_rate(self) -> int:
        return self._polling_rate

    @property
    def period(self) -> int:
        return self._period

    @property
    def period_max(self) -> int:
        return self._period_max

    @property
    def bot_token(self) -> str:
        return self._bot_token

    @classmethod
    def from_dict(cls: Type[T], dict: Dict) -> T:
        return cls(
            operator=dict['operator'],
            guildId=dict['guildId'],
            recruitChannelId=dict['recruitChannelId'],
            recruitRoleId=dict['recruitRoleId'],
            reportChannelId=dict['reportChannelId'],
            pollingRate=dict['pollingRate'],
            period=dict['period'],
            periodMax=dict['periodMax'],
            botToken=dict['botToken']
        )
        return

    def __init__(self, operator="", guildId=0, recruitChannelId=0, recruitRoleId=0, reportChannelId=0,  pollingRate=0, period=0, periodMax=0, botToken="") -> None:
        self._operator = operator
        self._guild = discord.Object(id=guildId)
        self._recruit_channel_id = recruitChannelId
        self._recruit_role_id=recruitRoleId
        self._report_channel_id = reportChannelId
        self._polling_rate = pollingRate
        self._period = period
        self._period_max = periodMax
        self._bot_token = botToken

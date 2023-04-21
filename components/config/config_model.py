from datetime import datetime
from typing import Dict, Type, TypeVar
import discord
from cron_converter import Cron

T = TypeVar('T', bound='ConfigData')


class ConfigKeys:
    operatorKeyId = 'operator'
    guildIdKeyId = 'guildId'
    recruitChannelIdKeyId = 'recruitChannelId'
    recruitRoleIdKeyId = 'recruitRoleId'
    reportChannelIdKeyId = 'reportChannelId'
    statusMessageIdKeyId = 'statusMessageId'
    pollingRateKeyId = 'pollingRate'
    periodKeyId = 'period'
    periodMaxKeyId = 'periodMax'
    botTokenKeyId = 'botToken'


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
    def status_message_id(self) -> int:
        return self._status_message_id

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

    def to_dict(self) -> Dict[str, str | int]:
        obj_json: Dict[str, str | int] = {}
        obj_json[ConfigKeys.operatorKeyId] = self.operator
        obj_json[ConfigKeys.guildIdKeyId] = self.guild.id
        obj_json[ConfigKeys.recruitChannelIdKeyId] = self.recruit_channel_id
        obj_json[ConfigKeys.recruitRoleIdKeyId] = self.recruit_role_id
        obj_json[ConfigKeys.reportChannelIdKeyId] = self.report_channel_id
        obj_json[ConfigKeys.statusMessageIdKeyId] = self.status_message_id
        obj_json[ConfigKeys.pollingRateKeyId] = self.polling_rate
        obj_json[ConfigKeys.periodKeyId] = self.period
        obj_json[ConfigKeys.periodMaxKeyId] = self.period_max
        obj_json[ConfigKeys.botTokenKeyId] = self.bot_token
        print(f"To_dict: {obj_json}")
        return obj_json

    @classmethod
    def from_dict(cls, dict: Dict[str, str | int]):
        return cls(
            operator=str(dict[ConfigKeys.operatorKeyId]),
            guildId=int(dict[ConfigKeys.guildIdKeyId]),
            recruitChannelId=int(dict[ConfigKeys.recruitChannelIdKeyId]),
            recruitRoleId=int(dict[ConfigKeys.recruitRoleIdKeyId]),
            reportChannelId=int(dict[ConfigKeys.reportChannelIdKeyId]),
            statusMessageId=int(dict[ConfigKeys.statusMessageIdKeyId]),
            pollingRate=int(dict[ConfigKeys.pollingRateKeyId]),
            period=int(dict[ConfigKeys.periodKeyId]),
            periodMax=int(dict[ConfigKeys.periodMaxKeyId]),
            botToken=str(dict[ConfigKeys.botTokenKeyId])
        )
        return

    def __init__(self, operator="", guildId=0, recruitChannelId=0, recruitRoleId=0, reportChannelId=0,
                 statusMessageId=0, pollingRate=0, period=0, periodMax=0, botToken="") -> None:
        self._operator = operator
        self._guild = discord.Object(id=guildId)
        self._recruit_channel_id = recruitChannelId
        self._recruit_role_id = recruitRoleId
        self._report_channel_id = reportChannelId
        self._status_message_id = statusMessageId
        self._polling_rate = pollingRate
        self._period = period
        self._period_max = periodMax
        self._bot_token = botToken

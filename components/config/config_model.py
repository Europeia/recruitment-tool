from datetime import datetime
from typing import Dict, List, Type, TypeVar
import discord

T = TypeVar('T', bound='ConfigData')


class ConfigData:

    @property
    def db_host(self) -> str:
        """MySQL host"""
        return self._db_host

    @property
    def db_port(self) -> int:
        """MySQL port"""
        return self._db_port

    @property
    def db_user(self) -> str:
        """MySQL user"""
        return self._db_user

    @property
    def db_password(self) -> str:
        """MySQL password"""
        return self._db_password

    @property
    def db_name(self) -> str:
        """MySQL database name"""
        return self._db_name

    @property
    def operator(self) -> str:
        """Bot user's NS nation name or email address, for API identification"""
        return self._operator

    @property
    def guild(self) -> discord.Object:
        """Discord server that the bot runs in"""
        return self._guild

    @property
    def recruit_channel_id(self) -> int:
        """Discord channel for recruiting -- requests from outside this channel will be ignored"""
        return self._recruit_channel_id

    @property
    def recruit_role_id(self) -> int:
        """Required role for recruiting"""
        return self._recruit_role_id

    @property
    def report_channel_id(self) -> int:
        """Discord channel that recruitment reports are uploaded to, this will be removed soon :tm:"""
        return self._report_channel_id

    @property
    def status_message_id(self) -> int:
        """Discord message that the bot will edit to display the current recruitment info"""
        return self._status_message_id

    @property
    def polling_rate(self) -> int:
        """Rate at which the bot will check for new nations to recruit, in seconds"""
        return self._polling_rate

    @property
    def period_max(self) -> int:
        """Maximum number of requests that the bot will make in a single bucket"""
        return self._period_max

    @property
    def bot_token(self) -> str:
        return self._bot_token

    @property
    def recruitment_exceptions(self) -> List[str]:
        """Regions that the bot will not pull nations from"""
        return self._recruitment_exceptions

    @classmethod
    def from_dict(cls: Type[T], dict: Dict) -> T:
        return cls(
            dbHost=dict['dbHost'],
            dbPort=dict['dbPort'],
            dbUser=dict['dbUser'],
            dbPassword=dict['dbPassword'],
            dbName=dict['dbName'],
            operator=dict['operator'],
            guildId=dict['guildId'],
            recruitChannelId=dict['recruitChannelId'],
            recruitRoleId=dict['recruitRoleId'],
            reportChannelId=dict['reportChannelId'],
            statusMessageId=dict['statusMessageId'],
            pollingRate=dict['pollingRate'],
            periodMax=dict['periodMax'],
            botToken=dict['botToken'],
            recruitmentExceptions=dict['recruitmentExceptions']
        )
        return

    def __init__(self, dbHost="", dbPort=0, dbUser="", dbPassword="", dbName="", operator="", guildId=0, recruitChannelId=0,
                 recruitRoleId=0, reportChannelId=0,
                 statusMessageId=0, pollingRate=0, periodMax=0, botToken="", recruitmentExceptions=[]) -> None:
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
        self._recruitment_exceptions = recruitmentExceptions

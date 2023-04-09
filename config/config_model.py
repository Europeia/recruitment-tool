from datetime import datetime, time
import discord
from cron_converter import Cron


class ConfigData:
    @property
    def operator(self) -> str:
        return self._operator

    @property
    def guild(self) -> discord.Object:
        return self._guild

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
    def next_report(self) -> datetime:
        val = self._report_cron_obj.next()
        self._report_cron_obj = Cron(self._report_cron).schedule(start_date=val)
        return val

    def __init__(self, operator="", guildId=0, reportChannelId=0, pollingRate=0, period=0, periodMax=0, reportCron=""):
        self._operator = operator
        self._guild = discord.Object(id=guildId)
        self._report_channel_id = reportChannelId
        self._polling_rate = pollingRate
        self._period = period
        self._period_max = periodMax
        self._report_cron = reportCron
        self._report_cron_obj = Cron(reportCron).schedule(start_date=datetime.now())

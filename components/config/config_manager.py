import inspect
import json
from logging import Logger
from os import getcwd, path

from .config_model import ConfigData


class ObjectEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_json"):
            return self.default(obj.to_json())
        elif hasattr(obj, "__dict__"):
            d = dict(
                (key, value)
                for key, value in inspect.getmembers(obj)
                if not key.startswith("_")
                and not inspect.isabstract(value)
                and not inspect.isbuiltin(value)
                and not inspect.isfunction(value)
                and not inspect.isgenerator(value)
                and not inspect.isgeneratorfunction(value)
                and not inspect.ismethod(value)
                and not inspect.ismethoddescriptor(value)
                and not inspect.isroutine(value)
            )
            return self.default(d)
        return obj


class ConfigManager:
    _data: ConfigData
    _std: Logger

    def __init__(self) -> None:
        print("INIT")
        self.readConfig()
        return

    @property
    def data(self) -> ConfigData:
        return self._data

    def set_logger(self, logger: Logger) -> None:
        self._std = logger
        return

    def readConfig(self) -> None:
        print("READ")
        try:
            f = open('settings.json', 'r')
            open_message = f'Loading settings from: {path.realpath(f.name)}'
            if hasattr(self, "_std") and self._std is not None:
                self._std.info(open_message)
            else:
                print(open_message)

            dict = json.load(f)
            self._data = ConfigData.from_dict(dict)
        except Exception as ex:
            print(ex)
        return

    def writeConfig(self) -> None:
        f = open('settings.json', 'w')

        data = {
            "dbHost": self._data._db_host,
            "dbPort": self._data._db_port,
            "dbUser": self._data._db_user,
            "dbPassword": self._data._db_password,
            "dbName": self._data._db_name,
            "operator": self._data._operator,
            "guildId": self._data._guild.id,
            "recruitChannelId": self._data._recruit_channel_id,
            "recruitRoleId": self._data._recruit_role_id,
            "reportChannelId": self._data._report_channel_id,
            "statusMessageId": self._data._status_message_id,
            "pollingRate": self._data._polling_rate,
            "periodMax": self._data._period_max,
            "botToken": self._data._bot_token,
            "recruitmentExceptions": self._data._recruitment_exceptions
        }

        json.dump(data, f, cls=ObjectEncoder, indent=2, skipkeys=True)
        return


configInstance = ConfigManager()

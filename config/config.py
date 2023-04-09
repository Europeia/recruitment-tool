import inspect
import json
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


class Config:
    _loaded_config = False
    _data = None

    @property
    def data(self) -> ConfigData:
        if self._data is None and self._loaded_config == False:
            self.readConfig()
        return self._data

    def readConfig(self):
        try:
            print(getcwd())
            f = open('settings.json', 'r')
            print(path.realpath(f.name))
            dict = json.load(f)
            print(dict)
            self._data = ConfigData(
                operator=dict['operator'],
                guildId=dict['guildId'],
                reportChannelId=dict['reportChannelId'],
                pollingRate=dict['pollingRate'],
                period=dict['period'],
                periodMax=dict['periodMax'],
                reportCron=dict['reportCron'])
            print(self._data)
            self._loaded_config = True
        except Exception as ex:
            self._data = None
            print(ex)
        return

    def writeConfig(self):
        f = open('settings.json', 'w')
        json.dump(self._data, f, cls=ObjectEncoder, indent=2)
        return

    def __init__(self):
        self._loaded_config = False
        self._data = None
        return

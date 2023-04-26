import inspect
import json
from logging import Logger
from os import getcwd, path
from typing import Dict

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
        self.readConfig()
        return

    @property
    def data(self) -> ConfigData:
        return self._data

    def set_logger(self, logger: Logger) -> None:
        self._std = logger
        return

    def readConfig(self) -> None:
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

    def writeConfig(self, data: Dict[str, str | int] | None) -> None:
        if data is not None:
            self._data = ConfigData.from_dict(data)

        f = open('settings.json', 'w')
        json.dump(self._data.to_dict(), f, cls=ObjectEncoder, indent=2)
        return


configInstance = ConfigManager()

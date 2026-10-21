import inspect
import json
from os import path

from .config_model import ConfigData
from .errors import ConfigError


class ObjectEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "to_json"):
            return self.default(o.to_json())
        elif hasattr(o, "__dict__"):
            d = dict(
                (key, value)
                for key, value in inspect.getmembers(o)
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
        return o


class ConfigManager:
    _data: ConfigData

    def __init__(self) -> None:
        print("INIT")
        self.read_config()
        return

    @property
    def data(self) -> ConfigData:
        return self._data

    def read_config(self) -> None:
        print("READ")
        try:
            with open("settings.json", "r") as f:
                data = json.load(f)

                self._data = ConfigData.from_dict(data)
        except FileNotFoundError:
            raise ConfigError(f"settings.json not found at {path.realpath('settings.json')}.")
        except json.JSONDecodeError as e:
            raise ConfigError(f"settings.json is malformed: {e}") from e
        except KeyError as e:
            raise ConfigError(f"settings.json is missing required field: {e.args[0]}") from e

    def write_config(self) -> None:
        with open("settings.json", "w") as f:
            data = {
                "db_host": self._data.db_host,
                "db_port": self._data.db_port,
                "db_user": self._data.db_user,
                "db_password": self._data.db_password,
                "db_name": self._data.db_name,
                "operator": self._data.operator,
                "polling_rate": self._data.polling_rate,
                "period_max": self._data.period_max,
                "bot_token": self._data.bot_token,
                "global_administrators": self._data.global_administrators,
                "environment": self._data._environment,
            }

            json.dump(data, f, cls=ObjectEncoder, indent=2, skipkeys=True)


configInstance = ConfigManager()

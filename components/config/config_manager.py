#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Configuration manager for the recruitment bot.

Provides:
  * ObjectEncoder: JSON encoder supporting objects with `to_json` or attributes.
  * ConfigManager: Load and save `settings.json` to a `ConfigData` instance.
  * configInstance: Singleton instance of ConfigManager.
"""

import inspect
import json
import os
from logging import Logger
from typing import Any, Optional

from .config_model import ConfigData


class ObjectEncoder(json.JSONEncoder):
    """JSON encoder that serializes objects via `to_json` or their public attributes."""

    def default(self, obj: Any) -> Any:
        """Convert supported objects to JSON-serializable structures.

        Args:
            obj: The object to encode.

        Returns:
            A JSON-serializable representation of the object.
        """
        if hasattr(obj, "to_json"):
            return self.default(obj.to_json())
        if hasattr(obj, "__dict__"):  # Collect non-private, non-callable members
            members = {
                key: value
                for key, value in inspect.getmembers(obj)
                if not key.startswith("_") and not inspect.isroutine(value)
            }
            return self.default(members)
        return super().default(obj)


class ConfigManager:
    """Manage reading from and writing to the bot's JSON settings file."""

    def __init__(self) -> None:
        """Initialize the manager and load existing settings."""
        self._std: Optional[Logger] = None
        self._data: ConfigData
        self.read_config()

    @property
    def data(self) -> ConfigData:
        """Current in-memory configuration."""
        return self._data

    def set_logger(self, logger: Logger) -> None:
        """Assign a logger for informational and error messages.

        Args:
            logger (Logger): Logger instance to use.
        """
        self._std = logger

    def read_config(self) -> None:
        """Load configuration from `settings.json`.

        Logs the file path via the assigned logger, or prints it if none.
        """
        filepath = "settings.json"
        try:
            with open(filepath, "r") as f:
                message = f"Loading settings from: {os.path.realpath(f.name)}"
                if self._std:
                    self._std.info(message)
                else:
                    print(message)
                config_dict = json.load(f)
            self._data = ConfigData.from_dict(config_dict)
        except Exception as ex:
            print(f"Error reading config '{filepath}': {ex}")

    def write_config(self) -> None:
        """Write the current configuration to `settings.json`."""
        filepath = "settings.json"
        try:
            with open(filepath, "w") as f:
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
                    "recruitmentExceptions": self._data._recruitment_exceptions,
                }
                json.dump(data, f, cls=ObjectEncoder, indent=2, skipkeys=True)
        except Exception as ex:
            message = f"Error writing config '{filepath}': {ex}"
            if self._std:
                self._std.error(message)
            else:
                print(message)


configInstance = ConfigManager()

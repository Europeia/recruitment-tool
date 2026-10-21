from typing import Dict, List, Type, TypeVar
from enum import StrEnum

T = TypeVar("T", bound="ConfigData")


class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


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
    def global_administrators(self) -> List[int]:
        """discord user ids for users with superadmin permissions"""
        return self._global_administrators

    @property
    def environment(self) -> Environment:
        return self._environment

    @property
    def log_level(self) -> LogLevel:
        return self._log_level

    @classmethod
    def from_dict(cls: Type[T], dict: Dict) -> T:
        return cls(
            db_host=dict["db_host"],
            db_port=dict["db_port"],
            db_user=dict["db_user"],
            db_password=dict["db_password"],
            db_name=dict["db_name"],
            operator=dict["operator"],
            polling_rate=dict["polling_rate"],
            period_max=dict["period_max"],
            bot_token=dict["bot_token"],
            global_administrators=dict["global_administrators"],
            environment=dict["environment"].lower(),
            log_level=dict["log_level"].upper(),
        )

    def __init__(
        self,
        db_host="",
        db_port=0,
        db_user="",
        db_password="",
        db_name="",
        operator="",
        polling_rate=0,
        period_max=0,
        bot_token="",
        global_administrators=[],
        environment=Environment.DEVELOPMENT,
        log_level=LogLevel.INFO,
    ) -> None:
        self._db_host = db_host
        self._db_port = db_port
        self._db_user = db_user
        self._db_password = db_password
        self._db_name = db_name
        self._operator = operator
        self._polling_rate = polling_rate
        self._period_max = period_max
        self._bot_token = bot_token
        self._global_administrators = global_administrators
        self._environment = environment
        self._log_level = log_level

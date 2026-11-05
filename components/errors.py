import discord
from discord import app_commands
from discord.ext import commands


class EmptyQueue(commands.CommandError):
    def __init__(self):
        super().__init__(message="queue empty")


class LastRecruitmentTooRecent(commands.CommandError):
    def __init__(self, user: discord.User | discord.Member, reset_in: float):
        self._user = user
        self._reset_in = reset_in

        super().__init__(message=f"{self._user.name}'s last recruitment was too recent, reset in {self._reset_in:.2f} seconds.")


class NoRecruiterRole(commands.CommandError):
    def __init__(self, user: discord.User):
        self.user = user

        super().__init__(message=f"{self.user.name} missing the recruiter role")


class NotRecruitManager(commands.CommandError):
    def __init__(self, user: discord.User):
        self.user = user

        super().__init__(message=f"{self.user.name} is not a recruit manager")


class NotRegistered(commands.CommandError):
    def __init__(self, user: discord.User | discord.Member):
        self._user = user

        super().__init__(message=f"{self._user.name} has not registered as a recruiter")


class TooManyRequests(commands.CommandError):
    def __init__(self, reset_in: float):
        self.reset_in = reset_in

        super().__init__(message=f"too many requests made in the current bucket, reset in {reset_in:.2f} seconds.")


class NationNotFound(commands.CommandError):
    """Raised when a nation cannot be retrieved via the NationStates API"""

    def __init__(self, user: discord.User | discord.Member, nation: str):
        self._user = user
        self._nation = nation

        super().__init__(message=f"{self._nation} does not exist")


class WhitelistError(app_commands.AppCommandError):
    """Raised when someone attempts to register a recruitment channel in server that is not whitelisted"""

    def __init__(self, user: discord.User | discord.Member, guild: discord.Guild):
        self.user = user
        self.guild = guild

        # super().__init__(message=f"{self.user.name} attempted to register server {self.guild.name} without being "
        #                          f"whitelisted")
        super().__init__()


class ActiveSessionError(commands.CommandError):
    """raised when a user with an active session tries to recruit normally"""

    def __init__(self, user: discord.User | discord.Member):
        self._user = user

        super().__init__(f"{self._user.name} attempted to recruit while in a session")

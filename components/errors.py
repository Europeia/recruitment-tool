import discord

from discord import app_commands
from discord.ext import commands


class EmptyQueue(commands.CommandError):
    def __init__(self, user: discord.User):
        self.user = user

        super().__init__(message=f"queue empty")


class LastRecruitmentTooRecent(commands.CommandError):
    def __init__(self, user: discord.User, reset_in: float):
        self.user = user
        self.reset_in = reset_in

        super().__init__(message=f"{self.user.name}'s last recruitment was too recent, reset in {self.reset_in:.2f} seconds.")


class NoRecruiterRole(commands.CommandError):
    def __init__(self, user: discord.User):
        self.user = user

        super().__init__(message=f"{self.user.name} missing the recruiter role")


class NotRecruitManager(commands.CommandError):
    def __init__(self, user: discord.User):
        self.user = user

        super().__init__(message=f"{self.user.name} is not a recruit manager")


class NotRegistered(commands.CommandError):
    def __init__(self, user: discord.User):
        self.user = user

        super().__init__(message=f"{self.user.name} has not registered as a recruiter")


class TooManyRequests(commands.CommandError):
    def __init__(self, reset_in: float):
        self.reset_in = reset_in

        super().__init__(message=f"too many requests made in the current bucket, reset in {reset_in:.2f} seconds.")


class NationNotFound(commands.CommandError):
    """Raised when a nation cannot be retrieved via the NationStates API"""
    def __init__(self, user: discord.User, nation: str):
        self.user = user
        self.nation = nation

        super().__init__(message=f"{self.nation} does not exist")


class WhitelistError(app_commands.AppCommandError):
    """Raised when someone attempts to register a recruitment channel in server that is not whitelisted"""
    def __init__(self, user: discord.User, guild: discord.Guild):
        self.user = user
        self.guild = guild

        # super().__init__(message=f"{self.user.name} attempted to register server {self.guild.name} without being "
        #                          f"whitelisted")
        super().__init__()

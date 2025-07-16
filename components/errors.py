# SPDX-License-Identifier: GPL-3.0-or-later
"""Custom command error classes for the recruitment bot.

This module defines exceptions that extend from discord.ext.commands.CommandError
and app_commands.AppCommandError to represent various error conditions in the
Aperta Recruitment Bot.
"""

import discord
from discord import app_commands
from discord.ext import commands


class EmptyQueue(commands.CommandError):
    """Raised when the recruitment queue is empty.

    Attributes:
        user (discord.User): The user who attempted to recruit.
    """

    def __init__(self, user: discord.User):
        """Initialize EmptyQueue.

        Args:
            user (discord.User): The user who attempted to recruit.
        """
        self.user = user
        super().__init__(message="Recruitment queue is empty.")


class LastRecruitmentTooRecent(commands.CommandError):
    """Raised when a user attempts to recruit before their cooldown has expired.

    Attributes:
        user (discord.User): The user who attempted to recruit.
        reset_in (float): Seconds remaining until next allowed recruitment.
    """

    def __init__(self, user: discord.User, reset_in: float):
        """Initialize LastRecruitmentTooRecent.

        Args:
            user (discord.User): The user who attempted to recruit.
            reset_in (float): Seconds remaining until the cooldown expires.
        """
        self.user = user
        self.reset_in = reset_in
        message = (
            f"{user.name}'s last recruitment was too recent; "
            f"resets in {reset_in:.2f} seconds."
        )
        super().__init__(message=message)


class NoRecruiterRole(commands.CommandError):
    """Raised when a user lacks the required recruiter role.

    Attributes:
        user (discord.User): The user without the recruiter role.
    """

    def __init__(self, user: discord.User):
        """Initialize NoRecruiterRole.

        Args:
            user (discord.User): The user missing the recruiter role.
        """
        self.user = user
        super().__init__(message=f"{user.name} is missing the recruiter role.")


class NotRecruitManager(commands.CommandError):
    """Raised when a user is not designated as a recruit manager.

    Attributes:
        user (discord.User): The user who attempted a manager-only action.
    """

    def __init__(self, user: discord.User):
        """Initialize NotRecruitManager.

        Args:
            user (discord.User): The user who is not a recruit manager.
        """
        self.user = user
        super().__init__(message=f"{user.name} is not a recruit manager.")


class NotRegistered(commands.CommandError):
    """Raised when a user has not registered as a recruiter.

    Attributes:
        user (discord.User): The user who attempted to recruit.
    """

    def __init__(self, user: discord.User):
        """Initialize NotRegistered.

        Args:
            user (discord.User): The user who is not registered.
        """
        self.user = user
        super().__init__(message=f"{user.name} has not registered as a recruiter.")


class TooManyRequests(commands.CommandError):
    """Raised when the API rate limit has been exceeded.

    Attributes:
        reset_in (float): Seconds remaining until the rate limit resets.
    """

    def __init__(self, reset_in: float):
        """Initialize TooManyRequests.

        Args:
            reset_in (float): Seconds until the rate limit window resets.
        """
        self.reset_in = reset_in
        super().__init__(message=f"Too many requests; resets in {reset_in:.2f} seconds.")


class NationNotFound(commands.CommandError):
    """Raised when a nation cannot be retrieved via the NationStates API.

    Attributes:
        user (discord.User): The user who requested the nation.
        nation (str): The nation identifier that was not found.
    """

    def __init__(self, user: discord.User, nation: str):
        """Initialize NationNotFound.

        Args:
            user (discord.User): The user who requested the nation.
            nation (str): The nation name or ID that was not found.
        """
        self.user = user
        self.nation = nation
        super().__init__(message=f"{nation} does not exist.")


class WhitelistError(app_commands.AppCommandError):
    """Raised when a server is not whitelisted for recruitment commands.

    Attributes:
        user (discord.User): The user who attempted the command.
        guild (discord.Guild): The guild that is not whitelisted.
    """

    def __init__(self, user: discord.User, guild: discord.Guild):
        """Initialize WhitelistError.

        Args:
            user (discord.User): The user who attempted the command.
            guild (discord.Guild): The guild that is not whitelisted.
        """
        self.user = user
        self.guild = guild
        message = (
            f"{user.name} attempted to register server "
            f"'{guild.name}' without it being whitelisted."
        )
        super().__init__(message=message)

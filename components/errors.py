import discord

from discord.ext import commands


class NotRegistered(commands.CommandError):
    user: discord.User

    def __init__(self, user: discord.User):
        self.user = user
        super().__init__(message="Not Registered!")


class NotRecruiter(commands.CommandError):
    user: discord.User

    def __init__(self, user: discord.User):
        self.user = user
        super().__init__(message="You don't have the 'Recruiter' role!")


class NotRecruitmentChannel(commands.CommandError):
    user: discord.User

    def __init__(self, user: discord.User):
        self.user = user
        super().__init__(message="Wrong channel!")


class EmptyQueue(commands.CommandError):
    user: discord.User

    def __init__(self, user: discord.User):
        self.user = user
        super().__init__(message="The queue is empty!")


class LastRecruitTooRecent(commands.CommandError):
    user: discord.User
    retry_in: float

    def __init__(self, user: discord.User, retry_in: float):
        self.user = user
        self.retry_in = retry_in
        super().__init__(message="You have already recruited someone recently!")


class SessionAlreadyStarted(commands.CommandError):
    user: discord.User

    def __init__(self, user: discord.User):
        self.user = user
        super().__init__(message="You already have a session started!")


class ActiveSession(commands.CommandError):
    user: discord.User

    def __init__(self, user: discord.User):
        self.user = user
        super().__init__(message="You cannot use /recruit while in a session!")


class NoWelcomeTemplate(commands.CommandError):
    user: discord.User

    def __init__(self, user: discord.User):
        self.user = user
        super().__init__("No welcome template")

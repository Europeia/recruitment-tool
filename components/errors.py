import discord

from discord.ext import commands


class NotRegistered(commands.CommandError):
    def __init__(self, user: discord.User):
        self.user = user
        super().__init__(message="Not Registered!")


class NotRecruiter(commands.CommandError):
    def __init__(self, user: discord.User):
        self.user = user
        super().__init__(message="You don't have the 'Recruiter' role!")


class NotRecruitmentChannel(commands.CommandError):
    def __init__(self, user: discord.User):
        self.user = user
        super().__init__(message="Wrong channel!")

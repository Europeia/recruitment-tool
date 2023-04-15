from discord.ext import commands

from components.config.config_manager import configInstance
from components.users import Users
from components.errors import NotRegistered, NotRecruiter, NotRecruitmentChannel


def register_command_validated(ctx: commands.Context) -> bool:
    return in_recruit_channel(ctx) and is_recruiter(ctx)


def recruit_command_validated(users: Users, ctx: commands.Context) -> bool:
    return in_recruit_channel(ctx) and is_registered(users, ctx) and is_recruiter(ctx)


def in_recruit_channel(ctx: commands.Context) -> bool:
    if ctx.channel.id != configInstance.data.recruit_channel_id:
        raise NotRecruitmentChannel(ctx.author)  # type: ignore
    else:
        return True


def is_registered(users: Users, ctx: commands.Context) -> bool:
    if not users.get(ctx.author):
        raise NotRegistered(ctx.author)  # type: ignore
    else:
        return True


def is_recruiter(ctx: commands.Context) -> bool:
    if ctx.guild.get_role(configInstance.data.recruit_role_id) not in ctx.author.roles:  # type: ignore
        raise NotRecruiter(ctx.author)  # type: ignore
    else:
        return True

from discord.ext import commands

import config
from components.users import Users
from components.errors import NotRegistered, NotRecruiter, NotRecruitmentChannel


def register_command_validated(ctx: commands.Context) -> bool:
    return in_recruit_channel(ctx) and is_recruiter(ctx)


def recruit_command_validated(users: Users, ctx: commands.Context) -> bool:
    return in_recruit_channel(ctx) and is_registered(users, ctx) and is_recruiter(ctx)


def in_recruit_channel(ctx: commands.Context) -> bool:
    if ctx.channel.id != config.RECRUIT_CHANNEL_ID:
        raise NotRecruitmentChannel(ctx.author)
    else:
        return True


def is_registered(users: Users, ctx: commands.Context) -> bool:
    if not users.get(ctx.author.id):
        raise NotRegistered(ctx.author)
    else:
        return True


def is_recruiter(ctx: commands.Context) -> bool:
    if ctx.guild.get_role(config.RECRUIT_ROLE_ID) not in ctx.author.roles:
        raise NotRecruiter(ctx.author)
    else:
        return True

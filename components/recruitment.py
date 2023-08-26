import discord

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple

from components.bot import RecruitBot
from components.views import RecruitView
from components.errors import EmptyQueue, LastRecruitTooRecent, NotRegistered, NoWelcomeTemplate


class RecruitType(Enum):
    COMMAND = 1,
    SESSION = 2,
    WELCOME = 3


def get_recruit_embed(user: discord.User, bot: RecruitBot, rtype: RecruitType) -> \
        Tuple[discord.Embed, RecruitView | discord.ui.Button]:
    recruiter = bot.rusers.get(user)

    if recruiter.allow_recruitment_at > datetime.now(timezone.utc):
        raise LastRecruitTooRecent(user, (recruiter.allow_recruitment_at - datetime.now(timezone.utc)).total_seconds())

    color = int("2d0001", 16)

    if rtype == RecruitType.WELCOME:
        if not recruiter.welcome_template:
            raise NoWelcomeTemplate(user)

        nation = bot.welcome_queue.get_nations(user=user, return_count=1)[0]

        embed = discord.Embed(title="Welcome", color=color)
        embed.add_field(name="Nation", value=f"https://www.nationstates.net/nation={nation}")
        embed.add_field(name="Template", value=f"```{recruiter.welcome_template}```", inline=False)
        embed.set_footer(
            text=f"Initiated by {recruiter.nation} at {datetime.now(timezone.utc).strftime('%H:%M:%S')}")

        view = RecruitView()
        view.add_item(discord.ui.Button(label="Open Telegram", style=discord.ButtonStyle.link,
                                        url=f"https://www.nationstates.net/page=compose_telegram?tgto={nation}&message=%25{recruiter.welcome_template}%25"))

        recruiter.set_next_recruitment(1)
        bot.daily.info(f"{recruiter.nation}")

        return embed, view

    nations = bot.queue.get_nations(user=user)

    embed = discord.Embed(title=f"Recruit", color=color)
    embed.add_field(name="Nations", value="\n".join(
        [f"https://www.nationstates.net/nation={nation}" for nation in nations]))
    embed.add_field(name="Template",
                    value=f"```{recruiter.template}```", inline=False)
    embed.set_footer(
        text=f"Initiated by {recruiter.nation} at {datetime.now(timezone.utc).strftime('%H:%M:%S')}")

    match rtype:
        case RecruitType.COMMAND:

            # link buttons can't be created in a subclassed view, so this is basically
            # an empty view with nothing but an on_timeout method
            view = RecruitView()
            view.add_item(discord.ui.Button(label="Open Telegram", style=discord.ButtonStyle.link,
                                            url=f"https://www.nationstates.net/page=compose_telegram?tgto={','.join(nations)}&message=%25{recruiter.template}%25"))

        case RecruitType.SESSION:
            view = discord.ui.Button(label="Open Telegram", style=discord.ButtonStyle.link,
                                     url=f"https://www.nationstates.net/page=compose_telegram?tgto={','.join(nations)}&message=%25{recruiter.template}%25")

    recruiter.set_next_recruitment(len(nations))
    bot.daily.info(f"{recruiter.nation} {len(nations)}")

    return embed, view

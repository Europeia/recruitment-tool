import discord

from datetime import datetime, timezone, time
from typing import Optional, Tuple

from discord.app_commands import commands

from components.bot import RecruitBot
from components.views import RecruitView

def recruit(user, ctx: commands.Context, bot: RecruitBot) -> Optional[Tuple[discord.Embed, RecruitView]]:
    response_tuple = get_recruit_embed(user_id=ctx.author.id, bot=bot)

    if response_tuple:
        user.last_recruited = time.time()

    return response_tuple


def get_recruit_embed(user_id: int, bot: RecruitBot) -> Optional[Tuple[discord.Embed, RecruitView]]:
    user = bot.rusers.get(user_id)

    # this will never happen because we validate that the user exists in the command,
    # but my IDE is complaining without it
    if not user:
        return None

    nations = bot.queue.get_nations()

    if not nations:
        return None

    color = int("2d0001", 16)
    embed = discord.Embed(title=f"Recruit", color=color)
    embed.add_field(name="Nations", value="\n".join(
        [f"https://www.nationstates.net/nation={nation}" for nation in nations]))
    embed.add_field(name="Template",
                    value=f"```{user.template}```", inline=False)
    embed.set_footer(
        text=f"Initiated by {user.nation} at {datetime.now(timezone.utc).strftime('%H:%M:%S')}")

    # link buttons can't be created in a subclassed view, so this is basically
    # an empty view with nothing but an on_timeout method
    view = RecruitView()
    view.add_item(discord.ui.Button(label="Open Telegram", style=discord.ButtonStyle.link,
                                    url=f"https://www.nationstates.net/page=compose_telegram?tgto={','.join(nations)}&message=%25{user.template}%25"))

    bot.daily.info(f"{user.nation} {len(nations)}")

    return embed, view

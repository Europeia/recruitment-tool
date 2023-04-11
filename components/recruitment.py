import discord

from datetime import datetime, timezone
from typing import Optional, Tuple

from components.bot import RecruitBot
from components.views import RecruitView


def get_recruit_embed(user_id: int, bot: RecruitBot) -> Optional[Tuple[discord.Embed, RecruitView]]:
    user = bot.rusers.get(user_id)

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
        text=f"Initiated by {user.nation} at {datetime.now(timezone.utc)}")

    # link buttons can't be created in a subclassed view, so this is basically
    # an empty view with nothing but an on_timeout method
    view = RecruitView()
    view.add_item(discord.ui.Button(label="Open Telegram", style=discord.ButtonStyle.link,
                                    url=f"https://www.nationstates.net/page=compose_telegram?tgto={','.join(nations)}&message={user.template}"))

    bot.daily.info(f"{user.nation} {len(nations)}")

    return embed, view

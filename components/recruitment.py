from datetime import datetime, timezone
from typing import Optional, Tuple

import discord
from discord.app_commands import commands
from discord.ui import Button

from cogs.sessions import Session
from components.bot import RecruitBot
from components.views import RecruitView


def recruit(ctx: commands.Context, bot: RecruitBot, session: Session = None):
    response_tuple = get_recruit_embed(user_id=ctx.author.id, bot=bot, session=session)

    if response_tuple:
        embed, view = response_tuple
        view.message = await ctx.reply(embed=embed, view=view)
        return True
    else:
        return False


def get_recruit_embed(user_id: int, bot: RecruitBot, session: Session) -> Optional[Tuple[discord.Embed, RecruitView]]:
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
        text=f"Initiated by {user.nation} at {datetime.now(timezone.utc)}")

    # link buttons can't be created in a subclassed view, so this is basically
    # an empty view with nothing but an on_timeout method
    view = RecruitView()
    button_ack = discord.ui.Button(label="Acknowledge", style=discord.ButtonStyle.green,
                                   custom_id=session.custom_id)
    button_send = discord.ui.Button(label="Send TG", style=discord.ButtonStyle.link, disabled=True,
                                    url=f"https://www.nationstates.net/page=compose_telegram?tgto={','.join(nations)}&message=%25{user.template}%25")

    view.add_item(button_ack)
    view.add_item(button_send)

    bot.daily.info(f"{user.nation} {len(nations)}")

    update_buttons()
    return embed, view


async def update_buttons(bot: RecruitBot, button_ack: Button, button_send: Button, session: Session):
    await bot.wait_for('interaction', check=lambda interaction: interaction.data[
                                                                    "component_type"] == 2 and session.custom_id in interaction.data.keys())

    button_ack.disabled = True
    button_send.disabled = False

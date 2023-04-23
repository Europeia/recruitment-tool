import discord

from datetime import datetime, timezone
from discord.ext import tasks
from typing import Optional

from components.bot import RecruitBot
from components.views import SessionView


class Session:
    bot: RecruitBot
    user: discord.User
    interval: int = 45
    strikes: int = 0
    channel: Optional[discord.TextChannel] = None

    def __init__(self, bot: RecruitBot, user: discord.User, channel_id: int, interval):
        self.bot = bot
        self.user = user
        self.channel = self.bot.get_channel(channel_id)

        self.interval = interval
        self.recruit_loop.change_interval(seconds=self.interval)

        self.recruit_loop.start()

    @tasks.loop(seconds=interval)
    async def recruit_loop(self):
        self.bot.std.info(f"Session looping for user {self.user.name}")
        if self.strikes >= 2:
            self.recruit_loop.cancel()
            self.bot.rusers.get(self.user).active_session = False
            await self.channel.send(f"Ending <@!{self.user.id}>'s recruitment session due to inactivity.")
        else:
            view = SessionView(self)
            view.message = await self.channel.send(f"<@!{self.user.id}>", view=view)

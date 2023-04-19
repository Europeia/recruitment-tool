from datetime import datetime, timezone
from discord import app_commands
from discord.ext import commands
from typing import Dict, Optional

from components.bot import RecruitBot
from components.config.config_manager import configInstance
from components.errors import SessionAlreadyStarted
from components.session import Session


class Sessions(commands.Cog):
    bot: RecruitBot
    sessions: Dict[int, Session] = {}

    def __init__(self, bot: RecruitBot):
        self.bot = bot

    def cog_unload(self):
        for session in self.sessions.values():
            session.test.cancel()

        for user in self.bot.rusers.users:
            user.active_session = False

    @commands.hybrid_command(name="session", with_app_command=True, description="Start a session")
    @app_commands.guilds(configInstance.data.guild)
    async def session(self, ctx: commands.Context, interval: int = 35):
        if self.sessions.get(ctx.author.id):
            raise SessionAlreadyStarted(ctx.author)

        self.bot.rusers.get(ctx.author).active_session = True

        if interval < 35:
            interval = 35

        self.sessions[ctx.author.id] = Session(self.bot, ctx.author, ctx.channel.id, interval)

        await ctx.reply(
            f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} - Session started for user {ctx.author}! Interval: {interval} seconds")


async def setup(bot):
    await bot.add_cog(Sessions(bot))

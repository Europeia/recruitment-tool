from asyncio import tasks

from dateutil import parser as timeinput
from dateutil.parser import ParserError
from discord import app_commands
from discord.app_commands import commands

from components.bot import RecruitBot
from components.config.config_manager import configInstance
from components.recruitment import recruit


# Object representing a recruitment session (user has requested reminders on an interval)
class Session:
    ctx: commands.Context
    interval: int = 30
    active: bool
    bot: RecruitBot

    @tasks.loop(seconds=interval)
    def work(self):
        if self.active:
            recruit(self.ctx, self.bot)
        # else: TODO end the loop if false


class SessionsCog(commands.Cog):
    bot: RecruitBot

    def __init__(self, bot: RecruitBot):
        self.bot = bot
        self.sessions = dict()

    @commands.hybrid_command(name="start", with_app_command=True, description="Start a recruitment session")
    @app_commands.guilds(configInstance.data.guild)
    async def start(self, ctx: commands.Context, duration: str = None):
        await ctx.defer()

        # Convert user input to a number of seconds
        interval = None
        # Just a number, assume it's seconds
        if duration.isnumeric():
            interval = duration
        # A string, try to parse it
        else:
            try:
                time = timeinput.parse(duration)
                interval = (time.day * 86400) + (time.hour * 3600) + (time.minute * 60) + (time.second)

                # Do some basic validation
                if interval < 30:
                    await ctx.reply("You cannot set a reminder interval shorter than 30 seconds.")
                elif interval > 86400:
                    await ctx.reply("You cannot set a reminder interval greater than 1 day.")
                    return
            # Exceptions on timeinput.parse
            except ParserError:
                await ctx.reply("Invalid reminder interval. Please try again.")
            except OverflowError:
                await ctx.reply("Your reminder interval broke the computer. Nice job.")

        # Create the session
        await ctx.reply(f"Starting new session with reminders every {interval} seconds.")
        session = Session(ctx, interval, True, self.bot)
        self.sessions.update({ctx.author.id, session})

    @commands.hybrid_command(name="stop", with_app_command=True, description="End your recruitment session")
    async def stop(self, ctx: commands.Context):

        # Find & end the session
        session = self.sessions.get(ctx.author.id)
        session.active = False

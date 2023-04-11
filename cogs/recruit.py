import asyncio

import requests

from bs4 import BeautifulSoup as bs
from datetime import datetime
from discord import app_commands
from discord.ext import commands, tasks

import config
from components.users import User
from components.checks import recruit_command_validated, register_command_validated
from components.recruitment import get_recruit_embed


class Recruit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.request_times: list[datetime] = []

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.newnations_polling.is_running():
            self.bot.std.info("Starting newnations polling")
            self.newnations_polling.start()
            self.bot.std.info("Starting reporting")
            self.reporter.start()

    @commands.hybrid_command(name="register", with_app_command=True,
                             description="Register a nation and telegram template")
    @app_commands.guilds(config.SERVER)
    async def register(self, ctx: commands.Context, nation: str, template: str):
        await ctx.defer()

        register_command_validated(ctx=ctx)

        new_user = User(
            ctx.author.id, nation.lower().replace(" ", "_"), template.replace("%", "%25"))

        self.bot.rusers.add(new_user)
        self.bot.std.info(
            f"Registering user: {new_user.id} with nation: {new_user.nation} and template: {new_user.template}")

        await ctx.reply("Registration complete!")

    @commands.cooldown(1, 40, commands.BucketType.user)
    @commands.hybrid_command(name="recruit", with_app_command=True, description="Generate a list of nations to recruit")
    @app_commands.guilds(config.SERVER)
    async def recruit(self, ctx: commands.Context):
        await ctx.defer()

        recruit_command_validated(users=self.bot.rusers, ctx=ctx)

        response_tuple = get_recruit_embed(user_id=ctx.author.id, bot=self.bot)

        if response_tuple:
            embed, view = response_tuple
            view.message = await ctx.reply(embed=embed, view=view)
        else:
            await ctx.reply("No nations in the queue at the moment!")

    @commands.hybrid_command(name="start", with_app_command=True, description="Start newnation polling")
    @app_commands.guilds(config.SERVER)
    @commands.has_permissions(administrator=True)
    async def start(self, ctx: commands.Context):
        await ctx.defer()

        if self.newnations_polling.is_running():
            await ctx.reply("Polling already started.")
        else:
            self.bot.std.info(f"Newnations polling initiated by {ctx.author}")
            self.newnations_polling.start()
            await ctx.reply("Polling started.")

    @commands.hybrid_command(name="stop", with_app_command=True, description="Stop newnation polling")
    @app_commands.guilds(config.SERVER)
    @commands.has_permissions(administrator=True)
    async def stop(self, ctx: commands.Context):
        await ctx.defer()

        if self.newnations_polling.is_running():
            self.bot.std.info(f"Newnations polling stopped by {ctx.author}")
            self.newnations_polling.cancel()
            await ctx.reply("Polling stopped.")
        else:
            await ctx.reply("Polling already stopped.")

    @commands.hybrid_command(name="purge", with_app_command=True, description="Clear queue")
    @app_commands.guilds(config.SERVER)
    @commands.has_permissions(administrator=True)
    async def purge(self, ctx: commands.Context):
        await ctx.defer()

        self.bot.std.info(f"Queue purge initiated by {ctx.author}")
        self.bot.queue.purge()

        await ctx.reply("Done.")

    @tasks.loop(seconds=config.POLLING_RATE)
    async def newnations_polling(self):
        current_time = datetime.now()

        while len(self.request_times) >= config.PERIOD_MAX:
            elapsed = (current_time - self.request_times[0]).total_seconds()

            if elapsed > config.PERIOD:
                del self.request_times[0]
            else:
                self.bot.std.info(
                    f"Sleeping for {config.PERIOD - elapsed} seconds")
                await asyncio.sleep(config.PERIOD - elapsed)

        self.request_times.append(current_time)

        headers = {
            "User-Agent": f"Euro Recruitment Bot, developed by upcnationstates@gmail.com, used by {self.bot.operator}"}

        try:
            self.bot.std.info("Polling NEWNATIONS shard.")
            new_nations = bs(requests.get("https://www.nationstates.net/cgi-bin/api.cgi?q=newnations",
                                          headers=headers).text, "xml").NEWNATIONS.text.split(",")
        except:
            # certified error handling moment
            self.bot.std.error(
                "An unspecified error occured while trying to reach the NS API")
        else:
            current_nations = [
                nation.name for nation in self.bot.queue.nations]

            # reverse the list because queue.add prepends to the queue
            # (so we get most recent nations first)
            for nation in reversed(new_nations):
                if nation not in current_nations:
                    self.bot.queue.add(nation)

    @tasks.loop(time=config.START_TIME)
    async def reporter(self):
        self.bot.std.info("Sending daily report")
        reports_channel = self.bot.get_channel(config.REPORT_CHANNEL_ID)

        with open("logs/daily.log", "r") as in_file:
            data = in_file.readlines()

        users = {}

        for entry in data:
            if not entry:
                return

            try:
                user, count = entry.split(": ")[1].split()
            except:
                # realistically this will never happen (someone would have to go in and manually fuck with the log file)
                # but jic
                pass
            else:
                if user in users:
                    users[user] += int(count)
                else:
                    users[user] = int(count)

        summary = "\n".join(f"{k}: {v}" for k, v in sorted(
            users.items(), key=lambda item: item[1]))

        # date format YYYY-MM-DD
        date = datetime.now().strftime("%Y-%m-%d")

        await reports_channel.send(f"Daily Report: {date}\n```{summary}```")


async def setup(bot):
    await bot.add_cog(Recruit(bot))

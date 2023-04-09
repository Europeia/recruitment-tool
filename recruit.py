import asyncio
import discord
import requests

from bs4 import BeautifulSoup as bs
from datetime import datetime, timezone
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View
from main import Bot

from users import User


class RecruitButton(View):
    def __init__(self):
        super().__init__()

    async def on_timeout(self):
        self.value = None
        for child in self.children:
            child.disabled = True

        await self.message.edit(view=self)
        self.stop()


class recruit(commands.Cog):
    bot: Bot = None

    def __init__(self, bot: Bot):
        self.bot = bot
        self.request_times: list[datetime] = []

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.newnations_polling.is_running():
            self.bot.std.info("Starting newnations polling")
            self.newnations_polling.start()
            self.bot.std.info("Starting reporting")
            self.reporter.start()

    @commands.hybrid_command(name="register", with_app_command=True, description="Register a nation and telegram template")
    @app_commands.guilds(bot.config.data.guild)
    async def register(self, ctx: commands.Context, nation: str, template: str):
        await ctx.defer()

        new_user = User(
            ctx.author.id, nation.lower().replace(" ", "_"), template)

        self.bot.rusers.add(new_user)
        self.bot.std.info(
            f"Registering user: {new_user.id} with nation: {new_user.nation} and template: {new_user.template}")

        await ctx.reply("Registration complete!")

    @commands.cooldown(1, 80, commands.BucketType.user)
    @commands.hybrid_command(name="recruit", with_app_command=True, description="Generate a list of nations to recruit")
    @app_commands.guilds(bot.config.data.guild)
    async def recruit(self, ctx: commands.Context):
        await ctx.defer()

        user = self.bot.rusers.get(ctx.author.id)

        if not user:
            await ctx.reply("You need to register before you can recruit! Use /register")
            return

        nations = self.bot.queue.get_nations()

        if not nations:
            await ctx.reply("There are no nations to recruit at the moment!")
            return

        color = int("2d0001", 16)
        embed = discord.Embed(title=f"Recruit", color=color)
        embed.add_field(name="Nations", value="\n".join(
            [f"https://www.nationstates.net/nation={nation}" for nation in nations]))
        embed.add_field(name="Template",
                        value=f"```{user.template}```", inline=False)
        embed.set_footer(
            text=f"Initiated by {ctx.author} at {datetime.now(timezone.utc)}")

        # link buttons can't be created in a subclassed view, so this is basically
        # an empty view with nothing but an on_timeout method
        view = RecruitButton()
        view.add_item(discord.ui.Button(label="Open Telegram", style=discord.ButtonStyle.link,
                      url=f"https://www.nationstates.net/page=compose_telegram?tgto={','.join(nations)}&message={user.template}"))

        await ctx.reply(embed=embed, view=view)

        self.bot.daily.info(f"{user.nation} {len(nations)}")

    @commands.hybrid_command(name="start", with_app_command=True, description="Start newnation polling")
    @app_commands.guilds(bot.config.data.guild)
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
    @app_commands.guilds(bot.config.data.guild)
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
    @app_commands.guilds(bot.config.data.guild)
    @commands.has_permissions(administrator=True)
    async def purge(self, ctx: commands.Context):
        await ctx.defer()

        self.bot.std.info(f"Queue purge initiated by {ctx.author}")
        self.bot.queue.purge()

        await ctx.reply("Done.")

    @tasks.loop(seconds=bot.config.data.polling_rate)
    async def newnations_polling(self):
        current_time = datetime.now()

        while len(self.request_times) >= self.bot.config.data.period_max:
            elapsed = (current_time - self.request_times[0]).total_seconds()

            if elapsed > self.bot.config.data.period:
                del self.request_times[0]
            else:
                self.bot.std.info(
                    f"Sleeping for {self.bot.config.data.period - elapsed} seconds")
                await asyncio.sleep(self.bot.config.data.period - elapsed)

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

    @tasks.loop(time=bot.config.data.next_report.time)
    async def reporter(self):
        self.bot.std.info("Sending daily report")
        reports_channel = self.bot.get_channel(self.bot.config.data.report_channel_id)

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
    await bot.add_cog(recruit(bot))

import asyncio
# from functools import wraps
import os

import discord
import requests

from bs4 import BeautifulSoup as bs
from datetime import datetime, time
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks
from components.bot import RecruitBot

from components.config.config_manager import configInstance
from components.users import User
from components.checks import recruit_command_validated, register_command_validated
from components.recruitment import RecruitType, get_recruit_embed


# def guilds_wrapper(f):
#     @wraps(f)
#     def _impl(self, *method_args, **method_kwargs):
#         print(self)
#         app_commands.guilds(configInstance.data.guild)
#         return f(*method_args, **method_kwargs)
#     return _impl


# def loop_rate_wrapper(f):
#     @wraps(f)
#     def _impl(self, *method_args, **method_kwargs):
#         tasks.loop(seconds=configInstance.data.polling_rate)
#         return f(*method_args, **method_kwargs)
#     return _impl


class Recruit(commands.Cog):
    bot: RecruitBot

    def __init__(self, bot: RecruitBot):
        self.bot = bot
        self.request_times: list[datetime] = []

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.newnations_polling.is_running():
            self.bot.std.info("Starting newnations polling")
            self.newnations_polling.start()
            self.bot.std.info("Starting reporting")
            self.reporter.start()

    async def update_status(self):
        self.bot.std.info("Updating Status Embed")
        channel: discord.TextChannel = self.bot.get_channel(configInstance.data.recruit_channel_id)
        message = await channel.fetch_message(configInstance.data.status_message_id)

        embed_data = message.embeds[0].to_dict()

        embed_data["fields"][0]["value"] = str(self.bot.queue.get_nation_count())
        embed_data["fields"][1]["value"] = f"<t:{int(self.bot.queue.last_update.timestamp())}:R>"

        embed = discord.Embed.from_dict(embed_data)
        await message.edit(embed=embed)

    @commands.hybrid_command(name="status_init", with_app_command=True, description="Initialize the status message")
    @commands.has_role(configInstance.data.manager_role_id)
    @app_commands.guilds(configInstance.data.guild)
    async def status_init(self, ctx: commands.Context):
        await ctx.defer()

        embed = discord.Embed(title="Recruitment Status", description="Current recruitment status")
        embed.add_field(name="Nations in Queue", value=self.bot.queue.get_nation_count())
        embed.add_field(name="Last Update", value=f"<t:{int(self.bot.queue.last_update.timestamp())}:R>")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="register", with_app_command=True,
                             description="Register a nation and telegram template")
    @commands.has_role(configInstance.data.recruiter_role_id)
    @app_commands.guilds(configInstance.data.guild)
    async def register(self, ctx: commands.Context, nation: str, template: str):
        await ctx.defer()

        register_command_validated(ctx=ctx)

        new_user = User(
            ctx.author.id, nation.lower().replace(" ", "_"), template.replace("%", ""))

        self.bot.rusers.add(new_user)
        self.bot.std.info(
            f"Registering user: {new_user.id} with nation: {new_user.nation} and template: {new_user.template}")

        await ctx.reply("Registration complete!")

    @commands.hybrid_command(name="recruit", with_app_command=True, description="Generate a list of nations to recruit")
    @commands.has_role(configInstance.data.recruiter_role_id)
    @app_commands.guilds(configInstance.data.guild)
    async def recruit(self, ctx: commands.Context):
        await ctx.defer()

        recruit_command_validated(users=self.bot.rusers, ctx=ctx)

        response_tuple = get_recruit_embed(user=ctx.author, bot=self.bot, rtype=RecruitType.COMMAND)

        if response_tuple:
            embed, view = response_tuple
            view.message = await ctx.reply(embed=embed, view=view)
            await self.update_status()
        else:
            await ctx.reply("No nations in the queue at the moment!")

    @commands.hybrid_command(name="polling", with_app_command=True, description="Start or stop newnation polling")
    @commands.has_role(configInstance.data.manager_role_id)
    @app_commands.guilds(configInstance.data.guild)
    @app_commands.choices(
        action=[
            Choice(name="start", value="start"),
            Choice(name="stop", value="stop")
        ]
    )
    async def polling(self, ctx: commands.Context, action: str):
        await ctx.defer()

        if action == "start":
            if self.newnations_polling.is_running():
                await ctx.reply("Polling already started.")
            else:
                self.bot.std.info(f"Newnations polling initiated by {ctx.author}")
                self.newnations_polling.start()
                await ctx.reply("Polling started.")
        elif action == "stop":
            if not self.newnations_polling.is_running():
                await ctx.reply("Polling already stopped.")
            else:
                self.bot.std.info(f"Newnations polling stopped by {ctx.author}")
                self.newnations_polling.cancel()
                await ctx.reply("Polling stopped.")

    @commands.hybrid_command(name="purge", with_app_command=True, description="Clear queue")
    @commands.has_role(configInstance.data.manager_role_id)
    @app_commands.guilds(configInstance.data.guild)
    async def purge(self, ctx: commands.Context):
        await ctx.defer()

        self.bot.std.info(f"Queue purge initiated by {ctx.author}")
        self.bot.queue.purge()

        await ctx.reply("Done.")

    @tasks.loop(seconds=configInstance.data.polling_rate)
    async def newnations_polling(self):
        current_time = datetime.now()

        while len(self.request_times) >= configInstance.data.period_max:
            elapsed = (current_time - self.request_times[0]).total_seconds()  # type: ignore

            if elapsed > configInstance.data.period:
                del self.request_times[0]
            else:
                self.bot.std.info(f"Sleeping for {configInstance.data.period - elapsed} seconds")
                await asyncio.sleep(configInstance.data.period - elapsed)

        self.request_times.append(current_time)

        headers = {
            "User-Agent": f"Euro Recruitment Bot, developed by upcnationstates@gmail.com, used by {configInstance.data.operator}"}

        try:
            self.bot.std.info("Polling NEWNATIONS shard.")

            new_nations = bs(
                requests.get("https://www.nationstates.net/cgi-bin/api.cgi?q=newnations", headers=headers).text,
                "xml").NEWNATIONS.text.split(",")  # type: ignore -- BeautifulSoup returns a variant type.
        except:
            # certified error handling moment
            self.bot.std.error("An unspecified error occurred while trying to reach the NS API")
        else:
            self.bot.queue.update(new_nations)
            await self.update_status()

    @tasks.loop(time=time(hour=23, minute=58))
    async def reporter(self):
        self.bot.std.info("Sending daily report")
        reports_channel = self.bot.get_channel(configInstance.data.report_channel_id)

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

        if reports_channel is not None:
            await reports_channel.send(f"Daily Report: {date}\n```{summary}```")  # type: ignore


async def setup(bot):
    await bot.add_cog(Recruit(bot))

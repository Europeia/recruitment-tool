import logging

import discord

from discord.ext import commands

from components.config.config_manager import configInstance
from components.loggers import create_loggers
from components.users import Users
from components.rqueue import Queue


class RecruitBot(commands.Bot):
    rusers: Users
    queue: Queue
    daily: logging.Logger
    std: logging.Logger
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        # there is already a users prop for the bot obj, so our custom one will be rusers /shrug
        self.rusers = Users().from_file()
        self.queue = Queue()
        self.daily, self.std = create_loggers()
        configInstance.set_logger(self.std)

        self.default_cogs = ["base", "error", "recruit"]

    async def setup_hook(self):
        # await self.load_extension("recruit")
        # self.std.info("Loaded recruitment cog")

        for cog in self.default_cogs:
            await self.load_extension(f"cogs.{cog}")
            self.std.info(f"Loaded {cog} cog")

        # technically syncing in the setup hook isn't a best practice, but I think that
        # it's fine for a small bot like this
        await self.tree.sync(guild=configInstance.data.guild)
        self.std.info(f"Synced slash commands for {self.user}")

    def run(self):
        super().run(configInstance.data.bot_token)
        return
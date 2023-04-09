from discord import app_commands
from discord.ext import commands
import discord
import logging
import os

from dotenv import load_dotenv

from config.config import Config
from loggers import create_loggers
from users import Users
from rqueue import Queue

load_dotenv()

# you can add a config.TOKEN value if you want, that is probably easier
# than having a separate .env for just that value, I just did not want
# to do that because I am committing my config.py to Github.
TOKEN = os.getenv("DISCORD_TOKEN")

daily: logging.Logger
std: logging.Logger

daily, std = create_loggers()


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        # there is already a users prop for the bot obj, so our custom one will be rusers /shrug
        self.rusers = Users().from_file()
        self.queue = Queue()

        # terrible name ik
        self.std = std
        self.daily = daily

        self.config = Config()

        self.operator = self.config.data.operator

    async def setup_hook(self):
        await self.load_extension("recruit")
        self.std.info("Loaded recruitment cog")

        # technically syncing in the setup hook isn't a best practice, but I think that
        # it's fine for a small bot like this
        await self.tree.sync(guild=self.config.data.guild)
        self.std.info(f"Synced slash commands for {self.user}")

    async def on_command_error(self, ctx, error):
        # this is what we call professional error handling
        self.std.error(
            f"{ctx.author} generated the following error on command invocation: {error}")
        await ctx.reply(error, ephemeral=True)


bot = Bot()


@bot.hybrid_command(name="reload", with_app_command=True, description="Reload recruitment cog")
@app_commands.guilds(bot.config.data.guild)
@commands.has_permissions(administrator=True)
async def reload(ctx: commands.Context):
    await ctx.defer()

    await bot.reload_extension("recruit")
    std.info("Reloaded recruitment cog")

    await ctx.reply("Reloaded cog!")


@bot.hybrid_command(name="sync", with_app_command=True, description="Sync slash commands")
@app_commands.guilds(bot.config.data.guild)
@commands.has_permissions(administrator=True)
async def sync(ctx: commands.Context):
    await ctx.defer()

    await bot.tree.sync(guild=bot.config.data.guild)
    bot.std.info(f"Synced slash commands for {bot.user}")

    await ctx.reply("Done!")


@bot.hybrid_command(name="kill", with_app_command=True, description="Put the bot to sleep")
@app_commands.guilds(bot.config.data.guild)
@commands.has_permissions(administrator=True)
async def kill(ctx: commands.Context):
    await ctx.defer()

    await ctx.reply("Goodbye!")
    bot.std.info(f"Bot shutdown initiated by {ctx.author}")
    await bot.close()


bot.run(TOKEN)

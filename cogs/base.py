# from functools import wraps
from discord import app_commands, guild
import discord
from discord.ext import commands

from components.bot import RecruitBot
from components.config.config_manager import configInstance
from components.config.config_model import ConfigKeys
from components.utils import Utils

class Base(commands.Cog):
    def __init__(self, bot: RecruitBot):
        self.bot = bot

    @commands.hybrid_command(name="reload", with_app_command=True, description="Reload recruitment cog")
    @app_commands.guilds(configInstance.data.guild)
    @commands.has_permissions(administrator=True)
    async def reload(self, ctx: commands.Context, extension: str):
        await ctx.defer()

        if extension not in self.bot.default_cogs:
            await ctx.reply("That is not a valid extension.")
            return

        await self.bot.reload_extension(f"cogs.{extension}")
        self.bot.std.info(f"Reloaded {extension} cog")

        await ctx.reply("Reloaded cog!")

    @commands.hybrid_command(name="sync", with_app_command=True, description="Sync slash commands")
    @app_commands.guilds(configInstance.data.guild)
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx: commands.Context):
        await ctx.defer()

        await self.bot.tree.sync(guild=configInstance.data.guild)
        self.bot.std.info(f"Synced slash commands for {self.bot.user}")

        await ctx.reply("Done!")

    @commands.hybrid_command(name="kill", with_app_command=True, description="Put the bot to sleep")
    @app_commands.guilds(configInstance.data.guild)
    @commands.has_permissions(administrator=True)
    async def kill(self, ctx: commands.Context):
        await ctx.defer()

        await ctx.reply("Goodbye!")
        self.bot.std.info(f"Bot shutdown initiated by {ctx.author}")
        await self.bot.close()

    @commands.hybrid_command(name="config", with_app_command=True, description="Set Config Values")
    @app_commands.guilds(configInstance.data.guild)
    @commands.has_permissions(administrator=True)
    async def config(self, ctx: commands.Context, setting: str, value: str):
        assert ctx.guild is not None

        match setting.lower():
            case "reportchannelid":
                vars = Utils.TryParseInt(value)
                if not vars[0]:
                    await ctx.reply("ERROR: Value must be a number!")
                    return

                channel = ctx.guild.get_channel(vars[1])
                if channel is None:
                    await ctx.reply("ERROR: Value must be the ID of a valid channel!")
                    return

                config_data = configInstance.data.to_dict()
                config_data[ConfigKeys.reportChannelIdKeyId] = vars[1]
                configInstance.writeConfig(config_data)
                await ctx.reply("Updated!")
                return
            
            case "recruitchannelid":
                vars = Utils.TryParseInt(value)
                if not vars[0]:
                    await ctx.reply("ERROR: Value must be a number!")
                    return

                channel = ctx.guild.get_channel(vars[1])
                if channel is None:
                    await ctx.reply("ERROR: Value must be the ID of a valid channel!")
                    return

                config_data = configInstance.data.to_dict()
                config_data[ConfigKeys.recruitChannelIdKeyId] = vars[1]
                configInstance.writeConfig(config_data)
                await ctx.reply("Updated!")
                return
            
            case "recruitroleid":
                vars = Utils.TryParseInt(value)
                if not vars[0]:
                    await ctx.reply("ERROR: Value must be a number!")
                    return

                role = ctx.guild.get_role(vars[1])
                if role is None:
                    await ctx.reply("ERROR: Value must be a valid Role Id!")
                    return

                config_data = configInstance.data.to_dict()
                config_data[ConfigKeys.recruitRoleIdKeyId] = vars[1]
                configInstance.writeConfig(config_data)
                await ctx.reply("Updated!")
                return
            
            case "recruitroleid":
                vars = Utils.TryParseInt(value)
                
            
            case "statusmessageid":
                vars = Utils.TryParseInt(value)
                if not vars[0]:
                    await ctx.reply("ERROR: Value must be a number!")
                    return

                channel = self.bot.get_channel(configInstance.data.recruit_channel_id)
                if channel is None or not isinstance(channel, discord.TextChannel):
                    await ctx.reply("ERROR: Invalid Recruiting Channel, please set that first.")
                    return

                message = await channel.fetch_message(vars[1])
                if message is None:
                    await ctx.reply(f"ERROR: Cannot find message ${vars[1]} in ${channel.name}!")
                    return

                config_data = configInstance.data.to_dict()
                config_data[ConfigKeys.statusMessageIdKeyId] = vars[1]
                configInstance.writeConfig(config_data)
                await ctx.reply("Updated!")
                return
            
            case "pollingrate":
                vars = Utils.TryParseInt(value)
                if not vars[0]:
                    await ctx.reply("ERROR: Value must be a number!")
                    return

                if vars[1] < 0:
                    await ctx.reply("ERROR: Value cannot be a negative number")
                    return

                config_data = configInstance.data.to_dict()
                config_data[ConfigKeys.pollingRateKeyId] = vars[1]
                configInstance.writeConfig(config_data)
                await ctx.reply("Updated!")
                return
            
            case "period":
                vars = Utils.TryParseInt(value)
                if not vars[0]:
                    await ctx.reply("ERROR: Value must be a number!")
                    return

                if vars[1] < 0:
                    await ctx.reply("ERROR: Value cannot be a negative number")
                    return

                config_data = configInstance.data.to_dict()
                config_data[ConfigKeys.periodKeyId] = vars[1]
                configInstance.writeConfig(config_data)
                await ctx.reply("Updated!")
                return
            
            case "periodmax":
                vars = Utils.TryParseInt(value)
                if not vars[0]:
                    await ctx.reply("ERROR: Value must be a number!")
                    return

                if vars[1] < 0:
                    await ctx.reply("ERROR: Value cannot be a negative number")
                    return

                config_data = configInstance.data.to_dict()
                config_data[ConfigKeys.periodMaxKeyId] = vars[1]
                configInstance.writeConfig(config_data)
                await ctx.reply("Updated!")
                return
            
            case _:
                await ctx.reply("Invalid Setting! Valid Settings: reportchannelid, recruitchannelid, recruitroleid, statusmessageid, pollingrate, period, periodmax")
                return

async def setup(bot: RecruitBot):
    await bot.add_cog(Base(bot))

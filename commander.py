from datetime import datetime

import discord
import asyncio

from discord import app_commands
from discord.app_commands import commands

import config
from recruit import recruit


class commander(commands.Cog):

    # Command to define a user's nation & template
    @commands.hybrid_command(name="register", with_app_command=True,
                             description="Register a nation and telegram template")
    @app_commands.guilds(config.SERVER)
    async def register(self, ctx: commands.Context, nation: str, template: str):
        await ctx.defer()

        # Standard validations
        self.recruitCommandValidated(self, ctx)

        # Attempt to register; print if successful
        if recruit.register(self, ctx, nation, template):
            await ctx.reply("Registration complete!")

    # Command to generate a single list of nations
    @commands.cooldown(1, 80, commands.BucketType.user)
    @commands.hybrid_command(name="recruit", with_app_command=True, description="Generate a list of nations to recruit")
    @app_commands.guilds(config.SERVER)
    async def recruit(self, ctx: commands.Context):
        await ctx.defer()

        # Standard validations
        if not self.recruitCommandValidated(self, ctx) or not self.isRegistered():
            return

        # Attempt to print nation list; print warning if failure
        if not recruit.recruit(self, ctx):
            await ctx.reply("There are no nations to recruit at the moment!")
            return

    # Command to start the bot updating the queue
    @commands.hybrid_command(name="start", with_app_command=True, description="Start newnation polling")
    @app_commands.guilds(config.SERVER)
    @commands.has_permissions(administrator=True)
    async def start(self, ctx: commands.Context):
        await ctx.defer()

        # Standard validations
        if not self.inRecruitChannel(self, ctx):
            return

        # Attempt to start polling, print result
        if recruit.start(self, ctx):
            await ctx.reply("Polling started.")
        else:
            await ctx.reply("Could not start polling (already started?).")

    # Command to stop the bot updating the queue
    @commands.hybrid_command(name="stop", with_app_command=True, description="Stop newnation polling")
    @app_commands.guilds(config.SERVER)
    @commands.has_permissions(administrator=True)
    async def stop(self, ctx: commands.Context):
        await ctx.defer()

        # Standard validations
        if not (self.inRecruitChannel(self, ctx)):
            return

        # Attempt to stop pulling, print result
        if recruit.stop(self, ctx):
            await ctx.reply("Polling stopped.")
        else:
            await ctx.reply("Could not start polling (already stopped?).")

    # Check if user has correct role & channel for recruitment command
    async def recruitCommandValidated(self, ctx: commands.Context):

        return self.isRecruiter() and self.inRecruitChannel()

    # Validate if user has the correct role
    async def isRecruiter(self, ctx: commands.Context):

        if ctx.guild.get_role(config.RECRUIT_ROLE_ID) not in ctx.author.roles:
            await ctx.reply("You need the 'recruiter' role to perform this command")
            return False

        return True

    # Validate if user is in the correct channel
    async def inRecruitChannel(self, ctx: commands.Context):

        if ctx.channel.id != config.RECRUIT_CHANNEL_ID:
            await ctx.reply("This command can't be executed in this channel")
            return False

        return True

    # Validate if user has registered
    async def isRegistered(self, ctx: commands.Context):

        user = self.bot.rusers.get(ctx.author.id)

        if not user:
            await ctx.reply("You need to register before you can recruit! Use /register")
            return False

        return True
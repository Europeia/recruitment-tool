import discord
from discord.ext import commands

from components.bot import Bot
from components.checks import is_global_admin_text


class Base(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="sync", description="Sync slash commands")
    @commands.check(is_global_admin_text)
    async def sync(self, ctx: commands.Context):
        await ctx.defer()

        await self.bot.tree.sync()
        await ctx.reply("Done!")

    @commands.command(name="reload", description="Reload a cog")
    @commands.check(is_global_admin_text)
    async def reload(self, ctx: commands.Context, cog: str):
        await self.bot.reload_extension(f"cogs.{cog}")
        await ctx.reply(f"Reloaded cog: {cog}")

    @commands.command(name="kill", description="Put the bot to sleep")
    @commands.check(is_global_admin_text)
    async def kill(self, ctx: commands.Context):
        await ctx.reply("Goodbye!")
        await self.bot.close()

    @commands.command(name="deregister", description="Deregister a recruitment channel by ID")
    @commands.check(is_global_admin_text)
    async def deregister(self, ctx: commands.Context, channel_id: int):
        message_id = await self.bot.deregister_recruitment_channel(channel_id)

        if message_id is None:
            await ctx.reply(f"Channel {channel_id} is not a registered recruitment channel.")
            return

        # Removes channel from memory; bot.deregister call drops from DB
        self.bot.queue_manager.remove_channel(channel_id)

        channel = await self.bot.resolve_channel(channel_id)
        if channel is not None:
            try:
                message = await channel.fetch_message(message_id)
                await message.delete()
            except discord.NotFound:
                pass
            except discord.HTTPException as e:
                await ctx.reply(
                    f"Deregistered channel {channel_id}, but failed to delete the status embed: {e}"
                )
                return

        await ctx.reply(f"Deregistered channel {channel_id}.")


async def setup(bot: Bot):
    await bot.add_cog(Base(bot))

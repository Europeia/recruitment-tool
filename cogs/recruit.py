import discord
import re

from datetime import datetime, timezone, timedelta
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Modal, View

from components.bot import Bot
from components.errors import WhitelistError, NationNotFound
from components.queue import Nation


class RegisterRecruitmentChannelModal(Modal, title="Register Recruitment Channel"):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    region = discord.ui.TextInput(
        label="Region",
        min_length=1,
        max_length=40,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.is_finished() and self.region.value != '':
            raise ValueError("Region cannot be empty")

        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                region = self.region.value.strip().lower().replace(' ', '_')

                message = await interaction.channel.send(view=RecruitView(self.bot))

                try:
                    await cur.execute(
                        'INSERT INTO recruitment_channels (serverId, channelId, messageId) VALUES (%s, '
                        '%s, %s);',
                        (interaction.guild.id, interaction.channel.id, message.id))

                    await cur.execute('INSERT INTO exceptions (channelId, region) VALUES ('
                                      '(SELECT id FROM recruitment_channels WHERE channelId = %s), %s);',
                                      (interaction.channel.id, region))

                    self.bot.queue_list.add_channel(interaction.channel.id, [region])

                except Exception as e:
                    await message.delete()
                    raise e
                else:
                    await interaction.response.send_message(f'Registered channel for region: {region}',
                                                            ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        print(error)
        await interaction.response.send_message(f'An error occurred:\n\n{error}', ephemeral=True)


class RegisterRecruiterModal(Modal, title="Registration"):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    nation = discord.ui.TextInput(
        label="Nation",
        placeholder="Enter your nation name",
        min_length=3,
        max_length=40,
    )

    recruitment_template = discord.ui.TextInput(
        label="Recruitment Template",
        placeholder="Enter your recruitment template",
        min_length=10,
        max_length=20,
    )

    session_length = discord.ui.TextInput(
        label="Session Length (in seconds)",
        placeholder="Session length (45 - 600 seconds)",
        default='60',
        min_length=1,
        max_length=3,
    )

    async def on_submit(self, interaction: discord.Interaction):
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                nation = self.nation.value.strip().lower().replace(" ", "_")
                template = self.recruitment_template.value.replace("%", "")

                try:
                    session_length = int(self.session_length.value)
                except ValueError:
                    raise Exception("Session length must be a number")

                if session_length < 45 or session_length > 600:
                    raise Exception("Session length must be between 45 and 600 seconds")

                try:
                    founded_time = datetime.fromtimestamp(
                        int((await self.bot.request(
                            f"https://www.nationstates.net/cgi-bin/api.cgi?nation={nation}&q=foundedtime")).find(
                            "FOUNDEDTIME").text))
                except AttributeError:
                    raise NationNotFound(interaction.user, nation)

                recruiter_id = await self.bot.get_recruiter_id(interaction.user, interaction.channel_id)

                if recruiter_id:
                    await cur.execute(
                        'UPDATE users SET nation = %s, recruitTemplate = %s, sessionLength = %s, foundedTime = %s WHERE id = %s;',
                        (nation, template, session_length, founded_time, recruiter_id))
                else:
                    await cur.execute(
                        'INSERT INTO users (discordId, nation, recruitTemplate, sessionLength, foundedTime, '
                        'channelId) VALUES (%s, %s, %s, %s, %s, (SELECT id FROM recruitment_channels WHERE '
                        'channelId = %s));',
                        (
                            interaction.user.id, nation, template, session_length, founded_time, interaction.channel_id
                        )
                    )

                # await conn.commit()
                await interaction.response.send_message("Registration complete!", ephemeral=True, delete_after=10)

    async def on_error(self, interation: discord.Interaction, error: Exception):
        self.bot.std.error(error)
        await interation.response.send_message(f"An error occurred: {error}", ephemeral=True)


class ReportModal(Modal, title="Recruitment Report"):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    start_time = discord.ui.TextInput(
        label="Start Time",
        placeholder="YYYY-MM-DD HH:MM:SS",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        min_length=10,
        max_length=19,
    )

    end_time = discord.ui.TextInput(
        label="End Time",
        placeholder="YYYY-MM-DD HH:MM:SS",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        min_length=10,
        max_length=19,
    )

    async def on_submit(self, interaction: discord.Interaction):
        start_time = datetime.fromisoformat(self.start_time.value).replace(tzinfo=timezone.utc)
        end_time = datetime.fromisoformat(self.end_time.value).replace(tzinfo=timezone.utc)

        result = await self.bot.get_telegrams(start_time, end_time, interaction.channel_id)

        resp = "\n".join([f"{nation}: {count}" for nation, count in result])
        await interaction.response.send_message(
            f"Recruitment Report: <t:{int(start_time.timestamp())}:f> to <t:{int(end_time.timestamp())}:f>\n```{resp}```",
            ephemeral=True
        )

    async def on_error(self, interation: discord.Interaction, error: Exception):
        self.bot.std.error(error)
        await interation.response.send_message(f"An error occurred: {error}", ephemeral=True)


class RecruitView(View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label='Recruit', style=discord.ButtonStyle.blurple, custom_id='recruitment_view:recruit')
    async def recruit(self, interaction: discord.Interaction, _button: discord.ui.button):
        embed, view, delete_after = await self.bot.create_recruitment_response(interaction.user, interaction.channel_id)
        view.message = await interaction.response.send_message(embed=embed, view=view, ephemeral=True,
                                                               delete_after=3 + delete_after)
        await self.bot.update_status_embeds(interaction.channel_id)

    @discord.ui.button(label='Register', style=discord.ButtonStyle.blurple, custom_id='recruitment_view:register')
    async def register(self, interaction: discord.Interaction, _button: discord.ui.button):
        await interaction.response.send_modal(RegisterRecruiterModal(self.bot))

    @discord.ui.button(label='Report', style=discord.ButtonStyle.blurple, custom_id='recruitment_view:report')
    async def report(self, interaction: discord.Interaction, _button: discord.ui.button):
        await interaction.response.send_modal(ReportModal(self.bot))

    async def on_error(self, interaction: discord.Interaction, error: Exception, _item: discord.ui.Item):
        self.bot.std.error(error)
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)


class TelegramView(View):
    message: discord.Message

    def __init__(self, cooldown: int):
        super().__init__(timeout=3 + cooldown)

    async def on_timeout(self):
        if self.message:
            await self.message.edit(view=None)
        self.stop()


class RecruitmentCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.pattern = re.compile(r'^\d+_|_\d+$')

    @app_commands.command(name='register', description='Register a channel for recruitment')
    @commands.has_permissions(administrator=True)
    async def register_recruitment_channel(self, interaction: discord.Interaction):
        async with self.bot.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('SELECT id FROM whitelist WHERE serverId = %s;', (interaction.guild.id,))

                if not await cur.fetchone():
                    raise WhitelistError(interaction.user, interaction.guild)

        await interaction.response.send_modal(RegisterRecruitmentChannelModal(self.bot))

    @app_commands.command(name='whitelist', description='Modify this channel\'s recruitment whitelist')
    @commands.has_permissions(administrator=True)
    @app_commands.choices(action=[
        app_commands.Choice(name='add', value='add'),
        app_commands.Choice(name='remove', value='remove'),
        app_commands.Choice(name='list', value='list'),
    ])
    async def whitelist(self, interaction: discord.Interaction, action: str, region: str = None):
        if action == 'add':
            if not region:
                raise ValueError("Region cannot be empty")
            else:
                region = region.strip().lower().replace(' ', '_')

            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """INSERT INTO exceptions (channelId, region) VALUES (
                            (SELECT id FROM recruitment_channels WHERE channelId = %s), %s
                        );""",
                        (interaction.channel.id, region)
                    )

                    self.bot.queue_list.channel(interaction.channel.id).add_to_whitelist(region)

                    await interaction.response.send_message(f'Added region {region} to whitelist', ephemeral=True)

        elif action == 'remove':
            if not region:
                raise ValueError("Region cannot be empty")
            else:
                region = region.strip().lower().replace(' ', '_')

            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """DELETE FROM exceptions WHERE region = %s AND channelId = (
                            SELECT id FROM recruitment_channels WHERE channelId = %s
                        );""",
                        (region, interaction.channel.id)
                    )

                    self.bot.queue_list.channel(interaction.channel.id).remove_from_whitelist(region)

                    await interaction.response.send_message(f'Removed region {region} from whitelist', ephemeral=True)

        elif action == 'list':
            regions = '\n'.join(self.bot.queue_list.channel(interaction.channel.id).whitelist)

            await interaction.response.send_message(f'Whitelisted regions: \n{regions}', ephemeral=True)

    @tasks.loop(seconds=15)
    async def update_loop(self):
        try:
            await self.update_queue()
        except Exception as e:
            self.bot.std.error(f"Error in update_loop: {e}")

    async def update_queue(self):
        self.bot.std.info("Updating queue")

        new_nations = await self.bot.request("https://www.nationstates.net/cgi-bin/api.cgi?q=newnationdetails")

        nations = []

        for raw_nation in reversed(new_nations.find_all('NEWNATION')):
            nation_name = raw_nation.attrs['name']

            if not self.pattern.search(nation_name) \
                    and int(raw_nation.FOUNDEDTIME.text) > self.bot.queue_list.last_update.timestamp():
                nations.append(
                    Nation(
                        name=raw_nation.attrs['name'],
                        region=raw_nation.REGION.text,
                        founding_time=datetime.fromtimestamp(int(raw_nation.FOUNDEDTIME.text), timezone.utc)
                    )
                )

        self.bot.queue_list.update(nations)
        await self.bot.update_status_embeds()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.update_loop.is_running():
            self.bot.std.info("Starting update loop")
            self.update_loop.start()

    @commands.Cog.listener()
    async def on_cog_load(self):
        if not self.update_loop.is_running():
            self.bot.std.info("Starting update loop")
            self.update_loop.start()

    @commands.Cog.listener()
    async def on_cog_unload(self):
        if self.update_loop.is_running():
            self.bot.std.info("Stopping update loop")
            self.update_loop.stop()


async def setup(bot: Bot):
    await bot.add_cog(RecruitmentCog(bot))

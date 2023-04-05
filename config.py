import discord
from datetime import time, timezone

# the user running the bot, used for the NS API user agent
OPERATOR = "The United Peoples of Centrism"
# the server that the bot is in, for syncing app commands
SERVER = discord.Object(id=1084622726800605184)
# the role ID for the recruitment role
RECRUIT_ROLE_ID = 1088807857442537654
# the channel ID for the reports channel
REPORT_CHANNEL_ID = 1088812851738722334
# the rate at which the bot will poll the NEWNATIONS API shard (in seconds)
POLLING_RATE = 15
# the NS API's bucket length. don't change this
PERIOD = 30
# the maximum requests that the bot will make to the NS API in PERIOD seconds
PERIOD_MAX = 5
# the time (UTC) at which the bot will generate daily reports
START_TIME = time(hour=23, minute=58, tzinfo=timezone.utc)

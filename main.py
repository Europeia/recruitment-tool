from components.bot import RecruitBot
from components.config.config_manager import configInstance

# We do this first, just to make sure it's there.
configInstance.readConfig()

bot = RecruitBot()

bot.run()

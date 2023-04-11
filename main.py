import config
from components.bot import RecruitBot

bot = RecruitBot()

bot.run(config.TOKEN)

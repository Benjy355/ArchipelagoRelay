import main
import logging
from include.discord_oauth import DISCORD_TOKEN

main.main_bot.run(DISCORD_TOKEN, log_level=logging.WARN)
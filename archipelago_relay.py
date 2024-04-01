import Config
import discord
from discord import app_commands
from discord_oauth import DISCORD_TOKEN

from chat_handler import chat_handler

class archi_relay:
    _bot = None # Discord client
    _channel = None # Channel where messages are relayed to
    _multiworld_link = None # Example: https://archipelago.gg/room/4_hWRGK1RPiG3wYFQTXImA

    _chat_handler = None

    def __init__(self, bot_client: discord.Client, response_channel: discord.channel.TextChannel, multiworld_link: str):
        self._bot = bot_client
        self._channel = response_channel
        self._multiworld_link = multiworld_link

        self._chat_handler = chat_handler(self._bot)
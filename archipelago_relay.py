import Config
import discord
from discord import app_commands
from discord_oauth import DISCORD_TOKEN

from archipelago_site_scraping import archipelago_site_data, get_site_data

from chat_handler import chat_handler

class FailedToStart(Exception):
    reason: str = "Undefined"
    def __init__(self, reason: str = "Undefined"):
        self.reason = reason
        super().__init__(self)

class archi_relay:
    _bot: discord.Client = None # Discord client
    _channel: discord.TextChannel = None # Channel where messages are relayed to
    _thread: discord.Thread = None # Thread where messages are relayed to (overrides _channel) *NOT YET IMPLEMENTED*
    _multiworld_link: str = None # Example: https://archipelago.gg/room/4_hWRGK1RPiG3wYFQTXImA
    _multiworld_site_data: archipelago_site_data = None


    _deathlink_relays = None # List of relays that are also connected (as other players), but we only care about deathlink messages from them
    _chat_handler: chat_handler = None

    async def __init__(self, bot_client: discord.Client, response_channel: discord.channel.TextChannel, multiworld_link: str, chat_handler_obj: chat_handler):
        self._bot = bot_client
        self._channel = response_channel
        self._thread = None
        self._multiworld_link = multiworld_link
        try:
            self._multiworld_site_data = await get_site_data(multiworld_link)
        except:
            raise FailedToStart("Failed to get multiworld site data!")

        self._deathlink_relays = None

        self._chat_handler = chat_handler_obj


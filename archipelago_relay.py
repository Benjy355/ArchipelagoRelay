import Config
import websockets
import discord
import asyncio
from archipelago_common import *
import sys
import os

import logging
logger = logging.getLogger(__name__)

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
    _chat_handler: chat_handler = None

    _deathlink_relays = None # List of relays that are also connected (as other players), but we only care about deathlink messages from them
    
    _socket: websockets.connect = None

    _pending_payloads: list[str] = []

    _continue = True # Keep loops active

    _incoming_data_loop: asyncio.Task = None
    _outgoing_data_loop: asyncio.Task = None

    def connection_url(self) -> str:
        return "wss://archipelago.gg:" + self._multiworld_site_data.port
    
    # Handle incoming data from Archipelago
    async def handle_response(self, response: str):
        pass
    
    async def send_data_loop(self):
        while self._continue:
            try:
                if (len(self._pending_payloads) > 0):
                    log_txt = "\nSEND:\n"
                    for p in self._pending_payloads:
                        log_txt += p + "\n"
                    logging.debug(log_txt)
                    await self._socket.send(self._pending_payloads)
                    self._pending_payloads = []
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error(exc_type, fname, exc_tb.tb_lineno)
                logging.error(e)
                self._continue = False
    
    async def receive_data_loop(self):
        while self._continue:
            try:
                async for data in self._socket:
                    decoded = decode(data)
                    for response in decoded:
                        logging.debug("\nRECEIVE:\n" + str(response))
                        await self.handle_response(response)
            except websockets.exceptions.ConnectionClosedError as e:
                await self._chat_handler.add_message("I've been disconnected from Archipelago")
                self._continue = False
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error(exc_type, fname, exc_tb.tb_lineno)
                logging.error(e)
                self._continue = False

    async def main_loop(self):
        try:
            self._socket = await websockets.connect(uri=self.connection_url, ping_interval=None, ping_timeout=None, ssl=get_ssl_context())
            self._incoming_data_loop = asyncio.create_task(coro=self.receive_data_loop(), name="INC_%s" % self._multiworld_site_data.game_id)
            self._outgoing_data_loop = asyncio.create_task(coro=self.send_data_loop(), name="OUT_%s" % self._multiworld_site_data.game_id)
        except ConnectionRefusedError:
            await self._chat_handler.add_message("Failed to connect to game *%s*! Connection refused." % self._multiworld_site_data.game_id)
        except websockets.ConnectionClosed:
            logging.info("Disconnected from game %s" % self._multiworld_site_data.game_id)


    async def __init__(self, bot_client: discord.Client, response_channel: discord.channel.TextChannel, multiworld_link: str, chat_handler_obj: chat_handler):
        self._bot = bot_client
        self._channel = response_channel
        self._thread = None
        self._multiworld_link = multiworld_link
        self._continue = True
        try:
            self._multiworld_site_data = get_site_data(multiworld_link)
        except:
            raise FailedToStart(reason="Failed to get multiworld site data!")
        
        if (self._multiworld_site_data == None):
            raise FailedToStart(reason="Multiworld data returned 'None'")
        
        self._deathlink_relays = None
        self._chat_handler = chat_handler_obj






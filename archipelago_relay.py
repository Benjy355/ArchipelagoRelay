import Config
import websockets
import discord
import asyncio
from archipelago_common import *
import sys
import os
import game_cache

import logging
logger = logging.getLogger(__name__)

from archipelago_site_scraping import *

from chat_handler import chat_handler, chat_message

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
    _password = None

    _deathlink_relays = None # List of relays that are also connected (as other players), but we only care about deathlink messages from them
    
    _socket: websockets.connect = None

    _pending_payloads: list[str] = []

    _continue = True # Keep loops active

    _incoming_data_loop: asyncio.Task = None
    _outgoing_data_loop: asyncio.Task = None

    _archi_slot_players = [] # Slot info from the players as the archipelago server states (not the site) (Do we even need to store this)
    _archi_players = [] # Player info from Archipelago
    _archi_slot_info = [] # Player slot info from Archi (I know I know; this is sent from the 'Connected' cmd)
    _room_info = {} # Raw packet from when _room_info['data'] would be 'RoomInfo'

    def connection_url(self) -> str:
        return "wss://archipelago.gg:" + self._multiworld_site_data.port
    
    def phantom_player(self) -> archipelago_site_slot_data:
        # Returns the player we plan on pretending to be, this should never be None so we won't bother try/excepting
        return self._multiworld_site_data.players[0]
    
    async def _get_playerName_by_id(self, id: int):
        for player in self.network_players:
            if player.slot == id:
                return player.name
            
    async def _get_playerAlias_by_id(self, id: int):
        for player in self.network_players:
            if player.slot == id:
                return player.alias
            
    async def _get_playerGame_by_id(self, id: int):
        slotName = ""
        pName = await self._get_playerName_by_id(id)
        for slot in self.network_slots:
            if slot.name == pName:
                return slot.game
            
    async def _get_itemName_by_id(self, id: int, playerId: int):
        game = await self._get_playerGame_by_id(playerId)
        item_name = self.game_data[game]['item_id_to_name'][int(id)]
        return item_name
    
    async def _get_locationName_by_id(self, id: int, playerId: int):
        game = await self._get_playerGame_by_id(playerId)
        loc_name = self.game_data[game]['location_id_to_name'][int(id)]
        return loc_name
    
    def get_archi_game_version(self, game:str) -> int:
        return int(self._room_info['datapackage_versions'][game])
    
    def append_payload(self, payload):
        self._pending_payloads.append(encode([payload]))
    
    async def handle_print_json(self, json: dict): # This has not been re-written yet since v1...
        try:
            final_text = ""
            for node in json:
                # If there is no 'type' it is just normal text
                if not "type" in node:
                    final_text += node['text']
                elif node['type'] == "player_id":
                    playerName = await self._get_playerAlias_by_id(int(node['text']))
                    final_text += "**%s**" % playerName
                elif node['type'] == "item_id":
                    #We only care if it's useful or progression
                    if node['flags'] & 0b001 or node['flags'] & 0b010 or node['flags'] & 0b100:
                        if node['flags'] & 0b001: #Progression
                            final_text += "**%s**" % await self._get_itemName_by_id(int(node['text']), int(node['player']))
                        elif node['flags'] & 0b010: #Useful
                            final_text += "*%s*" % await self._get_itemName_by_id(int(node['text']), int(node['player']))
                        else:
                            final_text += "<:Duc:1084164152681037845><:KerZ:1084164151317889034> %s" % await self._get_itemName_by_id(int(node['text']), int(node['player']))
                    else:
                        #Don't bother.
                        return
                elif node['type'] == "location_id":
                    final_text += await self._get_locationName_by_id(int(node['text']), int(node['player']))

            await self._chat_handler.add_message(chat_message(final_text, self._channel))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logging.error([exc_type, fname, exc_tb.tb_lineno])
            logging.error(e)

    # Handle incoming data from Archipelago
    async def handle_response(self, data: str):
        try:
            cmd = data['cmd']
        except:
            logging.error("Invalid response from Archipelago; failed to find 'cmd' in response.")
            return
        
        if (cmd == 'RoomInfo'):
            if ("players" in data):
                self._archi_slot_players = data.get("players", [])
            
            self._room_info = data
            phantom_player = self.phantom_player()
            await self._chat_handler.add_message(chat_message("Connecting to server! I will imitate %s playing %s." % (phantom_player.name, phantom_player.game), self._channel))
            # Connect as a user now that we have RoomInfo
            payload = {
                'cmd': 'Connect',
                'password': self._password, 'name': phantom_player.name, 'version': version_tuple,
                'tags': ['TextOnly', 'AP', 'DeathLink'], 'items_handling': 0b111,
                'uuid': 696942024, 'game': phantom_player.game, "slot_data":False
            }
            self.append_payload(payload)

        elif (cmd == "PrintJSON"):
            await self.handle_print_json(data['data'])
        
        elif (cmd == "Connected"):
            try:
                for p in data["players"]:
                    self._archi_players.append(p)
                for k, s in data["slot_info"].items():
                    self._archi_slot_info.append(s)
                # Get our cache together!
                games = []
                for slot in self._archi_slot_info:
                    if (not slot.game in games):
                        games.append(slot.game)
                
                # Rip out any games where we trust our cache
                for game in games:
                    testVer = self.get_archi_game_version(game)
                    test = game_cache.get_game_cache(game, testVer)
                    if (game_cache.get_game_cache(game, self.get_archi_game_version(game)) != None):
                        games.remove(game)
                if (len(games) > 0):
                    payload = {
                        'cmd': 'GetDataPackage',
                        'games': games
                    }
                    logging.debug("Requesting game data for:")
                    logging.debug(games)
                    self.append_payload(payload)
            except Exception as e:
                logging.error("[handle_response]Failed to read 'players' or 'slot_info' on 'Connected' cmd")
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error("[handle_response]")
                logging.error([exc_type, fname, exc_tb.tb_lineno])
                logging.error(e)

        elif (cmd == "DataPackage"):
            try:
                if ("games" in data['data']):
                    for single_game_name in data['data']['games']:
                        logging.debug("Receiving DataPackage for %s" % single_game_name)
                        game_cache.update_game_cache(single_game_name, data['data']['games'][single_game_name])
            except Exception as e:
                logging.error("[handle_response]Failed to parse DataPackage!")
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error("[handle_response]")
                logging.error([exc_type, fname, exc_tb.tb_lineno])
                logging.error(e)

        elif (cmd == "Bounced"):
            pass # Do Nothing (yet hehe)
        
        else:
            logging.warn("Received unhandled cmd: %s" % cmd)

    async def send_data_loop(self):
        while self._continue:
            try:
                if (len(self._pending_payloads) > 0):
                    logging.debug("\nSENDING:")
                    logging.debug(self._pending_payloads)
                    await self._socket.send(self._pending_payloads)
                    self._pending_payloads = []
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error("[SEND_DATA_LOOP]")
                logging.error([exc_type, fname, exc_tb.tb_lineno])
                logging.error(e)
            await asyncio.sleep(0.1)
    
    async def receive_data_loop(self):
        while self._continue:
            try:
                async for data in self._socket:
                    decoded = decode(data)
                    for response in decoded:
                        logging.debug("\nRECEIVE:" + str(response))
                        await self.handle_response(response)
            except websockets.exceptions.ConnectionClosedError as e:
                await self._chat_handler.add_message(chat_message("I've been disconnected from Archipelago", self._channel))
                logging.warn("[RECEIVE_DATA_LOOP]ConnectionClosedError")
                self._continue = False
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error("[RECEIVE_DATA_LOOP]")
                logging.error([exc_type, fname, exc_tb.tb_lineno])
                logging.error(e)
            await asyncio.sleep(0.1)

    def start(self):
        try:
            logging.debug("Getting site data for game from %s" % self._multiworld_link)
            self._multiworld_site_data = get_site_data(self._multiworld_link)
        except:
            raise FailedToStart(reason="Failed to get multiworld site data!")
        
        if (self._multiworld_site_data == None):
            raise FailedToStart(reason="Multiworld data returned 'None'")
        
        logging.debug("Creating main loop for %s" % self._multiworld_site_data.game_id) # TODO: Can probably just await this.
        asyncio.create_task(coro=self._main_loop(), name="MAIN_LOOP_%s" % self._multiworld_site_data.game_id)

    async def _main_loop(self):
        try:
            self._socket = await websockets.connect(uri=self.connection_url(), ping_interval=None, ping_timeout=None, ssl=get_ssl_context())
            self._incoming_data_loop = asyncio.create_task(coro=self.receive_data_loop(), name="INC_%s" % self._multiworld_site_data.game_id)
            self._outgoing_data_loop = asyncio.create_task(coro=self.send_data_loop(), name="OUT_%s" % self._multiworld_site_data.game_id)
        except ConnectionRefusedError:
            await self._chat_handler.add_message(chat_message("Failed to connect to game *%s*! Connection refused." % self._multiworld_site_data.game_id, self._channel))
        except websockets.ConnectionClosed:
            logging.info("Disconnected from game %s" % self._multiworld_site_data.game_id)
            await self.disconnect()

    def connected(self) -> bool:
        # Returns status of connection
        return (self._socket != None)
    
    async def disconnect(self):
        self._continue = False
        try:
            self._incoming_data_loop.cancel()
        except:
            pass
        try:
            self._outgoing_data_loop.cancel()
        except:
            pass
        self._socket.close()

    def __init__(self, bot_client: discord.Client, response_channel: discord.channel.TextChannel, multiworld_link: str, chat_handler_obj: chat_handler, password: str):
        self._bot = bot_client
        self._channel = response_channel
        self._thread = None
        self._multiworld_link = multiworld_link
        self._continue = True
        
        self._deathlink_relays = None
        self._chat_handler = chat_handler_obj

        self._archi_slot_players = []
        self._archi_players = []
        self._archi_slot_info = []
        self._password = password or ""
        self._room_info = {}
        self._pending_payloads = []





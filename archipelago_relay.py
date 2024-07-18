import include.Config as Config
import websockets
import discord
import asyncio
from include.archipelago_common import *
import sys
import os
import game_cache
import random
import copy
from typing import Union
from archipelago_site_scraping import *

from chat_handler import chat_handler, chat_message
from include.lang import insults

class FailedToStart(Exception):
    reason: str = "Undefined"
    def __init__(self, reason: str = "Undefined"):
        self.reason = reason
        super().__init__(self)

class archi_relay:
    _bot: discord.Client = None # Discord client
    _game_name: str = "" # Auto generated name of the game using 4 words.
    _message_destination: Union[discord.TextChannel, discord.Thread] = None # Channel where messages are relayed to
    _multiworld_link: str = None # Example: https://archipelago.gg/room/4_hWRGK1RPiG3wYFQT...
    _multiworld_site_data: archipelago_site_data = None
    _chat_handler: chat_handler = None
    _password = None
 
    _socket: websockets.connect = None

    _pending_payloads: list[str] = []

    _continue = True # Keep loops active

    _connected_callback = None # Async function called once we are fully connected
    slot_id = None

    _incoming_data_loop: asyncio.Task = None
    _outgoing_data_loop: asyncio.Task = None

    _archi_slot_players = [] # Slot info from the players as the archipelago server states (not the site) (Do we even need to store this)
    _archi_players: list[NetworkPlayer] = [] # Player info from Archipelago
    _archi_retrieved_name_map: dict[str, NetworkPlayer] = {} # Used by the Retreived command to simplify tying a player's game/name to a those goofy _read_hints_0_1 requests
    _archi_player_hints: dict[int, dict] = {} # Key is slot id of *receiving* player. Stores results of _read_hints_0_0 packets as dict
    _archi_player_items: dict[int, list] = {} # Used to store information received from ReceivedItems (ID/int is slot number)
    _archi_slot_info = [] # Player slot info from Archi (I know I know; this is sent from the 'Connected' cmd)
    _room_info = {} # Raw packet from when _room_info['data'] would be 'RoomInfo'

    _json_handler = None

    def connection_url(self) -> str:
        return "wss://archipelago.gg:" + self._multiworld_site_data.port
    
    def phantom_player(self) -> archipelago_site_slot_data:
        # Returns the player we plan on pretending to be, this should never be None so we won't bother try/excepting
        return self._multiworld_site_data.players[self.slot_id]
    
    def _get_playerName_by_id(self, id: int) -> str:
        for player in self._archi_players:
            if player.slot == id:
                return player.name
        return "Undefined"
    
    def _get_playerData_by_id(self, id: int) -> NetworkPlayer:
        for player in self._archi_players:
            if player.slot == id:
                return player
        return None
            
    def _get_playerAlias_by_id(self, id: int) -> str:
        for player in self._archi_players:
            if player.slot == id:
                return player.alias
        return "Undefined"
            
    def _get_playerGame_by_id(self, id: int) -> str:
        pName = self._get_playerName_by_id(id)
        for slot in self._archi_slot_info:
            if slot.name == pName:
                return slot.game
        return None
            
    def _get_itemName_by_id(self, id: int, playerId: int) -> str:
        try:
            game = self._get_playerGame_by_id(playerId)
            cache = game_cache.get_game_cache(game)['item_id_to_name']
            item_name = cache[int(id)]
        except Exception as e:
            logging.error("Failed to get item name from ID for item %i" % id)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logging.error([exc_type, fname, exc_tb.tb_lineno])
            logging.error(e)
            return "Undefined"
        return item_name
    
    def _get_locationName_by_id(self, id: int, playerId: int) -> str:
        try:
            game = self._get_playerGame_by_id(playerId)
            loc_name = game_cache.get_game_cache(game)['location_id_to_name'][int(id)]
        except Exception as e:
            logging.error("Failed to get location name from ID for location %i" % id)
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logging.error([exc_type, fname, exc_tb.tb_lineno])
            logging.error(e)
            return "Undefined"
        return loc_name

    def get_archi_game_checksum(self, game:str) -> str:
        return self._room_info['datapackage_checksums'][game]
    
    def append_payload(self, payload):
        self._pending_payloads.append(encode([payload]))
    
    async def handle_print_json(self, json: dict):
        try:
            if (self._json_handler == None):
                self._json_handler = json_message_handler(self)
            
            final_text = self._json_handler.convert_json_msg(json)
            if (final_text != None and final_text != ""):
                await self._chat_handler.add_message(chat_message(final_text, self._message_destination)) 
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logging.error([exc_type, fname, exc_tb.tb_lineno])
            logging.error(e)

    # Handle incoming data from Archipelago
    async def handle_response(self, data: dict):
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
            #await self._chat_handler.add_message(chat_message("Connecting to server! I will imitate *everybody*.", self._message_destination))
            # Connect as a user now that we have RoomInfo
            payload = {
                'cmd': 'Connect',
                'password': self._password, 'name': phantom_player.name, 'version': version_tuple,
                'tags': ['TextOnly', 'AP', 'DeathLink'], 'items_handling': 0b111,
                'uuid': 696942024, 'game': phantom_player.game, "slot_data":False
            }
            self.append_payload(payload)

        elif (cmd == "PrintJSON"):
            # We only care about this if we're slot 0, otherwise we only print Hints and Deathlink notifications
            if (self.slot_id == 0 and data['type'] != 'Hint'): # Don't print hints twice (because we still only care if it's FOR us)
                await self.handle_print_json(data)
            else:
                if (data['type'] == 'Hint'):
                    # We only care if it's for us
                    if (int(data['receiving'])-1 == self.slot_id): # 0 INDEX EVERYTHING YOU BASTARDS
                        await self.handle_print_json(data)
        
        elif (cmd == "Connected"):
            try:
                self._archi_players = []
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
                # Note to self, do not dynmamically update THE FUCKING ARRAY YOU ARE FOR X IN YING IN
                requested_games = copy.deepcopy(games)
                for game in games:
                    if (game_cache.get_game_cache(game, self.get_archi_game_checksum(game)) != None):
                        logging.debug("Game_Cache for %s is good" % game)
                        requested_games.remove(game)
                    else:
                        logging.debug("Game_Cache returned None for game %s" % game)
                if (len(requested_games) > 0):
                    payload = {
                        'cmd': 'GetDataPackage',
                        'games': requested_games
                    }
                    logging.info("Requesting game data for:")
                    logging.info(requested_games)
                    self.append_payload(payload)
                
                # Get all of the hints, and let Archipelago know we want notified of hints
                player_hint_request_strings = []
                for player in self._archi_players:
                    req_str = "_read_hints_%s_%s" % (player.team, player.slot)
                    player_hint_request_strings.append(req_str)
                    self._archi_retrieved_name_map[req_str] = player

                payload = {
                    'cmd': 'Get',
                    'keys': player_hint_request_strings
                }
                self.append_payload(payload)

                if (self._connected_callback != None):
                    await self._connected_callback()
                
                # Now that we are fully connected, create our deathlink relays
                """for player in self._multiworld_site_data.players:
                    logging.debug("[handle_response]Creating deathlink relay for user in slot %s (%s)" % (player.id, player.name))
                    new_relay = deathlink_relay(self, int(player.id))
                    await new_relay.start()
                    self._deathlink_relays.append(new_relay)"""

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
            if ('data' in data and 'source' in data['data']):
                global insults
                random_insult = insults[random.randint(0, len(insults)-1)]
                await self._chat_handler.add_message(chat_message("**%s** died! <:Duc:1084164152681037845><:KerZ:1084164151317889034> %s" % (data['data']['source'], random_insult), self._message_destination))

        elif (cmd == "ReceivedItems"):
            for item in data["items"]:
                if (not int(item.player) in self._archi_player_items):
                    self._archi_player_items[int(item.player)] = []
                self._archi_player_items[int(item.player)].append(item)

        elif (cmd == "RoomUpdate"):
            pass #TODO

        elif (cmd == "Retrieved"):
            if (not "keys" in data):
                logging.error("Bad 'Retrieved' result!")
                logging.error(data)
                return
            
            for k, key in data["keys"].items():
                if k in self._archi_retrieved_name_map:
                    for hint in key:
                        if ("class" in hint and hint["class"] == "Hint"):
                            if (hint["receiving_player"] not in self._archi_player_hints):
                                self._archi_player_hints[hint["receiving_player"]] = []
                            if (hint not in self._archi_player_hints[hint["receiving_player"]]): # Ignore duplicates, of course.
                                self._archi_player_hints[hint["receiving_player"]].append(hint)
                        else:
                            logging.error("Expected 'Retrieved' cmd packet")
                            logging.error(hint)
                else:
                    logging.error("Received 'Retrieved' cmd packet for user we don't track?")
                    logging.error(key)
        
        else:
            logging.warn("Received unhandled cmd: %s" % cmd)
            logging.warn(data)

    async def send_data_loop(self):
        while self._continue:
            try:
                if (len(self._pending_payloads) > 0):
                    payload = self._pending_payloads.pop(0)
                    logging.debug("\nSENDING:")
                    logging.debug(payload)
                    await self._socket.send(payload)
                    #self._pending_payloads = []
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error("[SEND_DATA_LOOP]")
                logging.error([exc_type, fname, exc_tb.tb_lineno])
                logging.error(e)
            await asyncio.sleep(0.1)
    
    async def receive_data_loop(self):
        while self._continue:
            if (self._socket == None or self._socket.closed):
                if (self.slot_id == 0):
                    await self._chat_handler.add_message(chat_message("Disconnected from *%s*" % self._multiworld_site_data.game_id, self._message_destination))
                await self.disconnect()
                return
            try:
                async for data in self._socket:
                    decoded = decode(data)
                    for response in decoded:
                        logging.debug("\nRECEIVE:" + str(response))
                        await self.handle_response(response)
            except websockets.exceptions.ConnectionClosedError as e:
                if (self.slot_id == 0):
                    await self._chat_handler.add_message(chat_message("Disconnected from *%s*" % self._multiworld_site_data.game_id, self._message_destination))
                logging.warn("[RECEIVE_DATA_LOOP]ConnectionClosedError")
                await self.disconnect()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error("[RECEIVE_DATA_LOOP]")
                logging.error([exc_type, fname, exc_tb.tb_lineno])
                logging.error(e)
            await asyncio.sleep(0.1)

    # Once fully connected, (when cmd "Connected" is receieved), we will call our 'callback' if it exists.
    def start(self, callback = None):
        try:
            if (self._multiworld_site_data == None):
                logging.debug("Getting site data for game from %s" % self._multiworld_link)
                self._multiworld_site_data = get_site_data(self._multiworld_link)
            else:
                logging.debug("Site data passed to me, not grabbing new information.")
        except:
            raise FailedToStart(reason="Failed to get multiworld site data!")
        
        if (self._multiworld_site_data == None):
            raise FailedToStart(reason="Multiworld data returned 'None'")
        
        logging.debug("Creating main loop for %s" % self._multiworld_site_data.game_id) # TODO: Can probably just await this.
        asyncio.create_task(coro=self._main_loop(), name="MAIN_LOOP_%s" % self._multiworld_site_data.game_id)
        self._connected_callback = callback

    async def _main_loop(self):
        try:
            self._socket = await websockets.connect(uri=self.connection_url(), ping_interval=None, ping_timeout=None, ssl=get_ssl_context())
            self._incoming_data_loop = asyncio.create_task(coro=self.receive_data_loop(), name="INC_%s" % self._multiworld_site_data.game_id)
            self._outgoing_data_loop = asyncio.create_task(coro=self.send_data_loop(), name="OUT_%s" % self._multiworld_site_data.game_id)
        except ConnectionRefusedError:
            await self._chat_handler.add_message(chat_message("Failed to connect to game *%s*! Connection refused." % self._multiworld_site_data.game_id, self._message_destination))
        except websockets.ConnectionClosed:
            logging.info("Disconnected from game %s" % self._multiworld_site_data.game_id)
            await self.disconnect()

    def connected(self) -> bool:
        # Returns status of connection
        return (self._socket != None)
    
    async def disconnect(self):
        self._continue = False

        try:
            await self._socket.close() # Sometimes this is None by the time we get here, do not care about actually handling the exception
        except:
            pass
        self._socket = None

    def __init__(self, 
                game_name: str, 
                bot_client: discord.Client,
                response_destination: Union[discord.TextChannel, discord.Thread],
                multiworld_link: str, chat_handler_obj: chat_handler, password: str,
                site_data: archipelago_site_data = None,
                slot_id = 0):
        self._bot = bot_client
        self._game_name = game_name
        self._message_destination = response_destination
        self._thread = None
        self._socket = None
        self._multiworld_link = multiworld_link
        self._multiworld_site_data = site_data
        self._continue = True

        self._connected_callback = None
        
        self.slot_id = slot_id # Slot ID to login as for our ghost user

        self._chat_handler = chat_handler_obj

        self._archi_slot_players = []
        self._archi_players = []
        self._archi_retrieved_name_map = {}
        self._archi_player_hints = {}
        self._archi_player_items = {}
        self._archi_slot_info = []
        self._password = password or ""
        self._room_info = {}
        self._pending_payloads = []


from json_message_handler import json_message_handler
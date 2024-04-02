from archipelago_relay import *
from archipelago_site_scraping import archipelago_site_slot_data
import logging
import os, sys
import random

class deathlink_relay(archi_relay):
    #Override archi-relay to only care about deathlink messages.
    slot_id = None # Slot ID to login as for our ghost user

    def phantom_player(self) -> archipelago_site_slot_data:
        return self._multiworld_site_data.players[self.slot_id - 1] # Slot data from the website starts at 1 instead of 0, adjust!

    def __init__(self, parent_client: archi_relay, slot_id: int):
        self.slot_id = slot_id
        
        self._bot = parent_client._bot
        self._channel = parent_client._channel
        self._thread = None
        self._multiworld_link = parent_client._multiworld_link
        self._continue = True
        
        self._deathlink_relays = None
        self._chat_handler = parent_client._chat_handler

        self._archi_slot_players = parent_client._archi_slot_players
        self._archi_players = parent_client._archi_players
        self._archi_slot_info = parent_client._archi_slot_info
        self._password = parent_client._password
        self._room_info = parent_client._room_info
        self._pending_payloads = []

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
            logging.debug("Deathlink Connection, I will imitate %s playing %s." % (phantom_player.name, phantom_player.game))
            # Connect as a user now that we have RoomInfo
            payload = {
                'cmd': 'Connect',
                'password': self._password, 'name': phantom_player.name, 'version': version_tuple,
                'tags': ['TextOnly', 'AP', 'DeathLink'], 'items_handling': 0b111,
                'uuid': 696942024 + self.slot_id + random.randint(1, 100), 'game': phantom_player.game, "slot_data":False
            }
            self.append_payload(payload)

        elif (cmd == "PrintJSON"):
            pass # Do not print JSON.
        
        elif (cmd == "Connected"):
            try:
                for p in data["players"]:
                    self._archi_players.append(p)
                for k, s in data["slot_info"].items():
                    self._archi_slot_info.append(s)
                # Get our cache together.
                games = []
                for slot in self._archi_slot_info:
                    if (not slot.game in games):
                        games.append(slot.game)
                
                # Rip out any games where we trust our cache
                for game in games:
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
            logging.critical("----------BOUNCED---------")
            logging.critical(data)
        
        else:
            logging.warn("Received unhandled cmd: %s" % cmd)

    async def start(self):        
        if (self._multiworld_site_data == None):
            raise FailedToStart(reason="Multiworld data is 'None'")
        
        asyncio.create_task(coro=self._main_loop(), name="DEATHLINK_LOOP_%s_%s" % (self._multiworld_site_data.game_id, self.slot_id))
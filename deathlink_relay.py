
from archipelago_relay import *
from archipelago_site_scraping import archipelago_site_slot_data
import logging
import os, sys
import random

class deathlink_relay(archi_relay):
    #Override archi-relay to only care about deathlink messages.
    slot_id = None # Slot ID to login as for our ghost user
    _parent_relay: archi_relay = None

    def phantom_player(self) -> archipelago_site_slot_data:
        return self._multiworld_site_data.players[self.slot_id - 1] # Slot data from the website starts at 1 instead of 0, adjust!
    def __init__(self, parent_client: archi_relay, slot_id: int):
        self.slot_id = slot_id
        self._parent_relay = parent_client
        # I don't think this is... the best way to go. But eh
        super().__init__(bot_client=parent_client._bot, game_name=parent_client._game_name, response_destination=parent_client._message_destination, multiworld_link = parent_client._multiworld_link, site_data = parent_client._multiworld_site_data, chat_handler_obj=parent_client._chat_handler, password=parent_client._password )
        
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
            if (data['type'] == 'Hint'):
                # We only care if it's for us
                if (data['receiving'] == self.slot_id):
                    await self._parent_relay.forward_message(data)
        
        elif (cmd == "Connected"):
            pass

        elif (cmd == "DataPackage"):
            pass

        elif (cmd == "Bounced"):
            #{'cmd': 'Bounced', 'tags': ['DeathLink'], 'data': {'time': 1712093523.7267756, 'source': 'Ben', 'cause': ''}}
            if ('data' in data and 'source' in data['data']):
                await self._parent_relay.report_death(data)

        #else:
            #logging.warn("Received unhandled cmd: %s" % cmd)

    async def start(self):        
        if (self._multiworld_site_data == None):
            raise FailedToStart(reason="Multiworld data is 'None'")
        
        asyncio.create_task(coro=self._main_loop(), name="DEATHLINK_LOOP_%s_%s" % (self._multiworld_site_data.game_id, self.slot_id))

    async def receive_data_loop(self):
        while self._continue:
            try:
                async for data in self._socket:
                    decoded = decode(data)
                    for response in decoded:
                        logging.debug("\nRECEIVE:" + str(response))
                        await self.handle_response(response)
            except websockets.exceptions.ConnectionClosedError as e:
                logging.warn("[DEATHLINK]ConnectionClosedError")
                self._continue = False
                # Disconnect our parent too to force everything.
                await self.disconnect()
                await self._parent_relay.disconnect()
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error("[DEATHLINK]")
                logging.error([exc_type, fname, exc_tb.tb_lineno])
                logging.error(e)
            await asyncio.sleep(0.1)
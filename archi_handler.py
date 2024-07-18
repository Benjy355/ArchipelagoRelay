""" Class to manage archi_relays, spawns multiple to take up every slot in a game
The relay 
"""
from archipelago_relay import archi_relay
from archipelago_site_scraping import archipelago_site_data
from chat_handler import chat_handler
from typing import Union
from discord import TextChannel, Thread, Client
import asyncio

class archi_handler:
    _all_relays: list[archi_relay] = []

    game_name: str = None
    bot_client: Client = None
    response_destination: Union[TextChannel, Thread] = None
    multiworld_link: str = None
    chat_handler_obj: chat_handler  = None
    password: str = None
    site_data: archipelago_site_data = None

    def __init__(self,
                game_name: str,
                bot_client: Client,
                response_destination: Union[TextChannel, Thread],
                multiworld_link: str,
                chat_handler_obj: chat_handler,
                password: str,
                site_data: archipelago_site_data):
        self.game_name = game_name
        self.bot_client = bot_client
        self.response_destination = response_destination
        self.multiworld_link = multiworld_link
        self.chat_handler_obj = chat_handler_obj
        self.password = password
        self.site_data = site_data

        self._all_relays = []

    async def start_other_relays(self):
        for i in range(1, len(self.site_data.players)):
            new_relay = archi_relay(
                                    game_name = self.game_name,
                                    bot_client = self.bot_client,
                                    response_destination = self.response_destination,
                                    multiworld_link = self.multiworld_link,
                                    chat_handler_obj = self.chat_handler_obj,
                                    password = self.password,
                                    site_data = self.site_data,
                                    slot_id = i)
            self._all_relays.append(new_relay)
            new_relay.start()

    def start(self): # Connect the main relay, our callback will spawn the rest
        if (len(self._all_relays) > 0):
            raise Exception("Relay was not reset before starting!")
        
        # Start our main relay, wait for it, then launch the rest
        new_relay = archi_relay(
                                    game_name = self.game_name,
                                    bot_client = self.bot_client,
                                    response_destination = self.response_destination,
                                    multiworld_link = self.multiworld_link,
                                    chat_handler_obj = self.chat_handler_obj,
                                    password = self.password,
                                    site_data = self.site_data,
                                    slot_id = 0)
        self._all_relays.append(new_relay)
        new_relay.start(callback=self.start_other_relays)

    async def disconnect(self): # Disconnect everybody
        for relay in self._all_relays:
            await relay.disconnect()

    def connected(self) -> bool:
        try:
            return self._all_relays[0].connected()
        except:
            return False
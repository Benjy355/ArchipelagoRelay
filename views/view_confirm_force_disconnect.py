from typing import Coroutine
import discord
from discord.components import Button

class force_disconnect_session(discord.ui.View):
    # Glorified dict to forward information when connecting to a game (because we handle a View confirmation if they already have something being tracked)
    planned_response = ""
    game_name = ""
    relay_chat_destination = None
    multiworld_link = ""
    password = ""
    game_info = None

    def __init__(self, planned_response, game_name, relay_chat_destination, multiworld_link, password, game_info):
        self.planned_response = planned_response
        self.game_name = game_name
        self.relay_chat_destination = relay_chat_destination
        self.multiworld_link = multiworld_link
        self.password = password
        self.game_info = game_info

class confirm_force_disconnect_view(discord.ui.View):
    _callback_func = None # callback_func(interaction: discord.Interaction, session: force_disconnect_session)
    _session = None
    _disc_button = None

    def __init__(self, callback_func: Coroutine, session: force_disconnect_session):
        self._session = session
        self._callback_func = callback_func
        super().__init__(timeout=30)

        self._disc_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Disconnect")
        self.add_item(self._disc_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        await self._callback_func(interaction, self._session)
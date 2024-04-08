from typing import Coroutine
import discord
from discord.components import SelectOption

class disconnect_modal(discord.ui.View):
    #_options: list[str] = ['server 1', 'server 2', 'server 3']
    _callback_func = None # callback_func(server_id_to_disconnect_from)

    items_dropdown = None

    def __init__(self, callback_func: Coroutine, options: list[SelectOption]):
        super().__init__(timeout=30)
        self._callback_func = callback_func

        temp_options = []
        
        for o in options:
            temp_options.append(o)

        self.items_dropdown = discord.ui.Select(min_values=1, max_values=1, options=temp_options)
        self.add_item(self.items_dropdown)
        
    async def interaction_check(self, interaction: discord.Interaction) -> None:
        await self._callback_func(self, interaction)
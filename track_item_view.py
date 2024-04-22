from typing import Coroutine
import discord
from discord.components import SelectOption

class track_item_view(discord.ui.View):
    #_options: list[str] = ['server 1', 'server 2', 'server 3']
    _callback_func = None # callback_func(server_id_to_disconnect_from)

    items_dropdown = None
    #item_textbox = None
    item_to_track = ""

    def __init__(self, callback_func: Coroutine, options: list[SelectOption], item_to_track: str):
        super().__init__(timeout=30)
        self._callback_func = callback_func
        self.item_to_track = item_to_track

        temp_options = []
        
        for o in options:
            temp_options.append(o)

        self.items_dropdown = discord.ui.Select(placeholder="Multiworld ID", min_values=1, max_values=1, options=temp_options)
        self.add_item(self.items_dropdown)

        # GOD DAMN IT DISCORD GET YOUR API TOGETHER
        #self.item_textbox = discord.ui.TextInput(label="Item name", placeholder="Ice Trap")
        #self.add_item(self.item_textbox)
        
    async def interaction_check(self, interaction: discord.Interaction) -> None:
        await self._callback_func(self, interaction)
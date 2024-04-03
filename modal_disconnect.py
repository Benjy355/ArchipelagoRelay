from typing import Coroutine
import discord
from discord.components import SelectOption

class disconnect_modal(discord.ui.Modal, title="Disconnect"):
    #_options: list[str] = ['server 1', 'server 2', 'server 3']
    _callback_func = None # callback_func(server_id_to_disconnect_from)

    items_dropdown = None

    def __init__(self, callback_func, options: list[str]):
        super().__init__()
        
        self._callback_func = callback_func

        temp_options = []
        
        for o in options:
            temp_options.append(SelectOption(label=o))

        self.items_dropdown = discord.ui.Select(min_values=0, max_values=25, options=temp_options)
        self.add_item(self.items_dropdown)
        
    async def on_submit(self, interaction: discord.Interaction) -> None:
        justBreakHere = True
        await self._callback_func("test1")
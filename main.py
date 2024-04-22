import Config
import discord
from archipelago_relay import archi_relay, FailedToStart
from discord_oauth import DISCORD_TOKEN
from discord import app_commands
import asyncio
import logging
from chat_handler import chat_handler
from discord.components import SelectOption

from disconnect_view import disconnect_view

# Perms int 377957207104
#test = get_site_data("https://archipelago.gg/room/4_hWRGK1RPiG3wYFQTXImA")
#breakHere = None

#logging.getLogger().setLevel(logging.DEBUG)

tracked_games: dict[list[archi_relay]] = {} # {guild_id: [archi_relays]}

intent = discord.Intents.default()
intent.message_content = True

main_bot = discord.Client(intents=intent)
main_chat_handler = chat_handler(main_bot)

cmd_tree = app_commands.CommandTree(main_bot)

async def do_connect(ctx: discord.Interaction, multiworld_link: str, password: str = None, create_thread: str = "False"):
    #actually handles connecting (so reconnect and connect can both access
    try:
        #Create our relay object to start tracking!
        #Check to make sure we don't have an active one with the same link
        if (ctx.guild_id in tracked_games):
            for relay in tracked_games[ctx.guild_id]:
                if (relay.connection_url == multiworld_link):
                    await relay.disconnect()
                    tracked_games[ctx.guild_id].remove(relay)
        else:
            tracked_games[ctx.guild_id] = []

        new_relay = archi_relay(main_bot, ctx.channel, multiworld_link, main_chat_handler, password)
        tracked_games[ctx.guild_id].append(new_relay)

        await ctx.response.send_message("Connecting!", ephemeral=True)
        new_relay.start()

        Config.set("last_archi_connection_link", multiworld_link, ctx.guild)
        Config.set("last_archi_connection_password", password, ctx.guild)
    except FailedToStart as e:
        await ctx.response.send_message("Failed to connect! %s" % e.reason, ephemeral=True)


@cmd_tree.command(name="connect", description="Starts monitoring/relaying messages (to this channel) from said game")
@app_commands.describe(multiworld_link="Example: https://archipelago.gg/room/4_hWRGK1RPi...")
@app_commands.describe(password="Password to connect to the multiworld game")
@app_commands.describe(create_thread="*Not yet implemented*; will create a thread in the text channel.")
async def connect(ctx: discord.Interaction, multiworld_link: str, password: str = None, create_thread: str = "False"):
    #TODO: CHECK IF WE HAVE PERMISSIONS IN THAT CHANNEL BEFORE STARTING
    await do_connect(ctx, multiworld_link, password, create_thread)

@cmd_tree.command(name="reconnect", description="Reconnects to the last Multiworld server")
@app_commands.describe(create_thread="*Not yet implemented*; will create a thread in the text channel.")
async def reconnect(ctx: discord.Interaction, create_thread: str = "False"):
    prev_link = Config.get("last_archi_connection_link", ctx.guild)
    if (prev_link):
        await do_connect(ctx, prev_link, Config.get("last_archi_connection_password", ctx.guild), create_thread)
    else:
        await ctx.response.send_message("I don't see a previous Multiworld game to connect to.", ephemeral=True)

async def _disconnect_from_game(calling_view: disconnect_modal, ctx: discord.Interaction):
    for game in tracked_games[ctx.guild_id]:
        if (game._multiworld_site_data.game_id == calling_view.items_dropdown.values[0]):
            await game.disconnect()
            tracked_games[ctx.guild_id].remove(game)
            break

    await ctx.response.send_message("Disconnecting from %s!" % calling_view.items_dropdown.values[0], ephemeral=False)

@cmd_tree.command(name="disconnect", description="Allows you to disconnect from your game(s)")
async def disconnect(ctx: discord.Interaction):
    disconnect_options = []
    if (ctx.guild_id in tracked_games):
        for game in tracked_games[ctx.guild_id]:
            if game.connected:
                disconnect_options.append(SelectOption(label=game._multiworld_site_data.game_id, description="100 characters max!"))
        
    if (len(disconnect_options) > 0):
        the_modal = disconnect_view(_disconnect_from_game, disconnect_options)
        await ctx.response.send_message(content="Which game?", view=the_modal, ephemeral=True)
    else:
        await ctx.response.send_message(content="I'm not connected to any games!", ephemeral=True)

@cmd_tree.command(name="lookout", description="Have the bot ping you when an item is found!")
@app_commands.describe(item_name="Name of the item to look out for")
async def track_item(ctx: discord.Interaction, item_name: str):
    pass

@main_bot.event
async def on_ready():
    await cmd_tree.sync()
    main_chat_handler.start()
    print("Ready!")

main_bot.run(DISCORD_TOKEN, log_level=logging.WARN)
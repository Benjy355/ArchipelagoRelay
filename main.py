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
from track_item_view import track_item_view

from archipelago_relay import TrackedItem

import game_cache

# Perms int 377957207104
#test = get_site_data("https://archipelago.gg/room/4_hWRGK1RPiG3wYFQTXImA")
#breakHere = None

#logging.basicConfig(filename="fuckme.log", level=logging.DEBUG)
logging.getLogger().setLevel(logging.INFO)

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

async def _disconnect_from_game(calling_view: disconnect_view, ctx: discord.Interaction):
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
                disconnect_options.append(SelectOption(label=game._multiworld_site_data.game_id))
        
    if (len(disconnect_options) > 0):
        the_view = disconnect_view(_disconnect_from_game, disconnect_options)
        await ctx.response.send_message(content="Which game?", view=the_view, ephemeral=True)
    else:
        await ctx.response.send_message(content="I'm not connected to any games!", ephemeral=True)

async def _handle_track_item_view_callback(calling_view: track_item_view, ctx: discord.Interaction):
    item_to_track = calling_view.item_to_track
    found_item_in_game = False
    if (item_to_track == ""):
        return
    
    for multi_world_game in tracked_games[ctx.guild_id]:
        if (multi_world_game._multiworld_site_data.game_id == calling_view.items_dropdown.values[0]):
            # Look inside the game_caches for this multiworld, and make sure the item exists before we start watching for it
            games = []
            for slot in multi_world_game._archi_slot_info:
                if (not slot.game in games):
                    games.append(slot.game)
            
            for game in games:
                temp_cache = game_cache.get_game_cache(game)['item_name_to_id']
                keys = temp_cache.keys()
                # Case insensitivity work around incoming, PREPARE YOUR ANGUS
                uppercase_item = item_to_track.upper()
                for item in keys:
                    if uppercase_item == item.upper():
                        found_item_in_game = True
                        new_tracked_item = TrackedItem(temp_cache[item], ctx.user.mention)
                        multi_world_game.add_item_to_track(new_tracked_item)
            
            if (found_item_in_game):
                await ctx.response.send_message("Tracking %s!" % item_to_track, ephemeral=False)
            else:
                await ctx.response.send_message("I couldn't find %s in any games in that multiworld :(" % item_to_track, ephemeral=True)

@cmd_tree.command(name="lookout", description="Have the bot ping you when an item is found!")
@app_commands.describe(item_name="The name of the item you want to track, (Eg. 'Ice Trap')")
async def track_item(ctx: discord.Interaction, item_name: str):
    multiworld_games = []
    if (ctx.guild_id in tracked_games):
        for game in tracked_games[ctx.guild_id]:
            if game.connected:
                multiworld_games.append(SelectOption(label=game._multiworld_site_data.game_id))

    if (len(multiworld_games) > 0):
        the_view = track_item_view(_handle_track_item_view_callback, multiworld_games, item_name)
        await ctx.response.send_message(content="Which multiworld game is this item in? Note: If you disconnect I will not remember what items you wanted tracked.", view=the_view, ephemeral=True)
    else:
        await ctx.response.send_message(content="Please connect to a multiworld server first", ephemeral=True)
    

@main_bot.event
async def on_ready():
    await cmd_tree.sync()
    main_chat_handler.start()
    print("Ready!")

main_bot.run(DISCORD_TOKEN, log_level=logging.WARN)
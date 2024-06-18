import include.Config as Config
import discord
from archipelago_relay import archi_relay, FailedToStart
from archipelago_site_scraping import *
from include.discord_oauth import DISCORD_TOKEN
from discord import app_commands
import asyncio
import logging
from chat_handler import chat_handler

from views.view_confirm_force_disconnect import *

from archipelago_relay import TrackedItem # TODO: LOL deal with this disaster
from typing import Union

from include.game_namer import name_game
import copy

# Perms int 377957207104
#test = get_site_data("https://archipelago.gg/room/4_hWRGK1RPiG3wYFQTXImA")

logging.getLogger().setLevel(logging.INFO)

active_relays: dict[
    int, dict[
        int, archi_relay
        ]] = {} # {guild: {channel/thread id: archi_relay}}

intent = discord.Intents.default()
intent.message_content = True

main_bot = discord.Client(intents=intent)
main_chat_handler = chat_handler(main_bot)

cmd_tree = app_commands.CommandTree(main_bot)

# Handles connecting to a game and spinning up a new relay.
async def do_connect(ctx: discord.Interaction, multiworld_link: str, password: str = None, create_thread: str = 'false'):
    if (create_thread.lower() == "true" or create_thread.lower() == "t"):
        create_thread = True
    else:
        create_thread = False

    game_info = get_site_data(multiworld_link)
    planned_response = "You shouldn't be seeing this message, Ben fucked up."
    if (game_info == None):
        await ctx.response.send_message("Failed to get game information from that link!", ephemeral=True)
        return

    # Check and see if we are monitoring this game
    if (ctx.guild.id in active_relays):
        for relay in active_relays[ctx.guild.id].values():
            if (relay._multiworld_site_data.game_id == game_info.game_id):
                if (relay.connected()):
                    await ctx.response.send_message("I'm already connected to this game elsewhere, sorry!", ephemeral=True)
                    return
    else:
        active_relays[ctx.guild.id] = {}

    # Let's see if we have a game history, so we can just use that name instead of making a new one
    game_name = Config.get("GAMENAME_%s" % game_info.game_id, ctx.guild)
    game_thread_id = Config.get("GAMETHREAD_%s" % game_info.game_id, ctx.guild)
    if (game_name == None):
        game_name = name_game() # No game found, generate a new name!

    relay_chat_destination: Union[discord.TextChannel, discord.Thread] = None

    # If we have a thread ID saved, try to use it automatically; if that fails, defer to previous settings
    if (game_thread_id != None):
        # Are we already in that thread?
        if (type(ctx.channel) == discord.Thread):
            if (ctx.channel.id == game_thread_id):
                relay_chat_destination = ctx.channel
            else:
                ctx.response.send_message("[Exception]Somehow this thread's ID (%i) is not the ID I expected (%i). Contact Ben, he broke this real bad" % (ctx.channel.id, game_thread_id), ephemeral=True)
                return
        else:
            relay_chat_destination = ctx.channel.get_thread(game_thread_id)

    if (relay_chat_destination == None):
    # Are we making a thread? If so, check and see if we have a non-archived thread for this game already, and we if we can make a thread
        if (create_thread):
            for thread in ctx.channel.threads:
                if thread.name == game_name:
                    relay_chat_destination = thread
                    break # No need to make a thread, we've got one.
            if (relay_chat_destination == None):
                try:
                    relay_chat_destination = await ctx.channel.create_thread(name=game_name, type=discord.ChannelType.public_thread)
                    planned_response = "Connecting to new game, \"%s\"" % game_name
                    await relay_chat_destination.add_user(ctx.user)
                except discord.Forbidden:
                    await ctx.response.send_message("I don't have permissions to create Threads in this channel.", ephemeral=True)
                    return
        else:
            # Do we have perms to chat in this channel?
            if (not ctx.channel.permissions_for(ctx.guild.me).send_messages): # Why is ClientUser a thing vs the User type... >:(
                await ctx.response.send_message("I cannot chat in this channel!", ephemeral=True)
                return
            else:
                planned_response = "Connecting to new game, \"%s\"" % game_name
                relay_chat_destination = ctx.channel
    else:
        planned_response = "Looks like we've got a thread already! I'll reconnect in there."
    
    # We've made it this far, our thread/game should be real, let's save the name
    Config.set("GAMENAME_%s" % game_info.game_id, game_name, ctx.guild)
    if (type(relay_chat_destination) is discord.Thread):
        Config.set("GAMETHREAD_%s" % game_info.game_id, relay_chat_destination.id, ctx.guild)

    # this is kind of really ugly
    new_session = force_disconnect_session(
                    planned_response=planned_response,
                    game_name=game_name,
                    relay_chat_destination=relay_chat_destination,
                    multiworld_link=multiworld_link,
                    password=password,
                    game_info=game_info
                )
    if (ctx.guild.id in active_relays.keys()):
        for thread_id in active_relays[ctx.guild.id].keys():
            if (active_relays[ctx.guild.id][thread_id].connected()):
                disc_view = confirm_force_disconnect_view(callback_func=finish_connection, session=new_session)
                await ctx.response.send_message("To continue tracking %s, disconnect %s. (Or do nothing to cancel)" % (game_name, active_relays[ctx.guild.id][thread_id]._game_name), view=disc_view, ephemeral=True)
                return
        
    await finish_connection(ctx, new_session)

async def finish_connection(ctx: discord.Interaction, session: force_disconnect_session):
    # Do this check again, to disconnect and delete duplicates
    # TODO: How the fuck can you iterate AND delete items from an array to cleanup things periodically (remake the array, dumbass)
    if (ctx.guild.id in active_relays.keys()):
        for thread_id in active_relays[ctx.guild.id].keys():
            if (active_relays[ctx.guild.id][thread_id].connected()):
                await active_relays[ctx.guild.id][thread_id].disconnect()

    await ctx.response.send_message(session.planned_response, ephemeral=True)
    new_relay = archi_relay(game_name=session.game_name,
                            bot_client=main_bot,
                            response_destination=session.relay_chat_destination,
                            multiworld_link=session.multiworld_link,
                            chat_handler_obj=main_chat_handler,
                            password=session.password,
                            site_data=session.game_info)

    active_relays[ctx.guild.id][session.relay_chat_destination.id] = new_relay

    new_relay.start()

    Config.set("last_archi_connection_link_%s" % session.relay_chat_destination.id, session.multiworld_link, ctx.guild)
    Config.set("last_archi_connection_password_%s" % session.relay_chat_destination.id, session.password, ctx.guild)


@cmd_tree.command(name="connect", description="Starts monitoring/relaying messages (to this channel) from said game")
@app_commands.describe(multiworld_link="Example: https://archipelago.gg/room/4_hWRGK1RPi...")
@app_commands.describe(password="[Optional]Password to connect to the multiworld game")
@app_commands.describe(create_thread="[Optional](t or f) Will create a thread in the text channel.")
async def connect(ctx: discord.Interaction, multiworld_link: str, password: str = None, create_thread: str = "f"):
    await do_connect(ctx, multiworld_link, password, create_thread)

@cmd_tree.command(name="reconnect", description="Reconnects to the last Multiworld server in this channel/thread")
@app_commands.describe(create_thread="*Not yet implemented*; will create a thread in the text channel.")
async def reconnect(ctx: discord.Interaction, create_thread: str = "False"):
    prev_link = Config.get("last_archi_connection_link_%s" % ctx.channel_id, ctx.guild)
    if (prev_link):
        await do_connect(ctx, prev_link, Config.get("last_archi_connection_password_%s" % ctx.channel_id, ctx.guild), create_thread)
    else:
        await ctx.response.send_message("I don't see a previous Multiworld game in this chat to connect to. (Try again in a specific channel or thread!)", ephemeral=True)

@cmd_tree.command(name="disconnect", description="Disconnect from the game active in this chat")
async def disconnect(ctx: discord.Interaction):
    # See if we're in a game here
    found_game = None
    if (ctx.guild.id in active_relays.keys()):
        for thread_id in active_relays[ctx.guild.id].keys():
            if (active_relays[ctx.guild.id][thread_id].connected()):
                found_game = active_relays[ctx.guild.id][thread_id]
                break
    if (found_game == None):
        await ctx.response.send_message("No active relay found in this channel/thread.", ephemeral=True)
        return
    
    await found_game.disconnect()
    await ctx.response.send_message("Disconnected from \"%s\"" % found_game._game_name, ephemeral=False)


"""
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
"""

"""
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
        await ctx.response.send_message(content="Which multiworld game is this item in? Note: If you disconnect I *will* remember what items you wanted tracked.", view=the_view, ephemeral=True)
    else:
        await ctx.response.send_message(content="Please connect to a multiworld server first", ephemeral=True)
    

async def _send_hints(calling_view: disconnect_view, ctx: discord.Interaction, server_id: str = ""):
    # So we're going to have to find a system for this command to send the "GET" command, AND get the response sent back over to it
    if (calling_view == None and not server_id == ""):
        game_data = None
        # Don't check view results if we were just given a server ID
        for multi_game in tracked_games[ctx.guild_id]:
            if multi_game._multiworld_site_data.game_id == server_id:
                game_data = multi_game
                break
        
        hints_string = ""
        if (game_data != None):
            for k, hint_dict in game_data._archi_player_hints.items():
                for hint in hint_dict:
                    hints_string += "**%s** for **%s** is at *%s* in *%s*'s world [*%s*]\n" % (
                        game_data._get_itemName_by_id(hint['item'], hint['receiving_player']),
                        game_data._get_playerAlias_by_id(hint['receiving_player']),
                        game_data._get_locationName_by_id(hint['location'], hint['finding_player']),
                        game_data._get_playerAlias_by_id(hint['finding_player']),
                        "*FOUND*" if hint['found'] == True else "Not Found"
                    )
            if (hints_string != ""):
                await ctx.response.send_message(hints_string, ephemeral=True)
            else:
                await ctx.response.send_message("I have no hints found for your multiworld game :(", ephemeral=True)
        else:
            await ctx.response.send_message("Something went wrong, blame Ben!", ephemeral=True)
            logging.error("Failed to find game_data for server id %s in _send_hints" % server_id)



@cmd_tree.command(name="hints", description="List hints (and their status)")
async def hints(ctx: discord.Interaction):
    server_options = []
    if (ctx.guild_id in tracked_games):
        for game in tracked_games[ctx.guild_id]:
            if game.connected:
                server_options.append(game._multiworld_site_data.game_id)

    if (len(server_options) < 1):
        await ctx.response.send_message(content="Please connect to a multiworld game first!", ephemeral=True)
    if (len(server_options) < 2):
        # We only have one option, just use it.
        await _send_hints(None, ctx, server_options[0])
    else:
        await ctx.response.send_message("Ben forgot to finish this part of the hints function", ephemeral=False) # Just in case
"""
@main_bot.event
async def on_ready():
    await cmd_tree.sync()
    main_chat_handler.start()
    print("Ready!")

main_bot.run(DISCORD_TOKEN, log_level=logging.WARN)
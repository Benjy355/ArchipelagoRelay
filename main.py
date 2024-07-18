import include.Config as Config
import discord
from archipelago_relay import archi_relay, FailedToStart
from archi_handler import archi_handler
from archipelago_site_scraping import *
from include.discord_oauth import DISCORD_TOKEN
from discord import app_commands
import asyncio
import logging
from chat_handler import chat_handler

from views.view_confirm_force_disconnect import *

from typing import Union

from include.game_namer import name_game
import copy

# Perms int 377957207104
#test = get_site_data("https://archipelago.gg/room/4_hWRGK1RPiG3wYFQTXImA")

logging.getLogger().setLevel(logging.INFO)

active_relays: dict[
    int, dict[
        int, archi_handler
        ]] = {} # {guild: {channel/thread id: archi_handler}}

intent = discord.Intents.default()
intent.message_content = True

main_bot = discord.Client(intents=intent)
main_chat_handler = chat_handler(main_bot)

cmd_tree = app_commands.CommandTree(main_bot)

# Handles connecting to a game and spinning up a new relay.
async def do_connect(ctx: discord.Interaction, multiworld_link: str, password: str = None, create_thread: str = 't'):
    if (create_thread.lower() == "true" or create_thread.lower() == "t"):
        create_thread = True
    else:
        create_thread = False

    await ctx.response.send_message("Please wait...", ephemeral=True)

    game_info = get_site_data(multiworld_link)
    planned_response = "You shouldn't be seeing this message, Ben fucked up."
    if (game_info == None):
        await ctx.edit_original_response(content="Failed to get game information from that link!")
        return

    # Check and see if we are monitoring this game
    if (ctx.guild.id in active_relays):
        for relay in active_relays[ctx.guild.id].values():
            if (relay._multiworld_site_data.game_id == game_info.game_id):
                if (relay.connected()):
                    await ctx.edit_original_response(content="I'm already connected to this game elsewhere, sorry!")
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
                    await ctx.edit_original_response(content="I don't have permissions to create Threads in this channel.")
                    return
        else:
            # Do we have perms to chat in this channel?
            if (not ctx.channel.permissions_for(ctx.guild.me).send_messages): # Why is ClientUser a thing vs the User type... >:(
                await ctx.edit_original_response(content="I cannot chat in this channel!")
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
    # Check to be sure we aren't tracking a game in the destination thread only.
    if (ctx.guild.id in active_relays.keys()):
        if (relay_chat_destination.id in active_relays[ctx.guild.id].keys() and 
            active_relays[ctx.guild.id][relay_chat_destination.id].connected()):
                disc_view = confirm_force_disconnect_view(callback_func=finish_connection, session=new_session)
                await ctx.followup.send("To continue tracking %s, disconnect %s. (Or do nothing to cancel)" % (game_name, active_relays[ctx.guild.id][relay_chat_destination.id]._game_name), view=disc_view, ephemeral=True)
                return
        
    await finish_connection(ctx, new_session)

async def finish_connection(ctx: discord.Interaction, session: force_disconnect_session):
    # Do this check again, to disconnect duplicates
    if (session.relay_chat_destination.id in active_relays[ctx.guild.id].keys() and 
            active_relays[ctx.guild.id][session.relay_chat_destination.id].connected()):
                await active_relays[ctx.guild.id][session.relay_chat_destination.id].disconnect()

    await ctx.edit_original_response(content=session.planned_response)
    new_relay = archi_handler(game_name=session.game_name,
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
async def connect(ctx: discord.Interaction, multiworld_link: str, password: str = None, create_thread: str = "t"):
    await do_connect(ctx, multiworld_link, password, create_thread)

@cmd_tree.command(name="reconnect", description="Reconnects to the last Multiworld server in this channel/thread")
@app_commands.describe(create_thread="Will create a thread in the text channel.")
# TODO: ALLOW RECONNECT TO FORCE A THREAD (IF ONE DIDN'T EXIST)
async def reconnect(ctx: discord.Interaction, create_thread: str = "t"):
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
    await ctx.response.send_message("Disconnected from \"%s\"" % found_game.game_name, ephemeral=False)


#@cmd_tree.command(name="break", description="Breaks the bot so ben can debug")
#async def Break(ctx: discord.Interaction):
#    pass

@main_bot.event
async def on_ready():
    await cmd_tree.sync()
    main_chat_handler.start()
    print("Ready!")

main_bot.run(DISCORD_TOKEN, log_level=logging.WARN)
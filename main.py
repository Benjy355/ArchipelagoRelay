import Config
import discord
from archipelago_relay import archi_relay, FailedToStart
from discord_oauth import DISCORD_TOKEN
from discord import app_commands
import logging
from chat_handler import chat_handler, chat_message

# Perms int 377957207104

tracked_games = []

intent = discord.Intents.default()
intent.message_content = True

main_bot = discord.Client(intents=intent)
main_chat_handler = chat_handler(main_bot)

cmd_tree = app_commands.CommandTree(main_bot)

#@cmd_tree.command(name="help", description="Lists all the commands, ")
#async def help(ctx: discord.Interaction):
#    await ctx.response.send_message("BEN FINISH ME")

@cmd_tree.command(name="connect", description="Starts monitoring/relaying messages (to this channel) from said game")
@app_commands.describe(multiworld_link="Example: https://archipelago.gg/room/4_hWRGK1RPi...")
@app_commands.describe(password="Password to connect to the multiworld game")
@app_commands.describe(create_thread="*Not yet implemented*; will create a thread in the text channel.")
async def connect(ctx: discord.Interaction, multiworld_link: str, password: str = None, create_thread: str = "False"):
    #TODO: CHECK IF WE HAVE PERMISSIONS IN THAT CHANNEL BEFORE STARTING
    try:
        tracked_games.append(await archi_relay(main_bot, ctx.channel, multiworld_link, main_chat_handler))
        await ctx.response.send_message("Connecting!", ephemeral=True)
    except FailedToStart as e:
        await ctx.response.send_message("Failed to connect! %s" % e.reason)

@main_bot.event
async def on_ready():

    await cmd_tree.sync()

main_bot.run(DISCORD_TOKEN, log_level=logging.WARN)


import Config
import discord
from archipelago_relay import archi_relay
from discord_oauth import DISCORD_TOKEN
from discord import app_commands
import archipelago_site_scraping
import logging

# Perms int 377957207104
#test = "https://archipelago.gg/room/4_hWRGK1RPiG3wYFQTXImA"
archipelago_site_scraping.get_site_data(test)


tracked_games = []

intent = discord.Intents.default()
intent.message_content = True

main_bot = discord.Client(intents=intent)

cmd_tree = app_commands.CommandTree(main_bot)

#@cmd_tree.command(name="help", description="Lists all the commands, ")
#async def help(ctx: discord.Interaction):
#    await ctx.response.send_message("BEN FINISH ME")

@cmd_tree.command(name="connect", description="NOT YET IMPLEMENTED LOL")
@app_commands.describe(multiworld_link="Example: https://archipelago.gg/room/4_hWRGK1RPiG3wYFQTXImA")
@app_commands.describe(create_thread="*Not yet implemented*; will create a thread in the text channel.")
async def connect(ctx: discord.Interaction, multiworld_link: str, create_thread: str):
    await ctx.response.send_message("You sent me the link: %s" % multiworld_link)

@main_bot.event
async def on_ready():
    await cmd_tree.sync()

main_bot.run(DISCORD_TOKEN, log_level=logging.WARN)
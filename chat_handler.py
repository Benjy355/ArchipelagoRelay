"""Object used to handle chatting in channels/threads
Its whole job is to keep a queue of messages running through at a certain rate so Discord doesn't get mad at us (especially when someone uses !release)

"""

import discord

class chat_message:
    #Simple container for message relay messages
    message = None
    channel = None
    
    def __init__(self, message: str, channel: discord.TextChannel):
        self.message = message
        self.channel = channel

class chat_handler:
    _bot_client = None
    _message_queue = None # List of chat_message objects

    def __init__(self, bot_client: discord.Client):
        self._bot_client = bot_client()
        self._message_queue = []
"""Object used to handle chatting in channels/threads
Its whole job is to keep a queue of messages running through at a certain rate so Discord doesn't get mad at us (especially when someone uses !release)

"""

import discord
import asyncio
import logging
logger = logging.getLogger(__name__)

import os
import sys

class chat_message:
    #Simple container for message relay messages
    # 20 = ~ 50/second
    message: str = None
    channel: discord.TextChannel = None
    
    def __init__(self, message: str, channel: discord.TextChannel):
        self.message = message
        self.channel = channel

class chat_handler:
    _NEXT_MESSAGE_DELAY = 20 # In milliseconds, how long to sleep between messages sent to Discord
    _bot_client: discord.Client = None
    _message_queue: list[chat_message] = None # List of chat_message objects
    _loop_object: asyncio.Task = None
    _keep_running = True

    def __init__(self, bot_client: discord.Client):
        self._bot_client = bot_client
        self._message_queue = []
        self._keep_running = True

        # Start our co-routine for sending messages
        self._loop_object = asyncio.create_task(self._message_loop(), name="discord_message_loop")        

    async def add_message(self, message: chat_message):
        self._message_queue.append(message)

    async def _message_loop(self):
        # Called every N ms to send a new message
        while (self._keep_running):
            try:
                if (len(self._message_queue) > 0):
                    next_message: chat_message = self._message_queue.pop
                    next_message.channel.send(next_message.message)
                await asyncio.sleep(self._NEXT_MESSAGE_DELAY)
            except discord.Forbidden:
                logging.error("[chat_handler]Don't have permissions to send messages in channel '%s', stopping." % next_message.channel.name)
                self._keep_running = False
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logging.error([exc_type, fname, exc_tb.tb_lineno])
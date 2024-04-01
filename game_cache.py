#Handles caching/retrieval of game data

import copy
import json
import os
import discord

#Dict containing everything
#_game_data[game] = {data}
_game_data = {}
_json_directory = "game_data"
_json_file = _json_directory + "\\c%s.json"

def get_game_details(game_name: str) -> dict:
    #Returns None when no cache exists yet
    pass

def update_game_details(game_name: str, game_dict: dict) -> None:
    pass
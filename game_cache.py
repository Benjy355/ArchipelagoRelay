#Handles caching/retrieval of game data

import copy
import json
import os
import discord

import logging
logger = logging.getLogger(__name__)

#Dict containing everything
#_game_data[game] = {data}
_game_data = {}
_json_directory = "game_data"
_json_file = _json_directory + "\\c%s.json"

def get_game_cache(game_name: str, version: int) -> dict:
    #Check to see if there is a JSON file containing all of our game data
    #Compare verions if it exists
    #Returns None when no cache exists yet, or cache is out of date.
    global _game_data, _json_file

    if (not game_name in _game_data or _game_data[game_name] == None):
        if (os.path.isfile(_json_file % game_name)):
            try:
                json_file = open(_json_file % game_name, 'r')
            except:
                logging.error("[game_cache]Failed to open JSON cache file for %s!" % game_name)
                return None
            try:
                logging.debug("[game_cache]Loading cache for %s" % _game_data)
                _game_data[game_name] = json.loads(json_file.read())
            except:
                json_file.close()
                logging.error("[game_cache]Cache for %s is corrupt (file level)! Requesting...." % game_name)
                _game_data[game_name] = None
                return None
            json_file.close()
        else:
            logging.debug("[game_cache]No cache for %s found" % game_name)
        return None
    else:
        #Check our version
        try:
            #TODO: CHECK THE CHECKSUM
            if (int(_game_data[game_name]['version']) < version):
                _game_data[game_name] = None
                logging.info("[game_cache]Cache for %s is out of date! Requesting..." % game_name)
        except:
            logging.error("[game_cache]Cache for %s is corrupt (in memory)! Requesting..." % game_name)
            return None
        return _game_data[game_name]

#'command', 'data', 'version'
def update_game_cache(game_name: str, game_dict: dict) -> None:
    #Replace any json file with our new game data.
    global _game_data, _json_file
    try:
        if (not os.path.exists(_json_directory)):
            os.makedirs(_json_directory)
    except:
        _game_data[game_name] = game_dict
        logging.error("[game_cache]Failed to make or access %s" % _json_directory)
    
    try:
        io_file = open(_json_file % game_name, 'w')
        json.dump(_game_data[game_name], io_file)
        io_file.close()
    except:
        logging.error("[game_cache]Failed to save cache for %s" % game_name)
    
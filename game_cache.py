#Handles caching/retrieval of game data

import json
import os
import sys

from include.archipelago_common import flip_dict, convert_keys_to_int

import logging
logger = logging.getLogger(__name__)

#Dict containing everything
#_game_data[game] = {data}
_game_data = {}
_json_directory = "game_data"
_json_file = _json_directory + "\\%s.json"

def get_game_cache(game_name: str, version: int = None) -> dict:
    #Check to see if there is a JSON file containing all of our game data
    #Compare verions if it exists
    #Returns None when no cache exists yet, or cache is out of date.
    #If version is None ignores checking (useful for repeated calls)
    global _game_data, _json_file

    if (not game_name in _game_data or _game_data[game_name] == None):
        # No cache in memory right now, let's grab the JSON
        if (os.path.isfile(_json_file % game_name)):
            try:
                json_file = open(_json_file % game_name, 'r')
            except:
                logging.error("[game_cache]Failed to open JSON cache file for %s!" % game_name)
                return None
            try:
                logging.info("[game_cache]Loading cache for %s" % game_name)
                temp_game_data = json.loads(json_file.read())
                temp_game_data['item_id_to_name'] = convert_keys_to_int(temp_game_data['item_id_to_name'])
                temp_game_data['location_id_to_name'] = convert_keys_to_int(temp_game_data['location_id_to_name'])
                _game_data[game_name] = temp_game_data
            except:
                json_file.close()
                logging.error("[game_cache]Cache for %s is corrupt (file level)! Requesting...." % game_name)
                _game_data[game_name] = None
                return None
            json_file.close()
        else:
            # No cache available, return None
            logging.info("[game_cache]No cache for %s found" % game_name)
            return None
    # We have something in our memory, let's confirm our version
    try:
        #TODO: CHECK THE CHECKSUM
        if (version != None):
            if (int(_game_data[game_name]['version']) < version):
                _game_data[game_name] = None
                logging.info("[game_cache]Cache for %s is out of date! Requesting..." % game_name)
                return None
    except:
        logging.error("[game_cache]Cache for %s is corrupt (in memory)! Requesting..." % game_name)
        return None
    
    # Our cache must be okay, let's send it over
    return _game_data[game_name]

def update_game_cache(game_name: str, game_dict: dict) -> None:
    #Replace any json file with our new game data.
    global _game_data, _json_file
    _game_data[game_name] = game_dict

    # We got fresh data, let's flip the item_name_to_id table for easy skimming
    for game in _game_data:
        _game_data[game]['item_id_to_name'] = flip_dict(_game_data[game]['item_name_to_id'])
        _game_data[game]['location_id_to_name'] = flip_dict(_game_data[game]['location_name_to_id'])

    try:
        if (not os.path.exists(_json_directory)):
            os.makedirs(_json_directory)
    except:
        logging.error("[game_cache]Failed to make or access %s" % _json_directory)
    
    try:
        io_file = open(_json_file % game_name, 'w')
        json.dump(game_dict, io_file)
        logging.info("[game_cache]Updated game cache for %s!" % game_name)
        io_file.close()
    except Exception as e:
        logging.error("[game_cache]Failed to save cache for %s" % game_name)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logging.error("[game_cache]")
        logging.error([exc_type, fname, exc_tb.tb_lineno])
        logging.error(e)


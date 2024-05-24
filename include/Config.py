import copy
import json
import os
import discord

#Handles persistent data/settings

#TODO: Move config over to SQL for flexability? NAH FUCK THAT TOO MUCH WORK YO

#Dict containing everything
#_config[server] = {config_dict}
_config = {}
_json_directory = "persistent_data"
_json_file = _json_directory + "\\c%s.json"

def _load(server: discord.Guild):
    #Attempt to load a server's json file, if no file exists, generate empty dict in place
    global _config
    json_file = _json_file % server.id
    if (os.path.isfile(json_file)):
        config_file = open(json_file, 'r')
        try:
            _config[server] = json.loads(config_file.read())
        except json.decoder.JSONDecodeError:
            print("Failed to load json file for server %s" % str(server.id))
            _config[server] = {}
            pass
        config_file.close()
    else:
        print("No json file found for server %s" % str(server.id))
        _config[server] = {}

def get(setting, server: discord.Guild, default=None):
    #returns the reference to a setting, or a reference to a new one
    global _config
    if (not server): #Generally happens when people private message the bot
        return default
    if (not server in _config):
        _load(server)
    if (not setting in _config[server]):
        _config[server][setting] = copy.deepcopy(default)
    
    return _config[server][setting]

def set(setting, newValue, server: discord.Guild):
    #returns the reference to a setting, or a reference to a new one
    global _config
    if (not server): #Generally happens when people private message the bot
        return
    if (not server in _config):
        _load(server)
    
    _config[server][setting] = copy.deepcopy(newValue)

    save()
    
    return _config[server][setting]

def forget(setting, server: discord.Guild):
    #removes a setting from _config[server]
    global _config
    if (setting in _config[server]):
        _config[server].pop(setting)

#TODO: Put catches in here for when read/writes fail?
def save():
    #saves everything to a json file
    global _config
    if (not os.path.exists(_json_directory)):
        os.makedirs(_json_directory)
        
    for key, server in _config.items():
        json_file = _json_file % key.id
        config_file = open(json_file, 'w')
        json.dump(server, config_file)
        config_file.close()
        
from include.JSONNodeFilter import JSONNodeFilter
from include.JSONMessageFilter import JSONMessageFilter    
from archipelago_relay import archi_relay
from include.archipelago_common import NetworkItem
#from json_message_handler import json_message_handler

## NODE FILTER FUNCTIONS
def _default_item_id_flags_func(node: dict, relay: archi_relay) -> str:
    if node['flags'] & 0b001: # Progression
        return "**%s**"
    elif node['flags'] & 0b010: # Useful
        return "*%s*"
    elif node['flags'] & 0b100: # Trap
        return "%s <:Duc:1084164152681037845><:KerZ:1084164151317889034>"
    else: # Junk
        return ""

## MESSAGE FILTER FUNCTIONS
def _do_nothing(data: dict, relay: archi_relay, parent_json_handler) -> str:
    return ""

def _default_generic_message_func(data: dict, relay: archi_relay, parent_json_handler):
    # Just go through node filters everything else.
    final_string = ""
    for node in data['data']:
        node_text = parent_json_handler._filter_node(node)
        if (node_text != None and node_text != ""):
            if ("%s" in node_text): # Fun fact I did not know, if you try to % format a string that doesn't contain a place for it, an exception is raised!
                final_string += node_text % node['text']
            else:
                final_string += node_text
        else:
            # _handle_node returned nothing, message should be ignored
            return ""
    return final_string

def _default_hint_message_func(data: dict, relay: archi_relay, parent_json_handler) -> str:
    #player_info = relay._get_playerData_by_id(data['slot'])
    receiving_player_name = relay._get_playerName_by_id(data['receiving'])
    item: NetworkItem = data['item']
    item_str = relay._get_itemName_by_id(item.item, data['receiving'])
    item_location_str = relay._get_locationName_by_id(item.location, item.player)
    sending_player_name = relay._get_playerName_by_id(item.player)
    found = data['found']
    if (found):
        return f"[Hint]: {receiving_player_name}'s **{item_str}** was **FOUND** at *{item_location_str}* in {sending_player_name}'s world."
    else:
        return f"[Hint]: {receiving_player_name}'s **{item_str}** is at *{item_location_str}* in {sending_player_name}'s world."
    
def _default_join_message_func(data: dict, relay: archi_relay, parent_json_handler) -> str:
    player_info = relay._get_playerData_by_id(data['slot'])
    return "*%s* has joined playing *%s*." % (player_info.name, relay._get_playerGame_by_id(data['slot']))

def _default_part_message_func(data: dict, relay: archi_relay, parent_json_handler) -> str:
    player_info = relay._get_playerData_by_id(data['slot'])
    return "*%s* has disconnected." % (player_info.name)

## Default groups

DefaultNodeFilters = {
    'text': JSONNodeFilter("text", filter_message="%s"),
    'player_id': JSONNodeFilter("player_id", filter_message="**%s**"),
    'item_id': JSONNodeFilter("item_id", check_func=_default_item_id_flags_func),
    'location_id': JSONNodeFilter("location_id", filter_message="%s"),
    'color': JSONNodeFilter("color", filter_message="%s")
}

DefaultMessageFilters = {
    'generic': JSONMessageFilter("generic", filter_func=_default_generic_message_func),
    'Join': JSONMessageFilter("Join", filter_func=_default_join_message_func),
    'Hint': JSONMessageFilter("Hint", filter_func=_default_hint_message_func),
    'Tutorial': JSONMessageFilter("Tutorial", filter_func=_do_nothing),
    'TagsChanged': JSONMessageFilter("TagsChanged", filter_func=_do_nothing),
    'Part': JSONMessageFilter("Part", filter_func=_default_part_message_func),
    'TagsChanged': JSONMessageFilter("TagsChanged", filter_func=_do_nothing)
}
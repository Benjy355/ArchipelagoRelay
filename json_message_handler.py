from archipelago_relay import archi_relay
import logging
import sys
import os
from include.JSONNodeFilter import JSONNodeFilter
from include.JSONMessageFilter import JSONMessageFilter
import JSONFilters

class json_message_handler:
    parent_relay: archi_relay = None
    node_filters: dict[str, JSONNodeFilter] = {}
    message_filters: dict[str, JSONMessageFilter] = {}

    def __init__(self, parent_relay: archi_relay, node_filters: dict[str, JSONNodeFilter] = JSONFilters.DefaultNodeFilters, message_filters: dict[str, JSONMessageFilter] = JSONFilters.DefaultMessageFilters):      
        self.parent_relay = parent_relay
        self.node_filters = node_filters
        self.message_filters = message_filters

    def _filter_node(self, node: dict) -> str:
        # Determines if we are modifying the node text, returns the new node 'text'
        # Returns "" if filters determine message should be ignored
        if (not "type" in node):
            node['type'] = "text" # So we can filter for generic text, we will force a type to exist.
                
        if (node['type'] in self.node_filters):
            # Is there a check function? If not, just use it's filter
            node_filter = self.node_filters[node['type']]
            filtered_node_txt = ""
            if (node_filter.check_func != None):
                filtered_node_txt = node_filter.check_func(node, self)
            else:
                filtered_node_txt = node_filter.filter_message

            if (filtered_node_txt != None and filtered_node_txt != ""):
                # Our message has been filtered, now let's fill in the relevent data
                if node['type'] == 'text':
                    pass # Do nothing, but leave this here just in case we wanna do stuff later I dunno
                elif node['type'] == 'player_id':
                    filtered_node_txt = filtered_node_txt % self.parent_relay._get_playerAlias_by_id(int(node['text']))
                elif node['type'] == 'item_id':
                    filtered_node_txt = filtered_node_txt % self.parent_relay._get_itemName_by_id(int(node['text']), int(node['player']))
                elif node['type'] == 'location_id':
                    filtered_node_txt = filtered_node_txt % self.parent_relay._get_locationName_by_id(int(node['text']), int(node['player']))

            return filtered_node_txt
        else:
            logging.warn("Node type '%s' not present in filters for message:" % node['type'])
            logging.warn(node)
            return node['text']
        
    def _filter_message(self, data: dict) -> str:
        final_message = ""
        if ("type" not in data):
            logging.warning("No type field for PrintJSON cmd!")
            logging.warning(data)
            data['type'] = "generic"
        
        if (data['type'] in self.message_filters):
            #check_func(node: dict, relay: archi_relay, parent_json_handler: json_message_handler) -> str
            final_message += self.message_filters[data['type']].filter_func(data=data, relay=self.parent_relay, parent_json_handler=self)
        else:
            logging.info("No handler for message type %s. Using generic." % data['type'])
            final_message += JSONFilters._default_generic_message_func(data=data, relay=self.parent_relay, parent_json_handler=self)
        
        return final_message


    def convert_json_msg(self, json: dict) -> str:
        # Converts the usual PRINTJSON command over to a regular string, after passing it through filters.
        # CAN RETURN EMPTY STRING!
        try:
            return self._filter_message(json)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logging.error([exc_type, fname, exc_tb.tb_lineno])
            logging.error(e)
            return ""
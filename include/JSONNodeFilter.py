from archipelago_relay import archi_relay

class JSONNodeFilter:
    node_type = "" # TODO: Is this required?
    filter_message = "%s" # Called as filter_message % (message.text), "" means 'ignore message'
    # Used to check nodes for flags or types before deciding on the filter_message, returns a replacement to filter_message
    check_func = None # check_func(node: dict, relay: archi_relay) -> str

    def __init__(self, node_type: str, filter_message:str = "", check_func = None):
        self.node_type = node_type
        self.filter_message = filter_message
        self.check_func = check_func
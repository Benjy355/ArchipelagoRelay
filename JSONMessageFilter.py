from archipelago_relay import archi_relay

class JSONMessageFilter:
    # Simple little container 
    node_type = "" # TODO: Is this required?
    filter_func = None # check_func(data: dict, relay: archi_relay, parent_json_handler: json_message_handler) -> str

    def __init__(self, node_type: str, filter_func):
        self.node_type = node_type
        self.filter_func = filter_func
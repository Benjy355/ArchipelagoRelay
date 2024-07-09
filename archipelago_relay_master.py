from archipelago_relay import archi_relay

class archi_relay_controller:
    _relays: list[archi_relay] = None # List of relays we are monitoring

    # Class who's whole job is to spin up N archi_relay instances for each user in a multiworld, designate which player slot it is
    # As well as handle the messages coming in (handle duplicates, [hint] messages, deathlink messages, etc)
    def __init__(self):
        pass
from JSONMessageFilter import JSONMessageFilter

def _default_item_id_flags_func(node: dict) -> str:
    if node['flags'] & 0b001: # Progression
        return "**%s**"
    elif node['flags'] & 0b010: # Useful
        return "*%s*"
    elif node['flags'] & 0b100: # Trap
        return "%s <:Duc:1084164152681037845><:KerZ:1084164151317889034>"
    else: # Junk
        return ""

DefaultFilters = {
    'text': JSONMessageFilter("text", filter_message="%s"),
    'player_id': JSONMessageFilter("player_id", filter_message="**%s**"),
    'item_id': JSONMessageFilter("item_id", check_func=_default_item_id_flags_func),
    'location_id': JSONMessageFilter("location_id", filter_message="%s")
}
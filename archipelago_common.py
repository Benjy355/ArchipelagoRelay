import ssl
from json import JSONEncoder, JSONDecoder
import typing
import enum

#Straight up ripped from Archipelago below!

class Version(typing.NamedTuple):
    major: int
    minor: int
    build: int

    def as_simple_string(self) -> str:
        return ".".join(str(item) for item in self)

def get_any_version(data: dict) -> Version:
    data = {key.lower(): value for key, value in data.items()}  # .NET version classes have capitalized keys
    return Version(int(data["major"]), int(data["minor"]), int(data["build"]))

custom_hooks = {
    "Version": get_any_version
}

class NetworkPlayer(typing.NamedTuple):
    """Represents a particular player on a particular team."""
    team: int
    slot: int
    alias: str
    name: str

class ByValue:
    """
    Mixin for enums to pickle value instead of name (restores pre-3.11 behavior). Use as left-most parent.
    See https://github.com/python/cpython/pull/26658 for why this exists.
    """
    def __reduce_ex__(self, prot):
        return self.__class__, (self._value_, )

class SlotType(ByValue, enum.IntFlag):
    spectator = 0b00
    player = 0b01
    group = 0b10

    @property
    def always_goal(self) -> bool:
        """Mark this slot as having reached its goal instantly."""
        return self.value != 0b01


class NetworkSlot(typing.NamedTuple):
    """Represents a particular slot across teams."""
    name: str
    game: str
    type: SlotType
    group_members: typing.Union[typing.List[int], typing.Tuple] = ()  # only populated if type == group


class NetworkItem(typing.NamedTuple):
    item: int
    location: int
    player: int
    flags: int = 0

allowlist = {
    "NetworkPlayer": NetworkPlayer,
    "NetworkItem": NetworkItem,
    "NetworkSlot": NetworkSlot
}

def _object_hook(o: typing.Any) -> typing.Any:
    if isinstance(o, dict):
        hook = custom_hooks.get(o.get("class", None), None)
        if hook:
            return hook(o)
        cls = allowlist.get(o.get("class", None), None)
        if cls:
            for key in tuple(o):
                if key not in cls._fields:
                    del (o[key])
            return cls(**o)

    return o

decode = JSONDecoder(object_hook=_object_hook).decode

def tuplize_version(version: str) -> Version:
    return Version(*(int(piece, 10) for piece in version.split(".")))

__Archiversion__ = "0.4.4" #TODO: THIS IS SCUFFED LOL
version_tuple = tuplize_version(__Archiversion__)

def get_ssl_context():
    import certifi
    return ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=certifi.where())

_encode = JSONEncoder(
    ensure_ascii=False,
    check_circular=False,
    separators=(',', ':'),
).encode

def _scan_for_TypedTuples(obj: typing.Any) -> typing.Any:
    if isinstance(obj, tuple) and hasattr(obj, "_fields"):  # NamedTuple is not actually a parent class
        data = obj._asdict()
        data["class"] = obj.__class__.__name__
        return data
    if isinstance(obj, (tuple, list, set, frozenset)):
        return tuple(_scan_for_TypedTuples(o) for o in obj)
    if isinstance(obj, dict):
        return {key: _scan_for_TypedTuples(value) for key, value in obj.items()}
    return obj

def encode(obj: typing.Any) -> str:
    return _encode(_scan_for_TypedTuples(obj))

def flip_dict(input_dict):
    return {v: k for k, v in input_dict.items()}
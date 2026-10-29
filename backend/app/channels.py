"""Release-channel vocabulary.

A channel is a closed dimension; 78dm's mixed "series/grade" categories are
not channels. A product can only have one release channel.
"""

RELEASE_CHANNELS = ("regular", "pb", "limited", "event", "other")

RELEASE_CHANNEL_LABELS = {
    "regular": "通贩",
    "pb": "PB",
    "limited": "限定",
    "event": "会场",
    "other": "其他",
}

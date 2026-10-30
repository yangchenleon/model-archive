"""Release-channel vocabulary.

A channel is a closed dimension; 78dm's mixed "series/grade" categories are
not channels. A product can only have one release channel.
"""

RELEASE_CHANNELS = ("regular", "pb", "base", "event", "lottery", "limited")

RELEASE_CHANNEL_LABELS = {
    "regular": "通贩",
    "pb": "PB",
    "base": "基地",
    "event": "活动/会场",
    "lottery": "抽奖/一番赏",
    "limited": "限定",
}

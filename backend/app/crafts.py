"""Craft / finish vocabulary.

A craft is a single-value material/process attribute, not a combination. The
official edition label stays in products.edition; this field only records the
recognizable craft.
"""

CRAFTS = (
    "clear",
    "transparent",
    "plated",
    "clear_plated",
    "color_plated",
    "pearl",
    "metallic",
    "coating",
    "matte",
    "crystal",
    "luminous",
)

CRAFT_LABELS = {
    "clear": "彩透",
    "transparent": "透明",
    "plated": "电镀",
    "clear_plated": "电镀透明",
    "color_plated": "彩色电镀",
    "pearl": "珍珠/珠光",
    "metallic": "金属色",
    "coating": "特殊涂层",
    "matte": "消光",
    "crystal": "水晶",
    "luminous": "夜光",
}

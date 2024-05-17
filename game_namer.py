adjectives = [
    "Adorable", "Brave", "Clever", "Dangerous", "Energetic", "Fancy",
    "Graceful", "Happy", "Inventive", "Jolly", "Kind-hearted", "Lively",
    "Mysterious", "Nimble","Optimistic", "Powerful", "Quirky", "Resourceful",
    "Silly", "Talented", "Unique", "Vivacious", "Witty", "Xenodochial",
    "Youthful", "Zealous"
]

verbs = [
    "Attacking", "Blasting", "Conquering", "Defeating", "Exploring", "Fighting",
    "Grappling", "Hurdling", "Investigating", "Jumping", "Knocking", "Liberating",
    "Mastering", "Navigating", "Outwitting", "Pummeling", "Questing", "Rescuing",
    "Smashing", "Traversing", "Uncovering", "Vanquishing", "Winning", "eXterminating",
    "Yielding", "Zooming"
]
nouns = [
    "Aliens", "BFG", "Cucco", "Deku", "Epona", "Fairy",
    "Goron", "Hylian", "Ivysaur", "Jigglypuff", "Kakariko", "Link",
    "Master Sword", "Nukem", "Octorok", "Pikachu", "Quad Damage", "Rupee",
    "Shield", "Triforce", "Uranium Bullets", "Voltorb", "Wisdom", "Xerneas",
    "Yiga Clan", "Zubat"
]

import random

def name_game() -> str:
    return "%s %s %s %s" % (random.choice(adjectives), random.choice(nouns), random.choice(verbs), random.choice(nouns))
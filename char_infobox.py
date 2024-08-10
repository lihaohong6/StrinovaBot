from char_info.achievement import generate_achievements
from char_info.char_infobox import generate_infobox, generate_character_selector
from char_info.gallery import generate_emotes, generate_skins
from char_info.dorm import generate_gifts, generate_bond_items
from char_info.skills import generate_skills, generate_string_energy_network
from char_info.story import generate_biography, generate_return_letter

from char_info.weapons import generate_weapons


# def generate_quality_table():
#     quality_table = get_quality_table()
#     text = json.dumps(quality_table)
#     p = Page(s, "Module:CharacterGifts/rarity.json")
#     if p.text.strip() == text:
#         return
#     p.text = text
#     p.save(summary="update rarity data")


def main():
    f = {
        "infobox": generate_infobox,
        "weapons": generate_weapons,
        "skills": generate_skills,
        "biography": generate_biography,
        "return_letter": generate_return_letter,
        "emotes": generate_emotes,
        "skins": generate_skins,
        "string_energy_network": generate_string_energy_network,
        "bond_items": generate_bond_items,
        "gifts": generate_gifts,
        "character_selector": generate_character_selector,
        "achievements": generate_achievements
    }
    from sys import argv
    assert len(argv) == 2, ", ".join(f.keys())
    arg = argv[1]
    if arg in f:
        f[arg]()
    elif arg == "all":
        for func in f.values():
            func()
    else:
        print(f.keys())


if __name__ == "__main__":
    main()

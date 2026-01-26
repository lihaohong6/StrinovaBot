from char_info.char_infobox import make_infobox
from utils.general_utils import get_weapon_type, get_default_weapon_id, get_char_pages2, get_weapon_name
from utils.wiki_utils import save_json_page


def generate_character_selector():
    data = {}
    for char, page in get_char_pages2():
        char_info = make_infobox(char, page, save=False)
        weapon_id = get_default_weapon_id(char.id)
        weapon_type = get_weapon_type(weapon_id)
        data[char.name] = {
            'camp': char_info['Camp'],
            'role': char_info['Role'],
            'weapon': get_weapon_name(weapon_id),
            'weapon_type': weapon_type,
        }
    save_json_page("Module:Characters/data.json", data)


def main():
    generate_character_selector()


if __name__ == "__main__":
    main()

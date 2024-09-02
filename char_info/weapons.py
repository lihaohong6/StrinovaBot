import wikitextparser as wtp
from pywikibot import Page

from utils.general_utils import get_game_json, get_char_by_id, get_default_weapon_id, get_weapon_name, \
    get_weapon_type, get_char_pages
from utils.wiki_utils import s
from global_config import char_id_mapper


def generate_weapons():
    from utils.upload_utils import upload_weapon
    i18n = get_game_json()['Weapon']
    for char_id, char_name, p in get_char_pages():
        parsed = wtp.parse(p.text)
        t = None
        for template in parsed.templates:
            if template.name.strip() == "PrimaryWeapon":
                t = template
                break
        else:
            print(f"No template found on {char_name}")
            continue

        weapon_id = get_default_weapon_id(char_id)
        if weapon_id == -1:
            continue
        result = upload_weapon(char_name, weapon_id)
        if not result:
            continue

        try:
            weapon_name = get_weapon_name(weapon_id)
            weapon_description = i18n.get(f"{weapon_id}_Tips", "")
            weapon_type = get_weapon_type(weapon_id)
        except Exception as e:
            print(f"Failed to generate weapon for {char_name} due to {e}")
            continue

        def add_arg(name, value):
            if t.has_arg(name) and value.strip() == "":
                return
            t.set_arg(name, value + "\n")

        add_arg("Name", weapon_name)
        add_arg("Description", weapon_description)
        add_arg("Type", weapon_type)

        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate weapon", minor=True)

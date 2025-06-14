import wikitextparser as wtp
from pywikibot import Page

from global_config import Character
from utils.general_utils import get_default_weapon_id, get_weapon_name, \
    get_weapon_type, get_char_pages, get_char_pages2
from utils.json_utils import get_game_json
from utils.lang import ENGLISH, get_language
from utils.lang_utils import RedirectRequest, redirect_pages
from utils.wtp_utils import get_templates_by_name


def generate_weapons(pages: list[tuple[Character, Page]] = None):
    from utils.upload_utils import upload_weapon
    lang = get_language()
    i18n = get_game_json(lang)['Weapon']
    redirect_requests: list[RedirectRequest] = []
    save = False
    if pages is None:
        pages = get_char_pages2(lang=lang)
        save = True
    for char, p in pages:
        char_id = char.id
        char_name = char.name
        parsed = wtp.parse(p.text)
        templates = get_templates_by_name(parsed, "PrimaryWeapon")
        if len(templates) == 0:
            print(f"No template found on {p.title()}")
            continue
        t = templates[0]

        weapon_id = get_default_weapon_id(char_id)
        if weapon_id == -1:
            continue
        result = upload_weapon(char_name, weapon_id)
        if not result:
            continue

        try:
            weapon_name = get_weapon_name(weapon_id, lang)
            weapon_description = i18n.get(f"{weapon_id}_Tips", "")
            weapon_type = get_weapon_type(weapon_id)

            weapon_name_en = get_weapon_name(weapon_id, ENGLISH)
            assert weapon_name is not None and weapon_name_en is not None, f"Unexpected name CN: {weapon_name} and name EN: {weapon_name_en}"
            if weapon_name_en != weapon_name:
                redirect_requests.append(RedirectRequest(lang, weapon_name, weapon_name_en))
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
        if save:
            p.save(summary="generate weapon", minor=True)

    # Do NOT redirect: weapon pages are not yet ready
    # redirect_pages(redirect_requests)


if __name__ == '__main__':
    generate_weapons()

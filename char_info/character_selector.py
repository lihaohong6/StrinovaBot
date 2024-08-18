from char_info.char_infobox import make_infobox
from global_config import char_id_mapper
from utils.general_utils import get_game_json, get_char_by_id, get_role_profile, get_weapon_type, get_default_weapon_id


def generate_character_selector():
    i18n = get_game_json()['RoleProfile']
    char_list = []
    get_char_by_id(101)
    for char_id in char_id_mapper.keys():
        key = f'{char_id}_NameCn'
        role_profile = get_role_profile(char_id)
        char_name = i18n[key]
        char_list.append(make_infobox(char_id, char_name, role_profile, i18n, save=False))
    result = []

    def make_tr(lst: list[str]):
        return "<tr>" + "".join(f"<td>{e}</td>" for e in lst) + "</tr>"

    for r in sorted(char_list, key=lambda d: d['Camp']):
        name = r['Name']
        camp = r['Camp']
        weapon = get_weapon_type(get_default_weapon_id(r['Id']))
        result.append(make_tr([
            "{{ProfileImage|" + name + "}}",
            f"[[{name}]]",
            camp,
            r['Role'],
            weapon
        ]))

    print("\n".join(result))

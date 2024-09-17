from char_info.char_infobox import make_infobox
from global_config import char_id_mapper
from utils.general_utils import get_weapon_type, get_default_weapon_id


def generate_character_selector():
    char_list = []
    for char_id, char_name in char_id_mapper.items():
        char_list.append(make_infobox(char_id, char_name, save=False))
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

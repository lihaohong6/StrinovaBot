import re
from typing import Callable

import wikitextparser as wtp
from pywikibot import Page

from utils import get_game_json_cn, get_game_json_ja, camp_id_to_string, role_id_to_string, get_weapon_name, \
    get_default_weapon_id, get_game_json, get_char_by_id, get_role_profile, get_weapon_type
from wiki_utils import s
from global_config import char_id_mapper


def nop(x: str | list[str]):
    if isinstance(x, list):
        assert len(x) == 1
        return x[0]
    return x


def get_group_0(x: re.Match):
    if x is None:
        return ""
    return x.group(0)


infobox_args: list[tuple[list[str] | str, str, Callable[[list[str] | str], str]]] = [
    ("Birthday", "Birthday", nop),
    ("Constellation", "Constellation", nop),
    ("Age", "Age", lambda x: get_group_0(re.search(r"^\d+", x))),
    ("Height", "Height", nop),
    ("Weight", "Weight", nop),
    ("Apartment", "Home", nop),
    ("Title", "Title", nop),
    ("Desc", "Description", nop),
    (["Cv", "CvCn"], "VA", lambda x: f"JP: {x[0]}<br/>CN: {x[1]}"),
]


def make_infobox(char_id, char_name, char_profile, profile, save=True) -> dict:
    data: dict[str, str] = {}
    if save:
        p = Page(s, char_name)
        parsed = wtp.parse(p.text)
        for template in parsed.templates:
            if template.name.strip() == "CharacterInfobox":
                t = template
                break
        else:
            print("Template not found on " + char_name)
            return data
    else:
        t = wtp.Template("{{CharacterInfobox}}")

    def add_arg(name, value):
        value = str(value)
        if t.has_arg(name) and value.strip() == "":
            return
        t.set_arg(name, value + "\n")
        data[name] = value

    add_arg("Id", char_id)
    add_arg("Name", char_name)
    add_arg("NameEN", char_name)
    add_arg("NameCN", get_game_json_cn()['RoleProfile'][f'{char_id}_NameCn'])
    add_arg("NameJP", get_game_json_ja()['RoleProfile'][f'{char_id}_NameCn'])
    for args, key, mapper in infobox_args:
        def get_arg(arg: str) -> str:
            k = f"{char_id}_{arg}"
            return profile[k] if k in profile else ""

        if isinstance(args, list):
            arg_list = [get_arg(arg) for arg in args]
        else:
            arg_list = get_arg(args)
        add_arg(key, mapper(arg_list))
    try:
        add_arg("Camp", camp_id_to_string[char_profile['Team']])
        add_arg("Role", role_id_to_string[char_profile['Profession']])
        add_arg("Weapon", get_weapon_name(get_default_weapon_id(char_id)))
    except Exception:
        print("Insufficient info for " + char_name)
        return data
    if not save:
        return data
    if p.text.strip() == str(parsed).strip():
        return data
    p.save(summary="generate infobox")


def generate_infobox():
    profile = get_game_json()['RoleProfile']
    get_char_by_id(101)
    for char_id, char_profile in char_id_mapper.items():
        key = f'{char_id}_NameCn'
        if key not in profile:
            continue
        char_name = profile[key]
        make_infobox(char_id, char_name, char_profile, profile)


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

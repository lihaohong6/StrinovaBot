import re
from typing import Callable

import wikitextparser as wtp
from pywikibot import Page

from global_config import name_to_cn, Character
from utils.general_utils import get_table, get_char_pages, get_camp, get_role_name, get_char_pages2
from utils.json_utils import get_game_json, get_game_json_ja
from utils.lang import get_language


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
    # ("Birthday", "Birthday", nop),
    ("Constellation", "Constellation", nop),
    ("Age", "Age", lambda x: get_group_0(re.search(r"^\d+", x))),
    ("Height", "Height", nop),
    ("Weight", "Weight", nop),
    ("Apartment", "Home", nop),
    ("Title", "Title", nop),
    ("Desc", "Description", nop),
    # (["Cv", "CvCn"], "VA", lambda x: f"JP: {x[0]}<br/>CN: {x[1]}"),
]


def make_infobox(char, p: Page, save=True) -> dict:
    lang = get_language()
    i18n = get_game_json(lang)['RoleProfile']
    char_profile = get_table("RoleProfile")[char.id]
    data: dict[str, str] = {}
    parsed = wtp.parse(p.text)
    for template in parsed.templates:
        if template.name.strip() == "CharacterInfobox":
            t = template
            break
    else:
        if not save:
            t = wtp.Template("{{CharacterInfobox}}")
        else:
            print("Infobox template not found on " + p.title())
            return data
    def add_arg(name, value):
        value = str(value)
        if t.has_arg(name) and value.strip() == "":
            return
        if "NoTextFound" in value:
            value = ""
        t.set_arg(name, value + "\n")
        data[name] = value

    add_arg("Id", char.id)
    for args, key, mapper in infobox_args:
        def get_arg(arg: str) -> str:
            k = f"{char.id}_{arg}"
            return i18n.get(k, char_profile.get(arg, {}).get('SourceString', ''))

        if isinstance(args, list):
            arg_list = [get_arg(arg) for arg in args]
        else:
            arg_list = get_arg(args)
        add_arg(key, mapper(arg_list))
    try:
        add_arg("Camp", get_camp(char_profile['Team']))
        add_arg("CampText", get_camp(char_profile['Team'], lang=lang))
        add_arg("Role", get_role_name(char_profile['Profession']))
        add_arg("RoleText", get_role_name(char_profile['Profession'], lang=lang))
    except Exception as e:
        print("Insufficient info for " + char.name)
        print(e)
        return data
    if p.text.strip() != str(parsed).strip():
        p.text = str(parsed)
        if save:
            p.save(summary="generate infobox")
    return data


def generate_infobox(pages: list[tuple[Character, Page]] = None):
    language = get_language()
    save = False
    if pages is None:
        pages = get_char_pages2(lang=language)
        save = True
    for char, p in pages:
        make_infobox(char, p, save=save)


if __name__ == "__main__":
    generate_infobox()

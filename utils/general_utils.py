import re
from pathlib import Path

import requests

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from utils.asset_utils import csv_root, en_csv_root
from global_config import name_to_en, char_id_mapper, internal_names
from utils.json_utils import load_json, get_game_json
from utils.lang import Language, ENGLISH
from utils.wiki_utils import bwiki, s


def zh_name_to_en(o: str) -> str:
    if o in name_to_en:
        return name_to_en[o]
    first = o.split("·")[0]
    if first in name_to_en:
        return name_to_en[first]
    return None


en_name_to_zh: dict[str, str] = dict((v, k) for k, v in name_to_en.items())


def cn_name_to_en(cn: str) -> str | None:
    t = name_to_en | dict((k.split('·')[0], v) for k, v in name_to_en.items() if '·' in k)
    return t.get(cn, None)


def get_char_by_id(char_id: int) -> str:
    return char_id_mapper.get(char_id, None)


def get_id_by_char(char_name: str) -> int | None:
    for k, v in char_id_mapper.items():
        if v == char_name:
            return k
    return None


camp_id_to_string = {
    1: "Painting Utopia Security",
    2: "The Scissors",
    3: "Urbino",
}


def get_camp(camp_id: int, lang: Language = ENGLISH) -> str:
    if camp_id == 1 and lang == ENGLISH:
        return "Painting Utopia Security"
    return get_game_json(lang)['RoleTeam'][f'{camp_id}_NameCn']


camp_name_cn = {
    "欧泊": "Painting Utopia Security",
    "剪刀手": "The Scissors",
    "乌尔比诺": "Urbino"
}

role_id_to_string = {
    1: "Duelist",
    2: "Sentinel",
    3: "Support",
    4: "Initiator",
    5: "Controller"
}


def get_role_name(role_id: int, lang: Language = ENGLISH) -> str:
    return get_game_json(lang)['RoleProfession'][f'{role_id}_NameCn']


table_cache: dict[str, dict] = {}


def get_table(file_name: str) -> dict[int, dict]:
    if file_name in table_cache:
        return table_cache[file_name]
    table = dict((int(k), v) for k, v in load_json(csv_root / f"{file_name}.json")['Rows'].items())
    table_cache[file_name] = table
    return table


def get_table_en(file_name: str) -> dict[int, dict]:
    table_entry = "EN" + file_name
    if table_entry in table_cache:
        return table_cache[file_name]
    table = dict((int(k), v) for k, v in load_json(en_csv_root / f"{file_name}.json")['Rows'].items())
    table_cache[table_entry] = table
    return table


def get_default_weapon_id(char_id: int | str) -> int:
    char_id = int(char_id)
    if not hasattr(get_default_weapon_id, "dict"):
        get_default_weapon_id.dict = {}
        table = get_default_weapon_id.dict
        for k, v in get_table("Role").items():
            table[int(k)] = v['DefaultWeapon1']
    return get_default_weapon_id.dict.get(char_id, -1)


def get_weapon_name(weapon_id: int, lang: Language = ENGLISH) -> str:
    return get_game_json(lang)['Weapon'].get(f"{weapon_id}_Name", "")


def get_quality_table() -> dict[int, str]:
    if not hasattr(get_quality_table, "table"):
        t = {}
        get_quality_table.table = t
        for k, v in get_game_json()['ItemQualityRes'].items():
            quality = re.search(r"(\d)_Desc$", k)
            if quality is None:
                continue
            quality = int(quality.group(1))
            t[quality] = v

    return get_quality_table.table


def download_file(url, target: Path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        f = open(target, 'wb')
        for chunk in r.iter_content(chunk_size=16 * 1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
        f.close()


def get_cn_wiki_skins():
    from pywikibot import Page
    p = Page(bwiki(), "模块:皮肤/RoleSkinData")
    matches = re.findall(r'"([^"]+)"[^"]+\s+Role = "([^"]+)"', p.text)
    result = dict((match[0], match[1]) for match in matches)
    assert len(result) > 100
    return result


def get_weapon_type(weapon_id: int | str) -> str:
    weapon_id = int(weapon_id)
    return get_table("Weapon")[weapon_id]['Type'].split("::")[1]


def make_tab_group(original: str) -> str:
    return original.replace(" ", "").replace("-", "")


def get_char_pages(subpage_name: str = "", lang: Language = ENGLISH) -> list[tuple[int, str, Page]]:
    def get_page_name(char_name):
        return f"{char_name}{subpage_name}{lang.page_suffix}"

    pages = list(PreloadingGenerator(Page(s, get_page_name(v)) for k, v in char_id_mapper.items()))
    assert len(pages) == len(char_id_mapper)
    res = [(t[0], t[1], pages[index])
           for index, t in enumerate(char_id_mapper.items())
           if get_page_name(t[1]) == pages[index].title()]
    assert len(res) == len(char_id_mapper)
    return res


def get_bwiki_char_pages() -> list[tuple[int, str, Page]]:
    pages = list(PreloadingGenerator(Page(bwiki(), k) for k in name_to_en))
    assert len(pages) == len(name_to_en)
    res = [(internal_names[t[1]], t[1], pages[index])
           for index, t in enumerate(name_to_en.items())
           if t[0] == pages[index].title()]
    assert len(res) == len(char_id_mapper)
    return res

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from global_config import name_to_en, char_id_mapper, internal_names, get_characters, Character
from utils.json_utils import get_game_json, get_table_global
from utils.lang import Language, ENGLISH
from utils.wiki_utils import bwiki, s

en_name_to_zh: dict[str, str] = dict((v, k) for k, v in name_to_en.items())


def cn_name_to_en(cn: str) -> str | None:
    t = name_to_en | dict((k.split('·')[0], v) for k, v in name_to_en.items() if '·' in k)
    return t.get(cn, None)


def en_name_to_cn(en: str, short: str = True) -> str | None:
    result = en_name_to_zh.get(en, None)
    if result is None:
        return None
    if short:
        return result.split("·")[0]
    return result


def get_char_by_id(char_id: int) -> str:
    return char_id_mapper.get(char_id, None)


def get_id_by_char(char_name: str) -> int | None:
    for c in get_characters():
        if c.name == char_name:
            return c.id
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


def get_default_weapon_id(char_id: int | str) -> int:
    char_id = int(char_id)
    if not hasattr(get_default_weapon_id, "dict"):
        get_default_weapon_id.dict = {}
        table = get_default_weapon_id.dict
        for k, v in get_table_global("Role").items():
            table[int(k)] = v['DefaultWeapon1']
    return get_default_weapon_id.dict.get(char_id, -1)


def get_char_id_to_weapon_id() -> dict[int, int]:
    r = {}
    for char_id, char_name in char_id_mapper.items():
        weapon_id = get_default_weapon_id(char_id)
        r[char_id] = weapon_id
    return r


def get_weapon_name(weapon_id: int, lang: Language = ENGLISH) -> str | None:
    r = get_game_json(lang)['Weapon'].get(f"{weapon_id}_Name", None)
    if r is not None and r == '!NoTextFound!':
        r = None
    return r


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


def download_file(url: str, target: Path):
    headers = None
    if "miraheze" in url or "wikitide" in url:
        headers = {'User-Agent': 'Bot by User:PetraMagna', }
    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()
        f = open(target, 'wb')
        for chunk in r.iter_content(chunk_size=16 * 1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
        f.close()


def get_cn_wiki_skins():
    from pywikibot import Page
    p = Page(bwiki(), "模块:角色/SkinData")
    matches = re.findall(r'"([^"]+)"[^"]+\s+Role = "([^"]+)"', p.text)
    result = dict((match[0], match[1]) for match in matches)
    assert len(result) > 100
    return result


def get_weapon_type(weapon_id: int | str) -> str:
    weapon_id = int(weapon_id)
    return get_table_global("Weapon")[weapon_id]['Type'].split("::")[1]


def make_tab_group(original: str) -> str:
    return original.replace(" ", "").replace("-", "")


def get_char_pages(subpage_name: str = "", lang: Language = ENGLISH) -> list[tuple[int, str, Page]]:
    def get_page_name(char_name):
        return f"{char_name}{subpage_name}{lang.page_suffix}"

    characters = get_characters()
    pages = list(PreloadingGenerator(Page(s, get_page_name(c.name)) for c in characters))
    assert len(pages) == len(characters)
    res = [(c.id, c.name, pages[index])
           for index, c in enumerate(characters)
           if get_page_name(c.name) == pages[index].title()]
    assert len(res) == len(characters)
    return res


def get_char_pages2(subpage_name: str = "", lang: Language = ENGLISH) -> list[tuple[Character, Page]]:
    def get_page_name(char_name):
        return f"{char_name}{subpage_name}{lang.page_suffix}"

    characters = get_characters()
    pages = list(PreloadingGenerator(Page(s, get_page_name(c.name)) for c in characters))
    assert len(pages) == len(characters)
    res = [(c, pages[index])
           for index, c in enumerate(characters)
           if get_page_name(c.name) == pages[index].title()]
    assert len(res) == len(characters)
    return res


def get_bwiki_char_pages() -> list[tuple[int, str, Page]]:
    pages = list(PreloadingGenerator(Page(bwiki(), k) for k in name_to_en))
    assert len(pages) == len(name_to_en)
    res = [(internal_names[t[1]], t[1], pages[index])
           for index, t in enumerate(name_to_en.items())
           if t[0] == pages[index].title()]
    assert len(res) == len(char_id_mapper)
    return res


def parse_ticks(ts: int) -> datetime:
    t_0 = datetime(2023, 8, 3)
    seconds_passed = (ts - 638266176000000000) / 10000000
    return t_0 + timedelta(seconds=seconds_passed)


def split_dict(d: dict[Any, Any]) -> tuple[dict[Any, Any], dict[Any, Any]]:
    lst = list(d.items())
    assert len(lst) >= 2, f"{len(lst)} items in dict"
    mid_index = len(lst) // 2
    return dict(lst[:mid_index]), dict(lst[mid_index:])

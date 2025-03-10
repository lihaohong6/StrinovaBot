import dataclasses
import enum
import json
import re
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Any

import requests
from numba.core.ir_utils import visit_vars
from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from global_config import name_to_en, char_id_mapper, internal_names, get_characters, Character
from utils.asset_utils import csv_root, global_csv_root, string_table_root
from utils.json_utils import load_json, get_game_json
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


def get_string_table(file_name: str) -> dict[int, str]:
    if file_name in table_cache:
        return table_cache[file_name]
    table = load_json(string_table_root / f"{file_name}.json")['StringTable']['KeysToMetaData']
    table_cache[file_name] = table
    return table


def get_table_global(file_name: str) -> dict[int, dict]:
    table_entry = "EN" + file_name
    if table_entry in table_cache:
        return table_cache[table_entry]
    table = dict((int(k), v) for k, v in load_json(global_csv_root / f"{file_name}.json")['Rows'].items())
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
    return get_table("Weapon")[weapon_id]['Type'].split("::")[1]


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


def save_page(page: Page | str, text, summary: str = "update page"):
    if isinstance(page, str):
        page = Page(s, page)
    if page.text.strip() != text.strip():
        page.text = text
        page.save(summary=summary)


MergeFunction = Callable[[str | int | None, str | int | None], str | int]

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, enum.Enum):
            return o.value
        return super().default(o)


def dump_json(o):
    return json.dumps(o, indent=4, cls=EnhancedJSONEncoder)


def dump_minimal_json(o):
    return json.dumps(o, indent=None, separators=(',', ':'), cls=EnhancedJSONEncoder)


def obj_to_lua_string(obj):
    def lua_kv(key: Any, value: Any):
        if isinstance(key, int) or re.match(r"^\d+$", key):
            return f'[{key}]={dump_lua(value)}'
        if isinstance(key, str):
            return f'["{key}"]={dump_lua(value)}'

    def dump_lua(data):
        if type(data) is str:
            return f'"{data}"'
        if type(data) in (int, float):
            return f'{data}'
        if type(data) is bool:
            return data and "true" or "false"
        if type(data) is list:
            l = "{"
            l += ",\n".join([dump_lua(item) for item in data])
            l += "}"
            return l
        if type(data) is dict:
            t = "{"
            t += ",\n".join([lua_kv(k, v) for k, v in data.items()])
            t += "}"
            return t
        raise TypeError("Unsupported data type")
    return dump_lua(json.loads(dump_json(obj)))


def save_lua_table(page: Page | str, obj, summary: str = "update lua table"):
    lua_string = "return " + obj_to_lua_string(obj)
    if isinstance(page, str):
        page = Page(s, page)
    if page.text.strip() == lua_string.strip():
        return
    page.text = lua_string
    page.save(summary=summary)


def save_json_page(page: Page | str, obj, summary: str = "update json page", merge: bool | None | MergeFunction = False):

    if isinstance(page, str):
        page = Page(s, page)

    if page.text != "":
        original_json = json.loads(page.text)
        original = dump_json(original_json)
    else:
        original_json = {}
        original = ""
    if merge is not None and merge:
        def merge_function(s1: str | None, s2: str | None) -> str:
            if s1 is None:
                return s2
            if s2 is None:
                return s1
            def check_no_bot(string: str) -> bool:
                return re.search(r"nobot", string, re.IGNORECASE) is not None
            if check_no_bot(s1):
                return s1
            if check_no_bot(s2):
                return s2
            return s1
        obj = merge_dict2(json.loads(dump_json(obj)), original_json, merge=merge_function if merge is True else merge)
    modified = dump_json(obj)
    if original != modified:
        page.text = modified
        page.save(summary=summary)


def pick_two(a: str, b: str) -> str:
    """
    Pick a string. Prefer the first one but use the second one if the first is empty.
    :param a:
    :param b:
    :return:
    """
    if a is None:
        return b
    if b is None:
        return a
    if "NoTextFound" in a:
        a = ""
    if "NoTextFound" in b:
        b = ""
    if a.strip() in {"", "?", "彩蛋"}:
        return b
    return a


def pick_string(strings: list[str]) -> str:
    i = len(strings) - 2
    while i >= 0:
        strings[i] = pick_two(strings[i], strings[i + 1])
        i -= 1
    return strings[0]


def pick_string_length(a: str, b: str) -> str:
    if a is None:
        return b
    if b is None:
        return a
    if "NoTextFound" in a:
        return b
    if "NoTextFound" in b:
        return a
    if "nobot" in a.lower():
        return a
    if "nobot" in b.lower():
        return b
    if len(a) > len(b):
        return a
    return b


def merge_dict[K, V](a: dict[K, V], b: dict[K, V], check: bool = False, merge: Callable[[list[str]], str] = None) -> dict[K, V]:
    """
    Use b as the base dict and override with a whenever there's a conflict
    """
    result = deepcopy(b)
    for k, v in a.items():
        if isinstance(v, dict):
            if result.get(k) is None:
                result[k] = v
            else:
                result[k] = merge_dict(v, result[k])
        elif isinstance(v, str):
            if merge is not None:
                result[k] = merge([result.get(k, None), v])
            if not check or (v != "" and "NoTextFound" not in v):
                result[k] = v
        else:
            raise RuntimeError("Unexpected type")
    return result


def merge_dict2(a: dict, b: dict, merge: MergeFunction = pick_string_length) -> dict:
    """
    Use b as the base dict and override with a whenever there's a conflict (i.e. prioritize a)

    @:param merge: A function that prefers the first parameter
    """
    result = deepcopy(b)
    for k, v in a.items():
        if isinstance(v, dict):
            if result.get(k) is None:
                result[k] = v
            else:
                result[k] = merge_dict2(v, result[k], merge)
        elif isinstance(v, str) or isinstance(v, int):
            result[k] = merge(result.get(k, None), v)
        elif v is not None:
            raise RuntimeError("Unexpected type")
    return result


def parse_ticks(ts: int) -> datetime:
    t_0 = datetime(2023, 8, 3)
    seconds_passed = (ts - 638266176000000000) / 10000000
    return t_0 + timedelta(seconds=seconds_passed)


def split_dict(d: dict[Any, Any]) -> tuple[dict[Any, Any], dict[Any, Any]]:
    lst = list(d.items())
    assert len(lst) >= 2, f"{len(lst)} items in dict"
    mid_index = len(lst) // 2
    return dict(lst[:mid_index]), dict(lst[mid_index:])

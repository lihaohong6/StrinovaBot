import re
from pathlib import Path

import requests

import json
from asset_utils import csv_root, localization_root
from global_config import name_to_en, char_id_mapper
from wiki_utils import bwiki


def load_json(file: str | Path):
    return json.load(open(file, "r", encoding="utf-8"))


game_json = None


def get_game_json():
    global game_json
    if game_json is None:
        game_json = load_json(localization_root / "en/Game.json")
    return game_json


game_cn_json = None


def get_game_json_cn():
    global game_cn_json
    if game_cn_json is None:
        game_cn_json = load_json(localization_root / "zh-Hans/Game.json")
    return game_cn_json


game_ja_json = None


def get_game_json_ja():
    global game_ja_json
    if game_ja_json is None:
        game_ja_json = load_json("json/GameJa.json")
    return game_ja_json


def zh_name_to_en(o: str) -> str:
    if o in name_to_en:
        return name_to_en[o]
    first = o.split("·")[0]
    if first in name_to_en:
        return name_to_en[first]
    return None


en_name_to_zh: dict[str, str] = dict((v, k) for k, v in name_to_en.items())


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

role_id_to_string = {
    1: "Duelist",
    2: "Sentinel",
    3: "Support",
    4: "Initiator",
    5: "Controller"
}

table_cache: dict[str, dict] = {}


def get_table(file_name: str) -> dict[int, dict]:
    if file_name in table_cache:
        return table_cache[file_name]
    table = dict((int(k), v) for k, v in load_json(csv_root / f"{file_name}.json")[0]['Rows'].items())
    table_cache[file_name] = table
    return table


def get_role_profile(char_id: int) -> dict:
    return get_table("RoleProfile")[char_id]


def get_default_weapon_id(char_id: int | str) -> int:
    char_id = int(char_id)
    if not hasattr(get_default_weapon_id, "dict"):
        get_default_weapon_id.dict = {}
        table = get_default_weapon_id.dict
        for k, v in get_table("Role").items():
            table[int(k)] = v['DefaultWeapon1']
    return get_default_weapon_id.dict.get(char_id, -1)


def get_weapon_name(weapon_id: int) -> str:
    return get_game_json()['Weapon'].get(f"{weapon_id}_Name", "")


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
    r = requests.get(url)
    f = open(target, 'wb')
    for chunk in r.iter_content(chunk_size=512 * 1024):
        if chunk:  # filter out keep-alive new chunks
            f.write(chunk)
    f.close()


def get_cn_wiki_skins():
    from pywikibot import Page
    p = Page(bwiki(), "模块:皮肤/RoleSkinData")
    matches = re.findall(r'\["([^"]+)"][^"]+Role = "([^"]+)"', p.text)
    return dict((match[0], match[1]) for match in matches)


def get_weapon_type(weapon_id: int | str) -> str:
    weapon_id = int(weapon_id)
    return get_table("Weapon")[weapon_id]['Type'].split("::")[1]


def make_tab_group(original: str) -> str:
    return original.replace(" ", "").replace("-", "")
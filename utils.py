import re
from pathlib import Path

import requests
from pywikibot import Site

import json


def bwiki():
    return Site(code="bwiki")


def load_json(file: str):
    return json.load(open(file, "r", encoding="utf-8"))


game_json = None


def get_game_json():
    global game_json
    if game_json is None:
        game_json = load_json("json/Game.json")
    return game_json


game_cn_json = None


def get_game_json_cn():
    global game_cn_json
    if game_cn_json is None:
        game_cn_json = load_json("json/GameCn.json")
    return game_cn_json


game_ja_json = None


def get_game_json_ja():
    global game_ja_json
    if game_ja_json is None:
        game_ja_json = load_json("json/GameJa.json")
    return game_ja_json


name_to_en: dict[str, str] = {
    "米雪儿·李": "Michele",
    "信": "Nobunaga",
    "心夏": "Kokona",
    "伊薇特": "Yvette",
    "芙拉薇娅": "Flavia",
    "明": "Ming",
    "拉薇": "Lawine",
    "梅瑞狄斯": "Meredith",
    "令": "Reiichi",
    "香奈美": "Kanami",
    "艾卡": "Eika",
    "加拉蒂亚": "Galatea",
    "奥黛丽": "Audrey",
    "玛德蕾娜": "Maddelena",
    "绯莎": "Fuchsia",
    "星绘": "Celestia",
    "白墨": "Bai Mo"
}


def zh_name_to_en(o: str) -> str:
    if o in name_to_en:
        return name_to_en[o]
    first = o.split("·")[0]
    if first in name_to_en:
        return name_to_en[first]
    return None


en_name_to_zh: dict[str, str] = dict((v, k) for k, v in name_to_en.items())

char_id_mapper: dict[int, str] = {}


def get_char_by_id(char_id: int) -> str:
    if len(char_id_mapper) == 0:
        for k, v in get_game_json()['RoleProfile'].items():
            if "_NameCn" not in k:
                continue
            char_id_mapper[int(re.search(r'^\d+', k).group(0))] = v
    return char_id_mapper[char_id]


camp_id_to_string = {
    1: "Painting Utopia Society",
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


def get_role_profile(char_id: int) -> dict:
    if not hasattr(get_role_profile, "dict"):
        get_role_profile.dict = {}
        d = get_role_profile.dict

        for k, v in load_json(f"json/CSV/RoleProfile.json")[0]['Rows'].items():
            d[int(k)] = v

    return get_role_profile.dict[char_id]


def get_default_weapon_id(char_id: int) -> int:
    if not hasattr(get_default_weapon_id, "dict"):
        get_default_weapon_id.dict = {}
        table = get_default_weapon_id.dict
        for k, v in load_json("json/CSV/Role.json")[0]['Rows'].items():
            table[int(k)] = v['DefaultWeapon1']
    return get_default_weapon_id.dict.get(char_id, -1)


def get_weapon_name(weapon_id: int) -> str:
    return get_game_json()['Weapon'].get(f"{weapon_id}_Name", "")


def get_weapon_table() -> dict:
    if not hasattr(get_weapon_table, "table"):
        get_weapon_table.table = dict((int(k), v) for k, v in load_json("json/CSV/Weapon.json")[0]['Rows'].items())

    return get_weapon_table.table


def get_skill_table() -> dict:
    if not hasattr(get_skill_table, "table"):
        get_skill_table.table = dict((int(k), v) for k, v in load_json("json/CSV/Skill.json")[0]['Rows'].items())

    return get_skill_table.table


def get_goods_table() -> dict:
    if not hasattr(get_goods_table, "table"):
        get_goods_table.table = dict((int(k), v) for k, v in load_json("json/CSV/Goods.json")[0]['Rows'].items())

    return get_goods_table.table


def download_file(url, target: Path):
    r = requests.get(url)
    f = open(target, 'wb')
    for chunk in r.iter_content(chunk_size=512 * 1024):
        if chunk: # filter out keep-alive new chunks
            f.write(chunk)
    f.close()

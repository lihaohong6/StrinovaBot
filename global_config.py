from dataclasses import dataclass

characters_with_dorms = {"Michele", "Kokona", "Yvette", "Lawine", "Kanami", "Celestia", "Audrey", "Maddelena",
                         "Fuchsia"}
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
    "加拉蒂亚·利里": "Galatea",
    "奥黛丽·格罗夫": "Audrey",
    "玛德蕾娜·利里": "Maddelena",
    "绯莎": "Fuchsia",
    "星绘": "Celestia",
    "白墨": "Bai Mo",
    "珐格兰丝": "Fragrans",
    "忧雾": "Yugiri",
    "蕾欧娜": "Leona",
}

name_to_cn: dict[str, str] = dict((v, k) for k, v in name_to_en.items())

@dataclass
class Character:
    id: int
    name: str

char_id_mapper: dict[int, str] = {101: 'Michele', 105: 'Audrey', 107: 'Maddelena', 108: 'Nobunaga', 109: 'Reiichi',
                                  110: 'Bai Mo', 112: 'Fuchsia', 115: 'Flavia', 119: 'Eika', 120: 'Fragrans',
                                  121: 'Yugiri',
                                  123: 'Leona',
                                  124: 'Kokona',
                                  128: 'Lawine', 131: 'Yvette', 132: 'Ming', 133: 'Meredith', 137: 'Kanami',
                                  146: 'Celestia',
                                  205: 'Galatea'}

def get_characters() -> list[Character]:
    return [Character(k, v) for k, v in char_id_mapper.items()]

internal_names: dict[str, int] = dict((c.name, c.id)for c in get_characters())
internal_names.update({"HuiXing": 146, "MoBai": 110, "Aika": 119, "Michelle": 101})

def is_valid_char_name(name: str) -> bool:
    chars = get_characters()
    for c in chars:
        if c.name == name:
            return True
    return False

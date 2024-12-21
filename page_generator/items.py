import re
from dataclasses import dataclass, field
from functools import cache

from audio.audio_parser import Voice, role_voice, parse_role_voice
from char_info.gallery import parse_skin_tables, SkinInfo, Emote, parse_emotes
from page_generator.badges import get_all_badges, Badge
from page_generator.decal import get_all_decals, Decal
from page_generator.id_card import get_all_id_cards, IdCard
from page_generator.weapons import Weapon, parse_weapons
from utils.general_utils import get_table, save_json_page, get_table_global, merge_dict2
from utils.json_utils import get_all_game_json
from utils.lang import CHINESE, ENGLISH
from utils.lang_utils import get_multilanguage_dict


@dataclass
class Item:
    id: int
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    quality: int = -1
    type: int = -1
    icon_id: int = -1

    @property
    def file(self):
        use_id = self.icon_id
        if use_id == -1:
            use_id = self.id
        return f"File:Item Icon {use_id}.png"

    @property
    def icon(self):
        return self.file


def localize_items(items: list[Item]):
    i18n = merge_dict2(get_all_game_json("Item"), get_all_game_json("Goods"))
    for item in items:
        item.name |= get_multilanguage_dict(i18n, f"{item.id}_Name")
        item.description |= get_multilanguage_dict(i18n, f"{item.id}_Desc")


@cache
def parse_items() -> dict[int, Item]:
    items: dict[int, Item] = {}

    def process_json(d: dict):
        for item_id, v in d.items():
            if isinstance(item_id, list):
                item_id = item_id[0]
            item = Item(item_id)
            item.name[CHINESE.code] = v['Name']['SourceString']
            item.description[CHINESE.code] = v['Desc'].get("SourceString", "")
            item.quality = v['Quality']
            item.type = v['ItemType']
            search_result = re.search(r"Item_(\d+)$", v.get('IconItem', {}).get('AssetPathName', ''))
            if search_result is not None:
                item.icon_id = int(search_result.group(1))
            items[item_id] = item

    process_json(get_table("Item"))
    process_json(get_table("Goods"))
    process_json(get_table_global("Item"))

    localize_items(list(items.values()))
    return items


@cache
def parse_currencies() -> dict[int, Item]:
    i18n = get_all_game_json("Currency")
    currencies: dict[int, Item] = {}
    for k, v in get_table("Currency").items():
        item = Item(k)
        item.name = get_multilanguage_dict(i18n, f"{k}_Name")
        item.description = get_multilanguage_dict(i18n, f"{k}_Desc")
        item.quality = v['Quality']
        currencies[item.id] = item
    return currencies


@cache
def get_all_items() -> dict[int, Item | Badge | Decal | SkinInfo | Weapon | Emote | IdCard]:
    currencies = parse_currencies()
    items = parse_items()
    badges = get_all_badges()
    decals = get_all_decals()
    id_cards = get_all_id_cards()
    skins: dict[int, SkinInfo] = {}
    for _, skin_list in parse_skin_tables().items():
        for skin in skin_list:
            for sid in skin.id:
                skins[sid] = skin
    weapons: dict[int, Weapon] = parse_weapons()
    emotes: dict[int, Emote] = {}
    for _, emote_list in parse_emotes().items():
        for emote in emote_list:
            emotes[emote.id] = emote
    voices: dict[int, Voice] = {}
    for vid, v in parse_role_voice().items():
        voices[vid] = v
    # increasing order of specificity
    return items | skins | badges | decals | id_cards | weapons | emotes | voices | currencies


@cache
def get_en_items() -> dict[str, Item]:
    items = get_all_items()
    result = {}
    for item in items.values():
        name_en = item.name.get(ENGLISH.code, None)
        if name_en is None:
            continue
        result[name_en] = item
    return result


def get_item(item: str | int) -> Item:
    items = get_all_items()
    if type(item) is int:
        return items[item]
    en_items = get_en_items()
    return en_items[item]


def save_all_items():
    items = get_en_items()
    result = {}
    for name_en, item in items.items():
        result[name_en] = {
            'id': item.id,
            'name': {
                'en': name_en,
            },
            'icon': item.icon,
            'quality': item.quality,
        }
    save_json_page("Module:Item/data.json", result)


def main():
    save_all_items()


if __name__ == '__main__':
    main()
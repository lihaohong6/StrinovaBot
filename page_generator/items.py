import re
from dataclasses import dataclass, field
from functools import cache

from audio.audio_parser import parse_role_voice
from audio.voice import Voice
from char_info.gallery import parse_skin_tables, SkinInfo
from char_info.emote import Emote, parse_emotes
from page_generator.badges import get_all_badges, Badge
from page_generator.chat_bubbles import ChatBubble, parse_chat_bubbles
from page_generator.decal import get_all_decals, Decal
from page_generator.id_card import get_all_id_cards, IdCard
from page_generator.weapons import Weapon, parse_weapons
from utils.dict_utils import merge_dict2
from utils.json_utils import get_all_game_json, get_table, get_table_global
from utils.lang import ENGLISH
from utils.lang_utils import get_text
from utils.wiki_utils import save_json_page


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


@cache
def parse_items() -> dict[int, Item]:
    items: dict[int, Item] = {}
    i18n = merge_dict2(get_all_game_json("Item"), get_all_game_json("Goods"))

    def process_json(d: dict):
        for item_id, v in d.items():
            if isinstance(item_id, list):
                item_id = item_id[0]
            item = Item(item_id)
            item.name = get_text(i18n, v['Name'])
            item.description = get_text(i18n, v['Desc'])
            item.quality = v['Quality']
            item.type = v['ItemType']
            search_result = re.search(r"Item_(\d+)$", v.get('IconItem', {}).get('AssetPathName', ''))
            if search_result is not None:
                item.icon_id = int(search_result.group(1))
            items[item_id] = item

    process_json(get_table("Item"))
    process_json(get_table("Goods"))
    process_json(get_table_global("Item"))
    return items


@cache
def parse_currencies() -> dict[int, Item]:
    i18n = get_all_game_json("Currency")
    currencies: dict[int, Item] = {}
    for k, v in get_table("Currency").items():
        item = Item(k)
        item.name = get_text(i18n, v['Name'])
        item.description = get_text(i18n, v['Desc'])
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
        skin_list: list[SkinInfo]
        for skin in skin_list:
            skins[skin.id] = skin
    weapons: dict[int, Weapon] = parse_weapons()
    emotes: dict[int, Emote] = {}
    for _, emote_list in parse_emotes().items():
        for emote in emote_list:
            emotes[emote.id] = emote
    voices: dict[int, Voice] = {}
    for vid, v in parse_role_voice().items():
        voices[vid] = v
    chat_bubbles: dict[int, ChatBubble] = {}
    for b in parse_chat_bubbles():
        chat_bubbles[b.id] = b
    # increasing order of specificity
    return items | skins | badges | decals | id_cards | weapons | emotes | voices | currencies | chat_bubbles


@cache
def get_en_items() -> list[Item]:
    items = get_all_items()
    result = []
    for item in items.values():
        name_en = item.name.get(ENGLISH.code, None)
        if name_en is None:
            continue
        result.append(item)
    return result


def save_all_items():
    items = get_en_items()
    result_name = {}
    result_id = {}
    for item in items:
        if isinstance(item.id, list):
            item_id = item.id[0]
        else:
            item_id = item.id
        name_en = item.name.get(ENGLISH.code, None)
        if name_en not in result_name:
            result_name[name_en] = item_id
        result_id[item_id] = {
            'name': {
                'en': name_en,
            },
            'icon': item.icon,
            'quality': item.quality,
        }
    save_json_page("Module:Item/by_name.json", result_name)
    save_json_page("Module:Item/by_id.json", result_id)


def main():
    save_all_items()


if __name__ == '__main__':
    main()
from dataclasses import dataclass, field
from functools import cache

from audio.audio_parser import Voice, role_voice
from char_info.gallery import parse_skin_tables, SkinInfo, Emote, parse_emotes
from page_generator.badges import get_all_badges, Badge
from page_generator.decal import get_all_decals, Decal
from page_generator.id_card import get_all_id_cards, IdCard
from page_generator.weapons import Weapon, parse_weapons
from utils.general_utils import get_table
from utils.json_utils import get_all_game_json
from utils.lang import CHINESE
from utils.lang_utils import get_multilanguage_dict


@dataclass
class Item:
    id: int
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    quality: int = -1
    type: int = -1

    @property
    def file(self):
        return f"File:Item Icon {self.id}.png"

    @property
    def icon(self):
        return self.file


def localize_items(items: list[Item]):
    table_name = "Item"
    i18n = get_all_game_json(table_name)
    for item in items:
        item.name |= get_multilanguage_dict(i18n, f"{item.id}_Name")
        item.description |= get_multilanguage_dict(i18n, f"{item.id}_Desc")


@cache
def parse_items() -> dict[int, Item]:
    item_json = get_table("Item")
    items: dict[int, Item] = {}
    for item_id, v in item_json.items():
        item = Item(item_id)
        item.name[CHINESE.code] = v['Name']['SourceString']
        item.description[CHINESE.code] = v['Desc'].get("SourceString", "")
        item.quality = v['Quality']
        item.type = v['ItemType']
        items[item_id] = item
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
    for vid, v in role_voice().items():
        voices[vid] = v
    return currencies | items | badges | decals | id_cards | skins | weapons | emotes | voices


def main():
    pass


if __name__ == '__main__':
    main()
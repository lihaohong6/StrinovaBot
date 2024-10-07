from dataclasses import dataclass, field
from pathlib import Path

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


def localize_items(items: list[Item]):
    table_name = "Item"
    i18n = get_all_game_json(table_name)
    for item in items:
        item.name |= get_multilanguage_dict(i18n, f"{item.id}_Name")
        item.description |= get_multilanguage_dict(i18n, f"{item.id}_Desc")


def get_all_items() -> dict[int, Item]:
    item_json = get_table("Item")
    items: dict[int, Item] = {}
    for item_id, v in item_json.items():
        item = Item(item_id)
        items[item_id] = item
        item.name[CHINESE.code] = v['Name']['SourceString']
        item.description[CHINESE.code] = v['Desc']['SourceString']
        item.quality = v['Quality']
        item.type = v['ItemType']
    localize_items(list(items.values()))
    return items


def main():
    pass


if __name__ == '__main__':
    main()
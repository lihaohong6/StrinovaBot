from dataclasses import dataclass
from datetime import datetime

from global_config import char_id_mapper
from page_generator.items import Item, get_all_items
from utils.general_utils import get_table_global, parse_ticks, get_table
from utils.json_utils import get_all_game_json
from utils.lang import ENGLISH
from utils.lang_utils import get_multilanguage_dict


@dataclass
class Banner:
    name: dict[str, str]
    role_id: int
    group: int
    start: datetime
    end: datetime

    def __str__(self):
        def filter_date(d: datetime):
            return d if d.year >= 2024 else "?"
        return (f";{self.name[ENGLISH.code]}\n"
                f"*Character: [[{char_id_mapper[self.role_id]}]]\n"
                f"*Start: {filter_date(self.start)}\n"
                f"*End: {filter_date(self.end)}")


def parse_banners() -> list[Banner]:
    i18n = get_all_game_json("Lottery")
    result = []
    for k, v in get_table_global("Lottery").items():
        if v['Type'] != 1:
            continue
        name = get_multilanguage_dict(i18n, f"{k}_Name")
        if len(name) == 0:
            continue

        role_id = v['RoleId']

        start = parse_ticks(v['Start']['Ticks'])
        end = parse_ticks(v['Finish']['Ticks'])
        result.append(Banner(name, role_id, v['NormalDrop'], start, end))
    return result


def generate_gacha_page():
    banners = parse_banners()
    print("\n".join(map(str, banners)))


@dataclass
class GachaDrop:
    item: Item
    quantity: int


def parse_gacha_drops() -> dict[int, list[GachaDrop]]:
    items = get_all_items()
    result: dict[int, list[GachaDrop]] = {}
    for drop_id, v in get_table_global("LotteryDrop").items():
        gacha_id = v['GroupId']
        if gacha_id not in result:
            result[gacha_id] = []
        drops = v['Items']
        assert len(drops) == 1, f"More than one drop: {drops}"
        drop = drops[0]
        item = items[drop['ItemId']]
        quantity = drop['ItemAmount']
        result[gacha_id].append(GachaDrop(item, quantity))
    return result


def make_gacha_page():
    banners = parse_banners()
    all_drops = parse_gacha_drops()
    for banner in banners:
        drops = all_drops[banner.group]
        print('<div style="display:flex; flex-wrap: wrap; gap: 5px">')
        for drop in drops:
            print(f"{{{{BattlePassReward|Level={drop.item.quality}|File={drop.item.icon.replace('File:', '').replace('.png', '')}|Name={drop.item.name[ENGLISH.code]}}}}}")
        print('</div>')



def main():
    make_gacha_page()


if __name__ == '__main__':
    main()
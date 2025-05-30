from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cache

from char_info.gallery import SkinInfo, parse_skin_tables
from page_generator.items import Item, get_all_items
from utils.general_utils import parse_ticks
from utils.json_utils import get_all_game_json, get_table, get_table_global
from utils.lang import ENGLISH, CHINESE
from utils.lang_utils import compose, StringConverters, get_text
from utils.wiki_utils import save_json_page


@dataclass
class Banner:
    name: dict[str, str]
    role_id: int
    group: int
    start: datetime
    end: datetime

    def __str__(self):
        def filter_date(d: datetime):
            return d if d.year >= 2023 else "?"

        return (f"=={self.name.get(ENGLISH.code, self.name.get(CHINESE.code))}==\n"
                f"*Start: {filter_date(self.start)}\n"
                f"*End: {filter_date(self.end)}\n"
                "{{#invoke:Gacha|main|" + str(self.group) + "|en|cn=1}}")


def parse_banners(use_cn: bool = False) -> list[Banner]:
    i18n = get_all_game_json("Lottery")
    result = []
    table = get_table("Lottery").items() if use_cn else get_table_global("Lottery").items()
    for k, v in table:
        if v['Type'] != 1:
            continue
        name = get_text(i18n, v['Name'],
                        converter=compose(StringConverters.basic_converter,
                                          StringConverters.all_caps_remove))
        if len(name) == 0:
            continue

        role_id = v['RoleId']

        start = parse_ticks(v['Start']['Ticks'])
        end = parse_ticks(v['Finish']['Ticks'])
        result.append(Banner(name, role_id, v['NormalDrop'], start, end))
    return result


@cache
def reverse_skin_lookup_table() -> dict[int, str]:
    skins = parse_skin_tables()
    result = {}
    for char_name, skin_list in skins.items():
        skin_list: list[SkinInfo]
        for skin in skin_list:
            result[skin.id] = char_name
    return result


def get_role_legendary_skin(banner_id: int) -> str:
    for drop in parse_gacha_drops()[banner_id]:
        if drop.item.quality == 5 and isinstance(drop.item, SkinInfo):
            role_name = reverse_skin_lookup_table()[drop.item.id]
            return drop.item.get_mh_portrait_title(role_name)
    print(f"WARNING: No legendary skin found for banner {banner_id}")
    return ""


def banners_to_serializable(banners: list[Banner]) -> list[dict]:
    result = []
    for b in banners:
        d = {
            "name": b.name,
            "start": str(b.start),
            "end": str(b.end),
            "image": get_role_legendary_skin(b.group),
            "group": b.group
        }
        result.append(d)
    return result


def make_gacha_banners():
    banners = parse_banners(use_cn=False)
    # Use this to remove long-running banners (e.g. targeted reconstruction, banners with gibberish dates)
    banners = [b for b in banners
               if b.end.year >= 2024 and (b.end - b.start) <= timedelta(days=90)]
    banners.sort(key=lambda b: b.start)
    obj = banners_to_serializable(banners)
    save_json_page("Module:Gacha/banners.json", obj)


@dataclass
class GachaDrop:
    item: Item
    quantity: int

    def to_dict(self) -> dict:
        return {
            'id': self.item.id,
            'name': self.item.name,
            'quality': self.item.quality,
            'quantity': self.quantity,
            'icon': self.item.icon,
        }


def parse_gacha_drops(use_cn: bool = False) -> dict[int, list[GachaDrop]]:
    items = get_all_items()
    result: dict[int, list[GachaDrop]] = {}
    table = get_table("LotteryDrop") if use_cn else get_table_global("LotteryDrop")
    for drop_id, v in table.items():
        gacha_id = v['GroupId']
        if gacha_id not in result:
            result[gacha_id] = []
        drops = v['Items']
        assert len(drops) == 1, f"More than one drop: {drops}"
        drop = drops[0]
        item = items.get(drop['ItemId'], None)
        if item is None:
            print(f"ERROR: item with id {drop['ItemId']} not found")
            continue
        quantity = drop['ItemAmount']
        result[gacha_id].append(GachaDrop(item, quantity))
    return result


def save_gacha_drop_json(use_cn: bool = False):
    all_drops = parse_gacha_drops(use_cn)
    result = {}
    for group_id in all_drops:
        result[group_id] = [d.to_dict() for d in
                            sorted(all_drops[group_id], key=lambda x: x.item.quality, reverse=True)]
    page_name = "Module:Gacha/drops_cn.json" if use_cn else "Module:Gacha/drops.json"
    save_json_page(page_name, result)


def make_gacha_drop_data():
    save_gacha_drop_json(use_cn=False)
    save_gacha_drop_json(use_cn=True)


def main():
    make_gacha_drop_data()
    make_gacha_banners()


if __name__ == '__main__':
    main()

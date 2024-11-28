from dataclasses import dataclass

from page_generator.items import get_all_items, Item
from utils.general_utils import get_table


@dataclass
class GachaDrop:
    item: Item
    quantity: int


def parse_gacha_drops() -> dict[int, list[GachaDrop]]:
    items = get_all_items()
    result: dict[int, list[GachaDrop]] = {}
    for drop_id, v in get_table("LotteryDrop").items():
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


def main():
    parse_gacha_drops()

if __name__ == '__main__':
    main()
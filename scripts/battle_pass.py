from dataclasses import dataclass

from page_generator.items import get_all_items, Item
from utils.general_utils import get_table, get_table_global, save_json_page, save_page
from utils.lang import ENGLISH, CHINESE, Language, LanguageVariants


@dataclass
class BattlePassReward:
    item: Item
    amount: int
    type: int


@dataclass
class BattlePassLevel:
    id: int
    season: int
    level: int
    rewards: list[BattlePassReward]


def parse_battle_pass(use_cn: bool = False) -> dict[int, list[BattlePassLevel]]:
    all_items = get_all_items()
    result = {}
    if use_cn:
        table = get_table("BattlePassPrize")
    else:
        table = get_table_global("BattlePassPrize")
    for k, v in table.items():
        season: int = v['Season']
        if season not in result:
            result[season] = []
        level = v['Id']
        rewards = []
        for prize_type, prize_list in enumerate([v['Prize1'], v['Prize2']], 1):
            for prize in prize_list:
                item_id = prize['ItemId']
                item_amount = prize['ItemAmount']
                if item_id not in all_items:
                    print(f"{item_id} not found")
                    continue
                item = all_items[item_id]
                rewards.append(BattlePassReward(item, item_amount, prize_type))
        result[season].append(BattlePassLevel(int(k), season, level, rewards))
    return result


def generate_battle_pass(use_cn: bool = False) -> str:
    result = []
    for season, battle_pass_levels in parse_battle_pass(use_cn).items():
        battle_pass_levels.sort(key=lambda x: x.level)
        result.append(f"==Season {season}==")
        result.append("{{BattlePass|")
        for r in battle_pass_levels:
            level = r.level
            for reward in r.rewards:
                file = reward.item.icon.replace("File:", "").replace(".png", "")
                name_dict = reward.item.name
                name = name_dict.get(ENGLISH.code,
                                     name_dict.get(CHINESE.code,
                                                   name_dict.get(LanguageVariants.SIMPLIFIED_CHINESE.value.code, "")))
                free = reward.type == 1
                if reward.amount != 1:
                    name = name + f" x {reward.amount}"
                result.append("{{BattlePassReward|"
                              f"Level={level}|File={file}|Name={name}" + ("|Free=1" if free else "") +
                              "}}")
        result.append("}}")
    return "\n".join(result)


def main():
    generate_battle_pass()
    save_page("Battle Pass/CN", generate_battle_pass(True))


if __name__ == '__main__':
    main()

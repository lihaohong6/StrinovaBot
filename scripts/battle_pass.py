from dataclasses import dataclass
from typing import Any

from page_generator.items import get_all_items
from utils.general_utils import get_table, get_table_global


@dataclass
class BattlePassReward:
    item: Any
    amount: int
    type: int


@dataclass
class BattlePassLevel:
    id: int
    season: int
    level: int
    rewards: list[BattlePassReward]

def parse_battle_pass() -> list[BattlePassLevel]:
    all_items = get_all_items()
    result = []
    for k, v in get_table_global("BattlePassPrize").items():
        season = v['Season']
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
        result.append(BattlePassLevel(int(k), season, level, rewards))
    return result


def generate_battle_pass():
    battle_pass_levels = parse_battle_pass()
    battle_pass_levels.sort(key=lambda x: x.level)
    result = ["{{BattlePass|"]
    for r in battle_pass_levels:
        level = r.level
        for reward in r.rewards:
            file = reward.item.icon.replace("File:", "").replace(".png", "")
            name = reward.item.name['en']
            free = reward.type == 1
            if reward.amount != 1:
                name = name + f" x {reward.amount}"
            result.append("{{BattlePassReward|"
                          f"Level={level}|File={file}|Name={name}" + ("|Free=1" if free else "") +
                          "}}")
    result.append("}}")
    print("\n".join(result))


def main():
    generate_battle_pass()

if __name__ == '__main__':
    main()
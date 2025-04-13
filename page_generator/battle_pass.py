import re
from dataclasses import dataclass

from page_generator.items import get_all_items, Item
from utils.general_utils import parse_ticks
from utils.json_utils import get_all_game_json, get_table, get_table_global
from utils.lang import ENGLISH, CHINESE, LanguageVariants
from utils.lang_utils import get_text, get_english_version
from utils.wiki_utils import save_page, save_json_page


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


@dataclass
class BattlePassSeason:
    id: int
    name: dict[str, str]
    start: str
    end: str
    image: str


def parse_battle_pass_rewards(use_cn: bool = False) -> dict[int, list[BattlePassLevel]]:
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


def parse_battle_pass_seasons() -> list[BattlePassSeason]:
    i18n = get_all_game_json("BattlePassSeason_I18N")
    result: list[BattlePassSeason] = []
    for k, v in get_table_global("BattlePassSeason").items():
        image_id = re.search(r"BattlePassLogo_(\d+)", v['SeasonLogo']['AssetPathName']).group(1)
        result.append(
            BattlePassSeason(
                v['Id'],
                get_text(i18n, v['Name']),
                str(parse_ticks(v['Start']['Ticks'])),
                str(parse_ticks(v['Finish']['Ticks'])),
                f"File:Season {image_id} wallpaper.png"
            ))
    result.sort(key=lambda x: x.start)
    return result


def generate_battle_pass_page(use_cn: bool = False) -> str:
    result = []
    for season, battle_pass_levels in parse_battle_pass_rewards(use_cn).items():
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


def make_cn_battle_page():
    save_page("Battle Pass/CN", generate_battle_pass_page(True))


def make_battle_pass_rewards():
    rewards = parse_battle_pass_rewards(use_cn=False)
    result: dict[int, list[dict]] = {}
    for season, battle_pass_levels in rewards.items():
        result[season] = []
        battle_pass_levels.sort(key=lambda x: x.level)
        for level in battle_pass_levels:
            for reward in level.rewards:
                item = reward.item.name
                reward_name = get_english_version(item)
                result[season].append({
                    'name': {
                        'en': reward_name,
                    },
                    'amount': reward.amount,
                    'image': reward.item.icon,
                    'level': level.level,
                    'free': reward.type == 1
                })
    save_json_page("Module:Season/battle_pass_rewards.json", result)


def make_battle_pass_seasons():
    seasons = parse_battle_pass_seasons()
    save_json_page("Module:Season/seasons.json", seasons)
    make_battle_pass_rewards()


def main():
    make_battle_pass_seasons()


if __name__ == '__main__':
    main()

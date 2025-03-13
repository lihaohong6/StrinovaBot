from dataclasses import dataclass

from page_generator.items import get_all_items, get_en_items
from utils.json_utils import get_table, get_table_global
from utils.lang import ENGLISH


@dataclass
class ClanLevel:
    level: int
    experience: int
    contribution: int
    reward: list[tuple[str, int]]


def parse_clan_levels():
    table = get_table_global("ClanLevelCfg")
    all_items = get_all_items()
    result = []
    for _, v in table.items():
        level = v['Level']
        exp = v['Exp']
        contribution = v['ContributionNeed']
        rewards = []
        for reward in v['Reward']:
            item_id = reward['ItemId']
            item = all_items[item_id]
            rewards.append((item.name[ENGLISH.code], reward['ItemAmount']))
        result.append(ClanLevel(level, exp, contribution, rewards))
    return result


def main():
    parse_clan_levels()
    print('{| class="wikitable"')
    for level in parse_clan_levels():
        assert len(level.reward) == 1
        reward = level.reward[0]
        print('|-\n'
              f'| {level.level} || {level.experience} || {level.contribution} || '
              f'{{{{Item|{reward[0]}|{reward[1]}}}}}')
    print('|}')


if __name__ == '__main__':
    main()
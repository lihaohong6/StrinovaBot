from dataclasses import dataclass
from enum import Enum

from utils.general_utils import get_table, get_string_table
from utils.lang import CHINESE


class TeamType(Enum):
    ZOMBIE = 0
    HUMAN = 1


class UpgradeRarity(Enum):
    BLUE = "Blue"
    PURPLE = "Purple"
    GOLD = "Gold"

    def sort_weight(self):
        table = {
            self.BLUE: 0,
            self.PURPLE: 1,
            self.GOLD: 2
        }
        return table[self]


LANG = CHINESE.code


@dataclass
class OutbreakUpgrade:
    id: int
    name: dict[str, str]
    description: dict[str, str]
    description_params: list[list[int]]
    max_level: int
    team_type: TeamType
    rarity: UpgradeRarity
    weights: list[float]

    def make_descriptions(self) -> list[str]:
        if len(self.description_params) == 0:
            return [self.description[LANG]]

        # assert len(self.description_params) == self.max_level, \
        #     f"{len(self.description_params)} != {self.max_level} for {self.name[LANG]} (id: {self.id})"

        levels = []
        for params in self.description_params:
            original = self.description[LANG]
            for index, param in enumerate(params):
                original = original.replace("{" + str(index) + "}", str(param))
            levels.append(original)

        return levels

    def __str__(self):
        result = [
            f"*Name: {self.name[LANG]}",
        ]
        descriptions = self.make_descriptions()
        if len(descriptions) == 1:
            result.append(f"*Description: {descriptions[0]}")
        else:
            result.append("*Descriptions:")
            for d in descriptions:
                result.append(f"**{d}")
        result.extend([
            f"*Rarity: {self.rarity.value}",
            f"*Weights: {self.weights}",
        ])
        return "\n".join(result)



def outbreak_upgrades() -> dict[int, OutbreakUpgrade]:
    cards = get_table("GameplayCard_Zombie")
    card_details = get_table("GameplayCardData_Zombie")
    card_strings = get_string_table("ST_GameplayCard")
    result: dict[int, OutbreakUpgrade] = {}
    for card_id, v in cards.items():
        name_key = v["Name"]["Key"]
        description_key = v["Desc"]["Key"]
        name = {CHINESE.code: card_strings[name_key]}
        description = {CHINESE.code: card_strings[description_key]}
        description_params = []
        for i in range(1, 10):
            k = f"DescParamLevel{i}"
            if k not in v:
                break
            if len(v[k]) == 0:
                break
            description_params.append(v[k])
        max_level = v["MaxLevel"]
        team_type = TeamType.HUMAN if "Human" in v["TeamType"] else TeamType.ZOMBIE
        rarity = UpgradeRarity(v["Rarity"].split(":")[-1])
        weights = [card_details[card_id][f"WeightStage{i}"] for i in range(1, 5)]
        result[card_id] = OutbreakUpgrade(
            card_id, name, description, description_params, max_level, team_type, rarity, weights
        )
    return result


def print_upgrades(upgrades: list[OutbreakUpgrade]) -> str:
    upgrades.sort(key=lambda x: x.rarity.sort_weight())
    result = []
    for upgrade in upgrades:
        result.append(str(upgrade))
    return "\n<hr>\n".join(result)


def main():
    upgrades = outbreak_upgrades()
    human = [u for u in upgrades.values() if u.team_type == TeamType.HUMAN]
    zombie = [u for u in upgrades.values() if u.team_type == TeamType.ZOMBIE]
    print("==Upgrades==")
    print("===Human===")
    print(print_upgrades(human))
    print("===Zombie===")
    print(print_upgrades(zombie))


if __name__ == '__main__':
    main()
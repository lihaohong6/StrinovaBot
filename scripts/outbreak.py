from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from utils.asset_utils import resource_root
from utils.json_utils import get_string_table, get_all_game_json, get_table_global
from utils.lang import ENGLISH, CHINESE
from utils.lang_utils import get_text
from utils.upload_utils import UploadRequest, process_uploads


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


LANG = ENGLISH.code


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
    image: Path

    def make_descriptions(self) -> list[str]:
        description = self.description.get(LANG, self.description.get(CHINESE.code))
        if len(self.description_params) == 0:
            return [description]

        # assert len(self.description_params) == self.max_level, \
        #     f"{len(self.description_params)} != {self.max_level} for {self.name[LANG]} (id: {self.id})"

        levels = []
        for params in self.description_params:
            original = description
            for index, param in enumerate(params):
                if abs(param - round(param)) < 0.0001:
                    param = int(param)
                original = original.replace("{" + str(index) + "}", str(param))
            levels.append(original)

        return levels

    def filename(self):
        return f"File:Outbreak icon {self.id}.png"

    def __str__(self):
        import wikitextparser as wtp
        template = wtp.parse("{{OutbreakUpgrade}}").templates[0]
        template.set_arg("Name", self.name.get(LANG, self.name.get(CHINESE.code)))
        template.set_arg("Image", self.filename())
        desc = self.make_descriptions()
        if len(desc) == 1:
            template.set_arg("Description", f"Description: {desc[0]}")
        else:
            template.set_arg("Description", "<br/>".join(f"Level {i}: {d}" for i, d in enumerate(desc, 1)))
        template.set_arg("Rarity", self.rarity.value)
        return str(template)

    def __str2__(self):
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
    cards = get_table_global("GameplayCard_Zombie")
    card_details = get_table_global("GameplayCardData_Zombie")
    card_strings = get_string_table("ST_GameplayCard")
    i18n = get_all_game_json("ST_GameplayCard")
    result: dict[int, OutbreakUpgrade] = {}
    for card_id, v in cards.items():
        name = get_text(i18n, v['Name'])
        # Some cards don't have a name
        if len(name) == 0:
            continue
        description = get_text(i18n, v['Desc'])
        description_params = []
        prev_param = None
        for i in range(1, 10):
            k = f"DescParamLevel{i}"
            if k not in v:
                break
            if len(v[k]) == 0:
                break
            if v[k] == prev_param:
                continue
            prev_param = v[k]
            description_params.append(v[k])
        if "{0}" in description['cn'] and len(description_params) == 0:
            continue
        max_level = v["MaxLevel"]
        if max_level != len(description_params) and len(description_params) != 0:
            print(name['en'], max_level, len(description_params))
        team_type = TeamType.HUMAN if "Human" in v["TeamType"] else TeamType.ZOMBIE
        rarity = UpgradeRarity(v["Rarity"].split(":")[-1])
        # weights = [card_details[card_id][f"WeightStage{i}"] for i in range(1, 5)]
        weights = []

        image_path = v["Icon"]["AssetPathName"].split(".")[-1] + ".png"
        image_path = resource_root / "RoguelikeCard" / image_path

        # If no image, probably unreleased
        if not image_path.exists():
            continue

        result[card_id] = OutbreakUpgrade(
            card_id, name, description, description_params, max_level, team_type, rarity, weights, image_path
        )
    return result


def print_upgrades(upgrades: list[OutbreakUpgrade]) -> str:
    upgrades.sort(key=lambda x: x.rarity.sort_weight())
    result = ["{{#invoke:ItemBox|container|mode=grid|min_width=200px|width=max|"]
    for upgrade in upgrades:
        result.append(str(upgrade))
    result.append("}}")
    return "\n".join(result)


def print_all_upgrades():
    upgrades = outbreak_upgrades()
    human = [u for u in upgrades.values() if u.team_type == TeamType.HUMAN]
    zombie = [u for u in upgrades.values() if u.team_type == TeamType.ZOMBIE]
    print("==Upgrades==")
    print("===Human===")
    print(print_upgrades(human))
    print("===Zombie===")
    print(print_upgrades(zombie))


def upload_icons(upgrades: list[OutbreakUpgrade]):
    r = []
    for u in upgrades:
        r.append(UploadRequest(u.image, u.filename(), "[[Category:Outbreak upgrade icons]]"))
    process_uploads(r)


def save_upgrades():
    upgrades = outbreak_upgrades()
    upgrades = list(upgrades.values())
    upgrades.sort(key=lambda x: x.rarity.sort_weight())
    upload_icons(upgrades)
    # result = []
    # for u in upgrades:
    #     result.append({
    #         "id": u.id,
    #         "name": u.name,
    #         "descriptions": u.make_descriptions(),
    #         "team_type": u.team_type.value,
    #         "rarity": u.rarity.value,
    #         "weights": u.weights,
    #         "file": u.filename()
    #     })
    # save_json_page("Module:Outbreak/data.json", result)


if __name__ == '__main__':
    print_all_upgrades()
    upload_icons(list(outbreak_upgrades().values()))
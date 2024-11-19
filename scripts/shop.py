from dataclasses import dataclass
from datetime import datetime

from global_config import char_id_mapper
from utils.general_utils import get_table_global, parse_ticks
from utils.json_utils import get_all_game_json
from utils.lang import ENGLISH
from utils.lang_utils import get_multilanguage_dict


@dataclass
class Banner:
    name: dict[str, str]
    role_id: int
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
        result.append(Banner(name, role_id, start, end))
    return result


def generate_gacha():
    banners = parse_banners()
    print("\n".join(map(str, banners)))


def main():
    generate_gacha()

if __name__ == '__main__':
    main()
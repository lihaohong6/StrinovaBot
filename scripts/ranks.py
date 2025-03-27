from dataclasses import dataclass

from utils.json_utils import get_all_game_json, get_table
from utils.lang import ENGLISH
from utils.lang_utils import get_text


@dataclass
class Division:
    name: str
    level: int
    score: int


def main():
    table = get_table("Division")
    i18n = get_all_game_json("Division")
    results = []
    for k, v in table.items():
        names = get_text(i18n, v['Name'])
        results.append(Division(names[ENGLISH.code], v['Level'], v['ScoreMax']))
    for result in results:
        print(f"|-\n"
              f"| {result.name} || {result.score}")


if __name__ == '__main__':
    main()
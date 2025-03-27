import re
from dataclasses import dataclass
from functools import cache

from pywikibot import FilePage

from utils.asset_utils import resource_root
from utils.general_utils import get_char_by_id
from utils.json_utils import get_all_game_json, get_table, get_table_global
from utils.lang_utils import get_multilanguage_dict, StringConverters, compose, get_text
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s, save_json_page


@dataclass
class Achievement:
    id: int
    level: int
    type: int
    quality: int
    role_id: int
    role_name: str
    name: dict[str, str]
    unlock: dict[str, str]
    description: dict[str, str]


def get_i18n() -> dict:
    i18n = get_all_game_json('Achievement')
    for k, v in get_all_game_json('Badge').items():
        if k not in i18n:
            i18n[k] = v
    return i18n


@cache
def parse_achievements(use_cn: bool = False) -> list[Achievement]:
    i18n = get_i18n()
    if use_cn:
        achievement_table = get_table("Achievement")
    else:
        achievement_table = get_table_global("Achievement")
    achievements = []
    for key, value in achievement_table.items():
        role_id: int = value['Role']
        role_name = get_char_by_id(role_id)

        def sub_condition(string: str):
            if "{0}" in string:
                string = string.format(value['Param2'][0])
                return re.sub(r"<Chat-Self>(\d+)</>", lambda match: match.group(1), string)
            if "[1]" in string:
                string = string.replace("[1]", str(value['Param2'][0]))
                return string
            return string

        converter = compose(StringConverters.basic_converter, sub_condition)
        name = get_text(i18n, value['Name'], converter=converter)
        unlock = get_text(i18n, value['Explain'], converter=converter)
        details = get_text(i18n, value['Details'], converter=converter)
        achievement = Achievement(key, value['Level'], value['Type'], value['Quality'], role_id, role_name,
                                  name, unlock, details)
        achievements.append(achievement)
    return achievements


def upload_achievements(achievements: list[Achievement]) -> None:
    requests: list[UploadRequest] = []
    for achievement in achievements:
        requests.append(UploadRequest(resource_root / "Achievement" / f"T_Dynamic_Achievement_{achievement.id}.png",
                                      FilePage(s, f"File:Achievement_{achievement.id}.png"),
                                      '[[Category:Achievement icons]]',
                                      'Batch upload achievement icons'))
    process_uploads(requests)


def generate_all_achievements(*args):
    achievements = parse_achievements()
    achievements_cn = parse_achievements(use_cn=True)
    upload_achievements(achievements_cn)
    save_json_page("Module:Achievement/data.json", achievements)


def main():
    generate_all_achievements()


if __name__ == '__main__':
    main()

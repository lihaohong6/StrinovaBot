import re
from dataclasses import dataclass
from functools import cache

from pywikibot import FilePage

from utils.asset_utils import resource_root
from utils.general_utils import get_table, get_char_by_id, save_json_page
from utils.json_utils import get_all_game_json
from utils.lang_utils import get_multilanguage_dict, StringConverters, compose
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s


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
def get_achievements(upload: bool = True) -> list[Achievement]:
    i18n = get_i18n()
    achievement_table = get_table("Achievement")
    achievements = []
    for key, value in achievement_table.items():
        try:
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
            name = get_multilanguage_dict(i18n, f"{key}_Name", converter=converter,
                                          extra=value['Name']['SourceString'])
            unlock = get_multilanguage_dict(i18n, f"{key}_Explain", converter=converter,
                                            extra=value['Explain']['SourceString'])
            details = get_multilanguage_dict(i18n, f"{key}_Details", converter=converter,
                                             extra=value['Details']['SourceString'])
            achievement = Achievement(key, value['Level'], value['Type'], value['Quality'], role_id, role_name,
                                      name, unlock, details)
            achievements.append(achievement)
        except KeyError:
            pass
    if upload:
        requests: list[UploadRequest] = []
        for achievement in achievements:
            requests.append(UploadRequest(resource_root / "Achievement" / f"T_Dynamic_Achievement_{achievement.id}.png",
                                          FilePage(s, f"File:Achievement_{achievement.id}.png"),
                                          '[[Category:Achievement icons]]',
                                          'Batch upload achievement icons'))
        process_uploads(requests)
    return achievements


def generate_all_achievements(*args):
    achievements = get_achievements()
    save_json_page("Module:Achievement/data.json", achievements)


def main():
    generate_all_achievements()


if __name__ == '__main__':
    main()

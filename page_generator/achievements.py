import re
from dataclasses import dataclass

import wikitextparser as wtp
from pywikibot import Page, FilePage

from scripts.rename_images import char_name
from utils.asset_utils import resource_root
from utils.general_utils import get_table, make_tab_group, get_char_by_id, save_json_page
from utils.json_utils import get_game_json, get_all_game_json
from utils.lang import Language, ENGLISH
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

    def to_gallery_string(self) -> str:
        return f"File:Achievement {self.id}.png|" + \
            '<span style="font-size: larger">' + f"'''{self.name}'''</span><br/>" + \
            f"'''Unlock''': {self.unlock}<br/>" + \
            f"<small>{self.description}</small>" + \
            f"|alt=Icon of achievement {self.name}"


def achievements_to_gallery(achievements: list[Achievement]) -> str:
    gallery = ["<gallery mode=packed>"]
    for achievement in achievements:
        gallery.append(achievement.to_gallery_string())
    gallery.append("</gallery>")
    return "\n".join(gallery)


def get_i18n() -> dict:
    i18n = get_all_game_json('Achievement')
    for k, v in get_all_game_json('Badge').items():
        if k not in i18n:
            i18n[k] = v
    return i18n


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


def get_achievements_by_level(a_list: list[Achievement]) -> dict[int, list[Achievement]]:
    levels: dict[int, list[Achievement]] = {}
    for achievement in a_list:
        level = achievement.level
        if level not in levels:
            levels[level] = []
        levels[level].append(achievement)
    return levels


def achievements_to_tabs(achievements: list[Achievement], group: str) -> str:
    levels = get_achievements_by_level(achievements)
    group = make_tab_group(group)
    tabs = "{{Tab/tabs | " + f"group={group} | " + " | ".join(f"Level {k}" for k in levels.keys()) + " }}"
    contents = []
    for a_list in levels.values():
        contents.append(achievements_to_gallery(a_list))
    return "\n{{Achievements|\n" + tabs + "\n" + "{{Tab/content | " + f"group={group} |\n" + \
        "\n\n|\n\n".join(contents) + "}}\n}}\n\n"


def generate_all_achievements(*args):
    achievements = get_achievements()
    save_json_page("Module:Achievement/data.json", achievements)


def main():
    generate_all_achievements()


if __name__ == '__main__':
    main()

import re
from dataclasses import dataclass

from pandas._typing import FilePath
from pywikibot import Page, FilePage

from utils.asset_utils import resource_root
from utils.general_utils import get_table, get_game_json, make_tab_group
from utils.lang_utils import Language, ENGLISH
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s

import wikitextparser as wtp


@dataclass
class Achievement:
    id: int
    level: int
    type: int
    quality: int
    role: int
    name: str
    unlock: str
    description: str

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


def get_i18n(lang: Language) -> dict:
    i18n = get_game_json(lang)['Achievement']
    for k, v in get_game_json(lang)['Badge'].items():
        if k not in i18n:
            i18n[k] = v
    return i18n


def get_achievements(upload: bool = True, lang: Language = ENGLISH) -> list[Achievement]:
    i18n = get_i18n(lang)
    achievement_table = get_table("Achievement")
    achievements = []
    for key, value in achievement_table.items():
        try:
            name = i18n.get(f'{key}_Name', value['Name']['SourceString'])
            unlock: str = i18n.get(f'{key}_Explain', value['Explain']['SourceString'])

            def sub_condition(string: str):
                if "{0}" in string:
                    string = string.format(value['Param2'][0])
                    return re.sub(r"<Chat-Self>(\d+)</>", lambda match: match.group(1), string)
                return string

            name = sub_condition(name)
            unlock = sub_condition(unlock)
            description = i18n.get(f'{key}_Details', value['Details']['SourceString'])
            achievement = Achievement(key, value['Level'], value['Type'], value['Quality'], value['Role'],
                                      name, unlock, description)
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


def generate_achievement_page(*args):
    achievements = get_achievements()
    p = Page(s, "Achievements")
    parsed = wtp.parse(p.text)
    type_nums = [1, 3, 4]
    for index, section in enumerate(section for section in parsed.sections if section.level == 2):
        type_num = type_nums[index]
        a_list = [a for a in achievements if a.type == type_num]
        section.contents = achievements_to_tabs(a_list, f"type{type_num}")
    if p.text.strip() != str(parsed).strip():
        p.text = str(parsed)
        p.save(summary="generate achievement page")


def main():
    generate_achievement_page()


if __name__ == '__main__':
    main()

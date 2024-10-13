import re
from dataclasses import dataclass

import wikitextparser as wtp
from pywikibot import Page

from global_config import char_id_mapper
from utils.general_utils import get_table, get_char_pages, save_json_page, get_char_by_id
from utils.json_utils import get_game_json, get_all_game_json
from utils.lang import get_language, JAPANESE, LanguageVariants
from utils.lang_utils import get_multilanguage_dict, compose, StringConverters, StringConverter
from utils.wiki_utils import s


@dataclass
class CharStory:
    title: dict[str, str]
    unlock: dict[str, str]
    content: dict[str, str]


def get_biography() -> dict[str, list[CharStory]]:
    char_stories: dict[str, list[CharStory]] = {}
    i18n = get_all_game_json("RoleBiography")
    for k, v in get_table("RoleBiography").items():
        char_id = v['RoleId']
        char_name = char_id_mapper[char_id]
        lst = char_stories.get(char_name, [])
        title = get_multilanguage_dict(i18n, f'{k}_StoryTitle')
        unlock = get_multilanguage_dict(i18n, f'{k}_UnlockTip')
        content = get_multilanguage_dict(i18n, f'{k}_StoryContent',
                                         converter=lambda x: re.subn(f"\s*\n\s*", "\n\n", x)[0])
        lst.append(CharStory(title, unlock, content))
        char_stories[char_name] = lst
    return char_stories


def generate_biography():
    bio = get_biography()
    save_json_page(Page(s, "Module:Biography/data.json"), bio)


def generate_return_letter():
    letters: dict[str, dict[str, str]] = {}
    i18n = get_all_game_json('ReturnLetterCfg')
    for k, v in get_table("ReturnLetterCfg").items():
        char_id = v['RoleId']
        char_name = get_char_by_id(char_id)
        converter = compose(StringConverters.basic_converter,
                            StringConverters.newline_to_br)
        part1 = get_multilanguage_dict(i18n, f'{k}_LetterTitle', default="",
                                       converter=converter)
        part2 = get_multilanguage_dict(i18n, f'{k}_LetterTitleTwo', default="",
                                       converter=converter)
        letters[char_name] = {}
        for lang_code in part1.keys():
            letters[char_name][lang_code] = (part1[lang_code] + "\n\n" + part2[lang_code]).strip()
    save_json_page("Module:ReturnLetter/data.json", letters)


if __name__ == "__main__":
    generate_biography()
    generate_return_letter()

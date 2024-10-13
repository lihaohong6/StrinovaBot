import re
from dataclasses import dataclass

import wikitextparser as wtp
from pywikibot import Page

from global_config import char_id_mapper
from utils.general_utils import get_table, get_char_pages, save_json_page
from utils.json_utils import get_game_json, get_all_game_json
from utils.lang import get_language
from utils.lang_utils import get_multilanguage_dict
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
    lang = get_language()
    char_stories = {}
    for k, v in get_table("ReturnLetterCfg").items():
        char_id = v['RoleId']
        lst = char_stories.get(char_id, [])
        lst.append(k)
        char_stories[char_id] = lst
    i18n = get_game_json(lang)['ReturnLetterCfg']
    for char_id, char_name, p in get_char_pages(lang=lang):
        if char_id not in char_stories:
            continue
        story_list = char_stories[char_id]
        parsed = wtp.parse(p.text)
        for t in parsed.templates:
            if t.name.strip() == "ReturnLetter":
                result = t
                break
        else:
            print(char_name + " has no template")
            return
        t = result

        def add_arg(name, value):
            if (t.has_arg(name) and value.strip() == "") or value.strip() == "!NoTextFound!":
                return
            t.set_arg(name, value + "\n")

        assert len(story_list) == 1
        story = story_list[0]
        content = (i18n.get(f'{story}_LetterTitle', "!NoTextFound!") +
                   "\n\n" +
                   i18n.get(f'{story}_LetterTitleTwo', "!NoTextFound!"))
        if "!NoTextFound!" in content:
            print(f"Can't generate return letter for {char_name} due to missing i18n")
            continue
        add_arg(f"Content", content.replace("\n", "<br/>"))

        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate return letter", minor=False)
    print("Return letter done")


if __name__ == "__main__":
    generate_biography()
    generate_return_letter()

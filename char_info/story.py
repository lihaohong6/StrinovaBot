import wikitextparser as wtp
from pywikibot import Page

from utils import load_json, get_game_json, get_char_by_id, s, get_table


def generate_biography():
    char_stories = {}
    for k, v in get_table("RoleBiography").items():
        char_id = v['RoleId']
        lst = char_stories.get(char_id, [])
        lst.append(k)
        char_stories[char_id] = lst
    i18n = get_game_json()['RoleBiography']
    for char_id, story_list in char_stories.items():
        char_name = get_char_by_id(char_id)
        p = Page(s, char_name)
        parsed = wtp.parse(p.text)
        for t in parsed.templates:
            if t.name.strip() == "CharacterBiography":
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

        for story_count, story_id in enumerate(story_list, 1):
            title = i18n[f'{story_id}_StoryTitle']
            unlock = i18n[f'{story_id}_UnlockTip']
            content = i18n[f'{story_id}_StoryContent']
            add_arg(f"Title{story_count}", title)
            add_arg(f"Unlock{story_count}", unlock)
            add_arg(f"Content{story_count}", content.replace("\n", "\n\n"))

        if p.text.strip() == str(parsed).strip():
            continue

        p.text = str(parsed)
        p.save(summary="generate biography", minor=False)


def generate_return_letter():
    char_stories = {}
    for k, v in get_table("ReturnLetterCfg").items():
        char_id = v['RoleId']
        lst = char_stories.get(char_id, [])
        lst.append(k)
        char_stories[char_id] = lst
    i18n = get_game_json()['ReturnLetterCfg']
    for char_id, story_list in char_stories.items():
        char_name = get_char_by_id(char_id)
        p = Page(s, char_name)
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
        content = i18n[f'{story}_LetterTitle'] + "\n\n" + i18n[f'{story}_LetterTitleTwo']
        if "!NoTextFound!" in content:
            continue
        add_arg(f"Content", content.replace("\n", "<br/>"))

        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate return letter", minor=False)
    print("Return letter done")

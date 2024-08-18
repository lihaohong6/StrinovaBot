import wikitextparser as wtp
from pywikibot import Page

from utils.general_utils import get_game_json, get_char_by_id, get_table, get_char_pages
from utils.wiki_utils import s


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

        valid = True
        for story_count, story_id in enumerate(story_list, 1):
            try:
                title = i18n[f'{story_id}_StoryTitle']
                unlock = i18n[f'{story_id}_UnlockTip']
                content = i18n[f'{story_id}_StoryContent']
            except KeyError:
                valid = False
                print(f"Failed to generate biography for {char_name} due to missing i18n")
                break
            add_arg(f"Title{story_count}", title)
            add_arg(f"Unlock{story_count}", unlock)
            add_arg(f"Content{story_count}", content.replace("\n", "\n\n"))
        if not valid:
            continue

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
    for char_id, char_name, p in get_char_pages():
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

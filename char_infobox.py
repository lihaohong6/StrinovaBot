import re
from dataclasses import dataclass
from typing import Callable

from pywikibot import Page, Site, FilePage

from utils import get_game_json, get_char_by_id, char_id_mapper, get_game_json_cn, get_game_json_ja, get_role_profile, \
    get_default_weapon_id, camp_id_to_string, role_id_to_string, get_weapon_name, get_weapon_table, get_skill_table, \
    load_json, get_goods_table, name_to_en, bwiki, en_name_to_zh, zh_name_to_en
import wikitextparser as wtp

s = Site()


def nop(x: str | list[str]):
    if isinstance(x, list):
        assert len(x) == 1
        return x[0]
    return x


def get_group_0(x: re.Match):
    if x is None:
        return ""
    return x.group(0)


infobox_args: list[tuple[list[str] | str, str, Callable[[list[str] | str], str]]] = [
    ("Birthday", "Birthday", nop),
    ("Constellation", "Constellation", nop),
    ("Age", "Age", lambda x: get_group_0(re.search(r"^\d+", x))),
    ("Height", "Height", nop),
    ("Weight", "Weight", nop),
    ("Apartment", "Home", nop),
    ("Title", "Title", nop),
    ("Desc", "Description", nop),
    (["Cv", "CvCn"], "VA", lambda x: f"JP: {x[0]}<br/>CN: {x[1]}"),
]


def make_infobox(char_id, char_name, char_profile, profile) -> str | None:
    t = wtp.Template("{{CharacterInfobox\n}}")

    def add_arg(name, value):
        if t.has_arg(name) and value.strip() == "":
            return
        t.set_arg(name, value + "\n")

    add_arg("Name", char_name)
    add_arg("NameEN", char_name)
    add_arg("NameCN", get_game_json_cn()['RoleProfile'][f'{char_id}_NameCn'])
    add_arg("NameJP", get_game_json_ja()['RoleProfile'][f'{char_id}_NameCn'])
    for args, key, mapper in infobox_args:
        def get_arg(arg: str) -> str:
            k = f"{char_id}_{arg}"
            return profile[k] if k in profile else ""

        if isinstance(args, list):
            arg_list = [get_arg(arg) for arg in args]
        else:
            arg_list = get_arg(args)
        add_arg(key, mapper(arg_list))
    try:
        add_arg("Camp", camp_id_to_string[char_profile['Team']])
        add_arg("Role", role_id_to_string[char_profile['Profession']])
        add_arg("Weapon", get_weapon_name(get_default_weapon_id(char_id)))
    except Exception:
        return None
    return str(t)


def generate_page_skeleton():
    profile = get_game_json()['RoleProfile']
    get_role_profile(101)
    for char_id, char_profile in get_role_profile.dict.items():
        char_name = profile[f'{char_id}_NameCn']
        p = Page(s, char_name)
        result = ["{{CharacterTop}}"]
        infobox = make_infobox(char_id, char_name, char_profile, profile)
        if infobox is None:
            continue
        result.append(infobox)
        result.append("")
        result.append("==Background==\n===Official introduction===\n")
        result.append("==Skills==\n")
        result.append("==Weapon==\n")
        result.append("{{CharacterNavbox}}")
        p.text = "\n".join(result)
        p.save(summary="generate page")


def generate_weapons():
    weapons = get_game_json()['Weapon']
    weapon_table = get_weapon_table()
    get_role_profile(101)
    for char_id, char_profile in get_role_profile.dict.items():
        char_name = get_char_by_id(char_id)
        p = Page(s, char_name)

        if "{{PrimaryWeapon" in p.text:
            continue

        weapon_id = get_default_weapon_id(char_id)
        if weapon_id == -1:
            continue
        weapon_name = get_weapon_name(weapon_id)
        weapon_description = weapons[f"{weapon_id}_Tips"]
        weapon_type = weapon_table[weapon_id]['Type'].split("::")[1]
        t = wtp.Template("{{PrimaryWeapon\n}}")

        def add_arg(name, value):
            if t.has_arg(name) and value.strip() == "":
                return
            t.set_arg(name, value + "\n")

        add_arg("Name", weapon_name)
        add_arg("Description", weapon_description)
        add_arg("Type", weapon_type)
        parsed = wtp.parse(p.text)
        for section in parsed.sections:
            if section.title is not None and section.title.strip() == "Weapon":
                section.string = section.string.replace("==\n", "==\n" + str(t))
                break
        else:
            continue
        if p.text.strip() != str(parsed):
            continue
        p.text = str(parsed)
        p.save(summary="generate weapon", minor=False)


def generate_skills():
    skill_texts = get_game_json()['Skill']
    skill_table = get_skill_table()
    get_role_profile(101)
    for char_id, char_profile in get_role_profile.dict.items():
        char_name = get_char_by_id(char_id)
        templates = []
        valid = True
        t = wtp.Template("{{Skill\n}}")

        def add_arg(name, value):
            if t.has_arg(name) and value.strip() == "":
                return
            t.set_arg(name, value + "\n")

        for skill_num in range(1, 4):
            key = char_id * 10 + skill_num

            try:
                add_arg(f"Name{skill_num}", skill_texts[f"{key}_Name"])
                add_arg(f"DisplayName{skill_num}", skill_texts[f"{key}_DisplayName"])
                add_arg(f"Description{skill_num}", skill_texts[f"{key}_Intro"])
            except Exception:
                valid = False
                break

            templates.append(str(t))
        if not valid:
            continue
        p = Page(s, char_name)
        parsed = wtp.parse(p.text)
        for section in parsed.sections:
            if section.title is not None and section.title.strip() == "Skills":
                section.contents = str(t) + "\n\n"
                break
        else:
            continue
        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate skills", minor=False)


def generate_biography():
    char_stories = {}
    for k, v in load_json("json/CSV/RoleBiography.json")[0]['Rows'].items():
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
    for k, v in load_json("json/CSV/ReturnLetterCfg.json")[0]['Rows'].items():
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


def generate_emotes():
    goods_table = get_goods_table()
    i18n = get_game_json()['Goods']
    items: dict[str, list[int]] = {}
    for k, v in goods_table.items():
        if v['ItemType'] != 6:
            continue
        name_chs = v['Name']['SourceString'].split("-")[0]
        name_en = zh_name_to_en(name_chs)
        if name_en is None:
            continue
        lst = items.get(name_en, [])
        lst.append(k)
        items[name_en] = lst

    for name, item_list in items.items():
        gallery = ['<gallery mode="packed">']
        for item in item_list:
            emote_name = i18n[f'{item}_Name']
            emote_name = re.search(f"^{name} ?- ?(.*)", emote_name).group(1)
            description = i18n[f'{item}_Desc']
            gallery.append(f"Emote_{item}.png|'''{emote_name}'''<br/>{description}")
        gallery.append("</gallery>")
        p = Page(s, name)
        parsed = wtp.parse(p.text)
        for section in parsed.sections:
            if section.title is not None and section.title.strip() == "Emotes":
                section.contents = "\n".join(gallery) + "\n\n"
                break
        else:
            continue
        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate emotes", minor=False)


def generate_skins():
    @dataclass
    class SkinInfo:
        id: int
        quality: int
        name_cn: str

    skins_table = load_json("json/CSV/RoleSkin.json")[0]['Rows']
    i18n = get_game_json()['RoleSkin']
    skins: dict[int, list[SkinInfo]] = {}
    for k, v in skins_table.items():
        skin_id = k
        name_cn = v['NameCn']['SourceString']
        quality = v['Quality']
        char_id = v['RoleId']
        lst = skins.get(char_id, [])
        lst.append(SkinInfo(skin_id, quality, name_cn))
        skins[char_id] = lst

    for char_id, skin_list in skins.items():
        char_name = get_char_by_id(char_id)
        for skin in skin_list:
            if skin.quality == 0:
                skin.quality = 10
        skin_list.sort(key=lambda x: x.quality, reverse=True)
        t = wtp.Template("{{CharacterSkins\n}}")
        skin_counter = 1

        def add_arg(name, value):
            if (t.has_arg(name) and value.strip() == "") or value.strip() == "!NoTextFound!":
                return
            t.set_arg(name, value + "\n")

        for skin in skin_list:
            k = f'{skin.id}_NameShort'
            if k not in i18n:
                continue
            name_en = i18n[k]
            description = i18n[f'{skin.id}_Description']
            if char_name not in en_name_to_zh:
                continue
            name_zh = en_name_to_zh[char_name]
            source_file = FilePage(bwiki(), f"{name_zh}时装-{skin.name_cn}.png")
            if not source_file.exists():
                continue
            target_file = FilePage(s, f"{char_name} Skin {name_en}.png")
            if not target_file.exists():
                s.upload(target_file, source_url=source_file.get_file_url(), comment="upload file from bwiki",
                         text=f"Taken from [https://wiki.biligame.com/klbq/{source_file.title(with_ns=True, underscore=True)} bwiki], "
                              f"this image is licensed under CC BY-NC-SA 4.0."
                              f"[[Category:Skin screenshots]]")

            add_arg(f"Name{skin_counter}", name_en)
            add_arg(f"Quality{skin_counter}", str(skin.quality))
            add_arg(f"Description{skin_counter}", description)
            skin_counter += 1

        p = Page(s, char_name)
        parsed = wtp.parse(p.text)
        for section in parsed.sections:
            if section.title is not None and section.title.strip() == "Skins":
                section.contents = str(t) + "\n\n"
                break
        else:
            continue
        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate skins", minor=False)


def main():
    # generate_weapons()
    generate_skills()
    # generate_biography()
    # generate_return_letter()
    # generate_emotes()
    # generate_skins()


if __name__ == "__main__":
    main()

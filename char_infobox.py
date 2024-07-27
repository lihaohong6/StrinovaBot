import dataclasses

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from pywikibot import Page, Site, FilePage
from pywikibot.pagegenerators import PreloadingGenerator, GeneratorFactory

from asset_utils import upload_item
from utils import get_game_json, get_char_by_id, get_game_json_cn, get_game_json_ja, get_role_profile, \
    get_default_weapon_id, camp_id_to_string, role_id_to_string, get_weapon_name, \
    load_json, name_to_en, bwiki, en_name_to_zh, zh_name_to_en, get_cn_wiki_skins, get_id_by_char, \
    get_table, get_quality_table
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
    p = Page(s, char_name)
    parsed = wtp.parse(p.text)
    t = None
    for template in parsed.templates:
        if template.name.strip() == "CharacterInfobox":
            t = template
            break
    else:
        print("Template not found on " + char_name)
        return

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
        print("Insufficient info for " + char_name)
        return
    if p.text.strip() == str(parsed).strip():
        return
    p.save(summary="generate infobox")


def generate_infobox():
    profile = get_game_json()['RoleProfile']
    get_role_profile(101)
    for char_id, char_profile in get_role_profile.dict.items():
        key = f'{char_id}_NameCn'
        if key not in profile:
            continue
        char_name = profile[key]
        make_infobox(char_id, char_name, char_profile, profile)


def generate_weapons():
    from asset_utils import upload_weapon
    weapons = get_game_json()['Weapon']
    weapon_table = get_table("Weapon")
    get_role_profile(101)
    for char_id, char_profile in get_role_profile.dict.items():
        char_name = get_char_by_id(char_id)
        p = Page(s, char_name)
        parsed = wtp.parse(p.text)
        t = None
        for template in parsed.templates:
            if template.name.strip() == "PrimaryWeapon":
                t = template
                break
        else:
            print(f"No template found on {char_name}")
            continue

        weapon_id = get_default_weapon_id(char_id)
        if weapon_id == -1:
            continue
        upload_weapon(char_name, weapon_id)

        weapon_name = get_weapon_name(weapon_id)
        weapon_description = weapons[f"{weapon_id}_Tips"]
        weapon_type = weapon_table[weapon_id]['Type'].split("::")[1]

        def add_arg(name, value):
            if t.has_arg(name) and value.strip() == "":
                return
            t.set_arg(name, value + "\n")

        add_arg("Name", weapon_name)
        add_arg("Description", weapon_description)
        add_arg("Type", weapon_type)

        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate weapon", minor=True)


def generate_skills():
    skill_texts = get_game_json()['Skill']
    skill_table = get_table("Skill")
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
    print("Return letter done")


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
            key = f'{item}_Name'
            if key not in i18n:
                continue
            emote_name = i18n[key]
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
    print("Emotes done.")


def generate_skins():
    @dataclass
    class SkinInfo:
        id: int
        quality: int
        name_cn: str

    skins_table = load_json("json/CSV/RoleSkin.json")[0]['Rows']
    store_skins_table = load_json("json/CSV/Goods.json")[0]['Rows']
    i18n_skin = get_game_json()['RoleSkin']
    i18n_store = get_game_json()['Goods']
    skins: dict[str, list[SkinInfo]] = {}

    def add_skin(char_name, skin_id, quality, name_cn):
        lst = skins.get(char_name, [])
        # avoid dups
        if any(s.name_cn == name_cn for s in lst):
            return
        lst.append(SkinInfo(skin_id, quality, name_cn))
        skins[char_name] = lst

    for k, v in skins_table.items():
        skin_id = k
        name_cn = v['NameCn']['SourceString']
        quality = v['Quality']
        char_name = get_char_by_id(v['RoleId'])
        if char_name is None:
            continue
        add_skin(char_name, skin_id, quality, name_cn)
    cn_skin_name_to_char_name = get_cn_wiki_skins()
    for k, v in store_skins_table.items():
        if v['ItemType'] != 8:
            continue
        skin_id = v['Id']
        name_cn = v['Name']['SourceString']
        quality = v['Quality']
        if name_cn not in cn_skin_name_to_char_name:
            continue
        char_name = zh_name_to_en(cn_skin_name_to_char_name[name_cn])
        add_skin(char_name, skin_id, quality, name_cn)

    for char_name, skin_list in skins.items():
        for skin in skin_list:
            if skin.quality == 0:
                skin.quality = 10
        skin_list.sort(key=lambda x: x.quality, reverse=True)

        p = Page(s, char_name)
        parsed = wtp.parse(p.text)
        t = None
        for template in parsed.templates:
            if template.name.strip() == "CharacterSkins":
                t = template
                break
        else:
            print("Template CharacterSkins not found on " + char_name)
            continue

        skin_counter = 1

        def add_arg(name, value):
            if (t.has_arg(name) and value.strip() == "") or value.strip() == "!NoTextFound!":
                return
            t.set_arg(name, value + "\n")

        for skin in skin_list:
            k1 = f'{skin.id}_NameCn'
            k2 = f'{skin.id}_Name'
            if k1 in i18n_skin:
                name_en = i18n_skin[k1]
                description = i18n_skin[f'{skin.id}_Description']
            elif k2 in i18n_store:
                name_en = i18n_store[k2]
                description = i18n_store.get(f'{skin.id}_Desc', "")
            else:
                continue
            if char_name not in en_name_to_zh:
                continue
            name_zh = en_name_to_zh[char_name]
            target_file = FilePage(s, f"{char_name} Skin {name_en}.png")
            if not target_file.exists():
                source_file = FilePage(bwiki(), f"{name_zh}时装-{skin.name_cn}.png")
                if not source_file.exists():
                    continue
                s.upload(target_file, source_url=source_file.get_file_url(), comment="upload file from bwiki",
                         text=f"Taken from [https://wiki.biligame.com/klbq/{source_file.title(with_ns=True, underscore=True)} bwiki], "
                              f"this image is licensed under CC BY-NC-SA 4.0."
                              f"[[Category:Skin screenshots]]")

            add_arg(f"Name{skin_counter}", name_en)
            add_arg(f"Quality{skin_counter}", str(skin.quality))
            add_arg(f"Description{skin_counter}", description)
            skin_counter += 1

        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate skins", minor=False)
    print("Skins done")


def generate_string_energy_network():
    """
Growth_Bomb

    Regular group name: 112_PartName_Index0-3
        112_Part1Desc_Index0-1
        112_Part2Desc_Index0-1
        112_Part4Desc_Index0-1
        112_Part5Desc_Index0-1

    Skill group name: skill id from Role.json, "{skill id}_Name"
        Q upgrade details: 112_QDesc_Index0-1
        Passive: 112_PassiveDesc_Index0-1

    Armor group name: 112_PartName_Index4-5
        112_ShieldDesc_Index0-1
        107_SurviveDesc_Index0-1

Growth_Escort

Growth_Team
    :return:
    """
    i18n = get_game_json()['Growth_Bomb']
    i18n_skill = get_game_json()['Skill']
    role_json = get_table("Role")
    skill_json = get_table("Skill")
    gen = GeneratorFactory(s)
    gen.handle_args(['-cat:Characters', '-ns:0'])
    gen = gen.getCombinedGenerator(preload=True)
    for p in gen:
        char_name = p.title()
        bwiki_base_page = Page(bwiki(), en_name_to_zh[char_name])
        if bwiki_base_page.isRedirectPage():
            bwiki_base_page = bwiki_base_page.getRedirectTarget()
        bwiki_page = Page(bwiki(), bwiki_base_page.title() + "/弦能增幅网络")
        assert bwiki_page.exists(), char_name
        char_id = get_id_by_char(char_name)
        assert char_id is not None
        weapon_name = get_weapon_name(get_default_weapon_id(char_id))
        parsed = wtp.parse(p.text)
        for template in parsed.templates:
            if template.name.strip() == "StringEnergyNetwork":
                t = template
                break
        else:
            print("Template StringEnergyNetwork not found on " + char_name)
            return

        part: wtp.Template | None = None

        def add_arg(name, value):
            nonlocal part
            value = str(value)
            if part.has_arg(name) and (value.strip() == "" or value.strip() == "!NoTextFound!"):
                return
            part.set_arg(" " + name, value + " ")

        t.set_arg("char", char_name + "\n")

        arg_index = 1
        for part_index, part_num in enumerate([1, 2, 4, 5]):
            part = wtp.Template("{{StringEnergyNetwork/group}}")
            add_arg("type", 1)
            add_arg("name", i18n[f"{char_id}_PartName_Index{part_index}"])
            add_arg("icon", re.search(rf"icon{part_index + 1}=(\d)+", bwiki_page.text).group(1))
            add_arg("text1", i18n[f"{char_id}_Part{part_num}Desc_Index0"])
            add_arg("cost1", 150)
            add_arg("text2", i18n[f"{char_id}_Part{part_num}Desc_Index1"])
            add_arg("cost2", 150)
            t.set_arg(f"group{arg_index}", str(part) + "\n")
            arg_index += 1

        skills = [role_json[char_id]['SkillActive'][0], role_json[char_id]['SkillPassive'][0]]
        localization_keys = ["QDesc", "PassiveDesc"]
        for skill_index in range(0, len(skills)):
            skill_id = skills[skill_index]
            localization_key = localization_keys[skill_index]
            skill_info = skill_json[skill_id]
            part = wtp.Template("{{StringEnergyNetwork/group}}")
            add_arg("type", 2)
            add_arg("name", i18n_skill[f"{skill_id}_Name"])
            add_arg("icon", re.search(r"\d+$", skill_info['IconSkill']['AssetPathName']).group(0))

            for index in range(0, 2):
                text_key = f"{char_id}_{localization_key}_Index{index}"
                if text_key not in i18n:
                    break
                text = i18n[text_key]
                add_arg(f"text{index + 1}", text)
                add_arg(f"cost{index + 1}", 250)
            t.set_arg(f"group{arg_index}", str(part) + "\n")
            arg_index += 1

        localization_keys = ["ShieldDesc", "SurviveDesc"]
        for i, part_index in enumerate([4, 5]):
            part = wtp.Template("{{StringEnergyNetwork/group}}")
            add_arg("type", 3)
            add_arg("name", i18n[f"{char_id}_PartName_Index{part_index}"])

            localization_key = localization_keys[i]
            for index in range(0, 2):
                add_arg(f"text{index + 1}", i18n[f"{char_id}_{localization_key}_Index{index}"])
                add_arg(f"cost{index + 1}", 250)
            t.set_arg(f"group{arg_index}", str(part) + "\n")
            arg_index += 1

        # process awakenings
        wake_ids = role_json[char_id]["SkillWake"]
        for wake_index, wake_id in enumerate(wake_ids, 1):
            part = wtp.Template("{{StringEnergyNetwork/awakening}}")
            wake_info = skill_json[wake_id]
            assert wake_info["SkillType"] == 4, wake_id
            active_cond = skill_json[wake_id]["ActiveCond"]
            for cond_index, cond in enumerate(active_cond, 1):
                add_arg(f"icon{cond_index}", cond)
            name = i18n_skill[f'{wake_id}_Name']
            text = i18n_skill[f'{wake_id}_Intro']
            add_arg("name", name)
            add_arg("text", text)
            t.set_arg(f"wake{wake_index}", str(part) + "\n")

        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate string energy network", minor=True)
# def generate_quality_table():
#     quality_table = get_quality_table()
#     text = json.dumps(quality_table)
#     p = Page(s, "Module:CharacterGifts/rarity.json")
#     if p.text.strip() == text:
#         return
#     p.text = text
#     p.save(summary="update rarity data")


def generate_gifts():
    @dataclass
    class Gift:
        id: int
        name: str = ""
        quality: int | str = -1
        file: str = ""
        description: str = ""
        characters: dict[str, tuple[int, int]] = field(default_factory=dict)
        best_characters: list[str] = field(default_factory=list)

    i18n = get_game_json()['Item']
    gift_json = get_table("RoleFavorabilityGiftPresent")
    gift_dict: dict[int, Gift] = {}
    for gift in gift_json.values():
        gift_id = gift['Gift']
        char_id = gift['RoleId']
        char_name = get_char_by_id(char_id)
        favorability = gift['Favorability']
        like_level = gift['LikeLevel']
        if gift_id not in gift_dict:
            gift_dict[gift_id] = Gift(gift_id)
        gift_dict[gift_id].characters[char_name] = (favorability, like_level)
    item_table = get_table("Item")
    gifts = list(gift_dict.values())
    for gift in gifts:
        g = item_table[gift.id]
        gift.file = re.search(r"_(\d+)$", g['IconItem']['AssetPathName']).group(1)
        gift.quality = g['Quality']
        gift.name = i18n[f"{gift.id}_Name"]
        gift.description = i18n[f"{gift.id}_Desc"]

    gifts = [g
             for g in sorted(gifts, key=lambda t: t.quality, reverse=True)
             if g.file != "10001"]
    all_recipients = set(gifts[0].characters.keys())
    for g in gifts:
        all_recipients.intersection_update(set(g.characters.keys()))
        # upload_item(g.file)
    for gift in gifts:
        max_favorability = max(map(lambda t: t[0], gift.characters.values()))
        gift.best_characters = list(
            map(lambda t: t[0], filter(lambda t: t[1][0] == max_favorability and t[0] in all_recipients, gift.characters.items())))
        if len(gift.best_characters) == len(all_recipients):
            gift.best_characters = ["Everyone"]

    # quality_table = get_quality_table()
    # for g in gifts.values():
    #     g.quality = quality_table[int(g.quality)]

    class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            return super().default(o)

    p = Page(s, "Module:CharacterGifts/data.json")
    text = json.dumps(gifts, cls=EnhancedJSONEncoder)
    if p.text.strip() == text:
        return
    p.text = text
    p.save(summary="update gift data")

    for char_name in all_recipients:
        p = Page(s, char_name)
        parsed = wtp.parse(p.text)
        for t in parsed.templates:
            if t.name.strip() == "CharacterGifts":
                break
        else:
            raise RuntimeError("Template not found on " + char_name)
        if t.has_arg("1"):
            continue
        t.set_arg("1", char_name, positional=True)
        p.text = str(parsed)
        p.save("enable character gift")


def main():
    # generate_infobox()
    # generate_weapons()
    # generate_skills()
    # generate_biography()
    # generate_return_letter()
    # generate_emotes()
    # generate_skins()
    # generate_string_energy_network()
    generate_gifts()
    pass


if __name__ == "__main__":
    main()

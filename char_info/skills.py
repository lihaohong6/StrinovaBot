import re
from dataclasses import dataclass
from typing import Final

import wikitextparser as wtp
from pywikibot import FilePage, Page
from wikitextparser import parse

from global_config import char_id_mapper, Character, get_characters
from utils.asset_utils import resource_root
from utils.general_utils import get_table, get_char_pages, pick_two, get_table_global, save_json_page, get_char_pages2
from utils.json_utils import get_game_json, get_all_game_json
from utils.lang import get_language, ENGLISH
from utils.lang_utils import get_multilanguage_dict
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s
from utils.wtp_utils import get_templates_by_name


@dataclass
class Skill:
    name: dict[str, str]
    type: dict[str, str]
    description: dict[str, str]


@dataclass
class CharacterSkills:
    char: Character
    active_skill: Skill
    passive_skill: Skill
    ultimate_skill: Skill


def parse_skills() -> dict[str, CharacterSkills]:
    i18n = get_all_game_json('Skill')
    skill_table = get_table("Skill")
    result: list[CharacterSkills] = []

    for char in get_characters():
        skills = []
        for skill_num in range(1, 4):
            key = char.id * 10 + skill_num
            name_cn = skill_table[key]['Name']['SourceString']
            description_cn = skill_table[key]['Intro']['SourceString']
            name = get_multilanguage_dict(i18n, f"{key}_Name", extra=name_cn)
            skill_type = get_multilanguage_dict(i18n, f"{key}_DisplayName")
            description = get_multilanguage_dict(i18n, f"{key}_Intro", extra=description_cn)
            skills.append(Skill(name=name, type=skill_type, description=description))
        result.append(CharacterSkills(char, *skills))
    return dict((r.char.name, r) for r in result)


def generate_character_skills(skill_table, skill_texts, char, p, save: bool = True):
    templates = []
    valid = True
    parsed = wtp.parse(p.text)
    for t in parsed.templates:
        if t.name.strip() == "Skill":
            break
    else:
        print("No skill template found for " + char.name)
        return

    def add_arg(name, value):
        if t.has_arg(name) and value.strip() == "":
            return
        t.set_arg(name, value + "\n")

    for skill_num in range(1, 4):
        key = char.id * 10 + skill_num

        try:
            name_cn = skill_table[key]['Name']['SourceString']
            description_cn = skill_table[key]['Intro']['SourceString']
            add_arg(f"Name{skill_num}", pick_two(skill_texts.get(f"{key}_Name"), name_cn))
            add_arg(f"DisplayName{skill_num}", pick_two(skill_texts.get(f"{key}_DisplayName"), ""))
            add_arg(f"Description{skill_num}", pick_two(skill_texts.get(f"{key}_Intro"), description_cn))
        except Exception:
            valid = False
            break

        templates.append(str(t))
    if not valid:
        return
    if p.text.strip() == str(parsed).strip():
        return
    p.text = str(parsed)
    if save:
        p.save(summary="generate skills", minor=False)


def generate_skills(pages: list[tuple[Character, Page]] = None):
    lang = get_language()
    skill_texts = get_game_json(lang)['Skill']
    skill_table = get_table("Skill")
    # Only need this check once. Do it for English.
    # Disable auto-uploads since they need to be preprocessed with imagemagick
    if lang == ENGLISH and False:
        upload_skill_icons()

    save = False
    if pages is None:
        pages = get_char_pages2(lang=lang)
        save = True
    for char, p in pages:
        generate_character_skills(skill_table, skill_texts, char, p, save=save)


def upload_skill_icons():
    requests: list[UploadRequest] = []
    for char_id, char_name in char_id_mapper.items():
        for num in range(1, 4):
            source = resource_root / "Skill" / f"T_Dynamic_Skill_{char_id}{num:02}.png"
            target = FilePage(s, f"File:{char_name}_Skill_{num}.png")
            req = UploadRequest(source, target, text="", comment="batch upload skill icons")
            requests.append(req)
    process_uploads(requests)


def generate_string_energy_network(pages: list[tuple[Character, Page]] = None):
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
    lang = get_language()
    i18n = get_game_json(lang)['ST_GrowthDefine']
    i18n_skill = get_game_json(lang)['Skill']
    role_json = get_table("Role")
    skill_json = get_table_global("Skill")
    growth_bomb = get_table_global("Growth_Bomb")
    save = False
    if pages is None:
        pages = get_char_pages2(lang=lang)
        save = True
    for char, p in pages:
        char_id = char.id
        char_name = char.name
        # FIXME: bwiki api is too slow
        # bwiki_base_page = Page(bwiki(), en_name_to_zh[char_name])
        # if bwiki_base_page.isRedirectPage():
        #     bwiki_base_page = bwiki_base_page.getRedirectTarget()
        # bwiki_page = Page(bwiki(), bwiki_base_page.title() + "/弦能增幅网络")
        # assert bwiki_page.exists(), char_name
        parsed = wtp.parse(p.text)
        for template in parsed.templates:
            if template.name.strip() == "StringEnergyNetwork":
                t = template
                break
        else:
            print("Template StringEnergyNetwork not found on " + char_name)
            continue

        try:
            char_string_energy_network(char_id, char_name, growth_bomb, i18n, i18n_skill, p, role_json, skill_json, t)
        except Exception as e:
            print(f"Failed to process string energy network for {char_name} due to {e}")
            continue
        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        if save:
            p.save(summary="generate string energy network", minor=True)


def char_string_energy_network(char_id, char_name, growth_bomb, i18n, i18n_skill, p, role_json, skill_json, t):
    part: wtp.Template | None = None
    char_growth = growth_bomb[char_id]

    def add_arg(name, value):
        nonlocal part
        value = str(value)
        if part.has_arg(name) and (value.strip() == "" or value.strip() == "!NoTextFound!"):
            return
        part.set_arg(" " + name, value + " ")

    def get_formatted_string(growth_dict) -> str:
        if 'SourceFmt' in growth_dict:
            formatted = i18n[growth_dict['SourceFmt']['Key']]
            for arg in growth_dict['Arguments']:
                formatted = formatted.replace(f"{{{arg['Type']}}}", str(arg['Value']))
                formatted, _ = re.subn(r"\{\d}", str(arg['Value']), formatted)
        else:
            formatted = i18n[growth_dict['Key']]
        return formatted

    t.set_arg("char", char_name + "\n")
    arg_index = 1
    for part_index, part_num in enumerate([1, 2, 4, 5]):
        part = wtp.Template("{{StringEnergyNetwork/group}}")
        add_arg("type", 1)

        upgrade_name = i18n[char_growth['PartName'][part_index]['Key']]
        add_arg("name", upgrade_name)
        # FIXME: bwiki api is too slow
        # add_arg("icon", re.search(rf"icon{part_index + 1}=(\d)+", bwiki_page.text).group(1))
        add_arg("icon", re.search(rf"group{arg_index}=.*icon=(\d)", p.text).group(1))

        descriptions = char_growth[f'Part{part_num}Desc']
        for index, description in enumerate(descriptions, 1):
            add_arg(f"text{index}", get_formatted_string(description))
            add_arg(f"cost{index}", 150)
        t.set_arg(f"group{arg_index}", str(part) + "\n")
        arg_index += 1
    skills = [role_json[char_id]['SkillActive'][0], role_json[char_id]['SkillPassive'][0]]
    localization_keys = ["QDesc", "PassiveDesc"]
    for skill_index in range(0, len(skills)):
        skill_id = skills[skill_index]
        skill_info = skill_json[skill_id]
        part = wtp.Template("{{StringEnergyNetwork/group}}")
        add_arg("type", 2)
        add_arg("name", i18n_skill[f"{skill_id}_Name"])
        add_arg("icon", re.search(r"\d+$", skill_info['IconSkill']['AssetPathName']).group(0))

        skill_growths = char_growth[localization_keys[skill_index]]
        for index, skill_growth in enumerate(skill_growths):
            add_arg(f"text{index + 1}", get_formatted_string(skill_growth))
            add_arg(f"cost{index + 1}", 250)
        t.set_arg(f"group{arg_index}", str(part) + "\n")
        arg_index += 1
    localization_keys = ["ShieldDesc", "SurviveDesc"]
    for i, part_index in enumerate([4, 5]):
        part = wtp.Template("{{StringEnergyNetwork/group}}")
        add_arg("type", 3)
        shield_name = i18n[char_growth['PartName'][part_index]['Key']]
        add_arg("name", shield_name)

        shield_growths = char_growth[localization_keys[i]]
        for index, shield_growth in enumerate(shield_growths):
            add_arg(f"text{index + 1}", get_formatted_string(shield_growth))
            add_arg(f"cost{index + 1}", 250)
        t.set_arg(f"group{arg_index}", str(part) + "\n")
        arg_index += 1
    # process awakenings
    awakening_template_name = "StringEnergyNetwork/awakening"
    original_templates = get_templates_by_name(parse(p.text), awakening_template_name)
    wake_ids = role_json[char_id]["SkillWake"]
    for wake_index, wake_id in enumerate(wake_ids, 1):
        if len(original_templates) >= wake_index:
            part = original_templates[wake_index - 1]
        else:
            part = wtp.Template("{{" + awakening_template_name + "}}")
        activate_condition = char_growth[f'Arousal{wake_index}ActivateNeed']
        for cond_index, cond in enumerate(activate_condition, 1):
            add_arg(f"icon{cond_index}", cond)
        name = i18n_skill[f'{wake_id}_Name']
        text = i18n_skill[f'{wake_id}_Intro']
        add_arg("name", name)
        add_arg("text", text)
        part.set_arg(" number", str(wake_index) + " ", before="name")
        t.set_arg(f"wake{wake_index}", str(part) + "\n")


@dataclass
class StringEnergyNetworkStats:
    rate_of_fire:int
    ads_speed: int
    accuracy: int
    handling: int
    magazine: int
    reload_speed: int
    rechambering_speed: int
    stringified_damage: int
    scope_zoom: str
    movement_speed: int

EXTRAS: Final[dict] = {
    "MagazineCapacity": -1,
    "Armor": -1,
    "ShootSpeed": -1,
}

def parse_string_energy_network_stats():
    table = get_table_global("Growth_Bomb")
    result: dict = {}
    for role_id, v in table.items():
        char_name = char_id_mapper[role_id]
        attributes = {}
        for row in v['DefaultProperty1']:
            x = row.split("|")
            name, value = x[0], x[1]
            value = float(value) if "." in value else int(value)
            attributes[name] = value
        assert len(attributes) == 9

        for k, value in EXTRAS.items():
            attributes[k] = value

        attributes["MoveSpeed"] = int(attributes["MoveSpeed"])

        result[char_name] = attributes
    return result


def make_string_energy_network_stats():
    stats = parse_string_energy_network_stats()
    def merge_function(n1: int, n2: int) -> int:
        if n1 is None:
            return n2
        if n2 is None:
            return n1
        if n1 == 0 or n1 == -1:
            return n2
        return n1
    save_json_page("Module:SENStats/data.json", stats, merge=merge_function)


def main():
    generate_skills()
    generate_string_energy_network()
    make_string_energy_network_stats()


if __name__ == "__main__":
    main()


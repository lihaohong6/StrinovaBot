import re
import subprocess
from dataclasses import dataclass
from typing import Final

import wikitextparser as wtp
from pywikibot import FilePage, Page
from wikitextparser import parse

from global_config import char_id_mapper, Character, get_characters
from utils.asset_utils import global_resources_root
from utils.general_utils import get_char_pages2
from utils.json_utils import get_game_json, get_all_game_json, get_table_global
from utils.lang import get_language
from utils.lang_utils import get_multilanguage_dict, get_text
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s, save_lua_table, save_json_page
from utils.wtp_utils import get_templates_by_name


@dataclass
class Skill:
    id: int
    name: dict[str, str]
    type: dict[str, str]
    description: dict[str, str]


@dataclass
class Awakening:
    id: int
    name: dict[str, str]
    description: dict[str, str]
    cond: tuple[int, int, int]


@dataclass
class CharacterSkills:
    char: Character
    active_skill: Skill
    passive_skill: Skill
    tactical_skill: Skill
    ultimate_skill: Skill
    awakening1: Awakening
    awakening2: Awakening
    awakening3: Awakening


def parse_skills() -> dict[str, CharacterSkills]:
    i18n = get_all_game_json('Skill')
    skill_table = get_table_global("Skill")
    role_table = get_table_global("Role")
    growth_bomb = get_table_global("Growth_Bomb")
    result: list[CharacterSkills] = []

    for char in get_characters():
        skills = []
        # Active, passive, tactical, and ultimate skills
        for skill_num in [1, 2, 9, 3]:
            key = char.id * 10 + skill_num
            v = skill_table[key]
            name = get_text(i18n, v['Name'])
            skill_type = get_text(i18n, v['DisplayName'])
            description = get_text(i18n, v['Intro'])
            skills.append(Skill(id=key, name=name, type=skill_type, description=description))
        # Awakenings
        wake_ids = role_table[char.id]["SkillWake"]
        for wake_index, wake_id in enumerate(wake_ids, 1):
            char_growth = growth_bomb[char.id]
            activate_condition = tuple[int, int, int](char_growth[f'Arousal{wake_index}ActivateNeed'])
            name = get_multilanguage_dict(i18n , f'{wake_id}_Name')
            text = get_multilanguage_dict(i18n, f'{wake_id}_Intro')
            skills.append(Awakening(id=wake_id, name=name, description=text, cond=activate_condition))
        result.append(CharacterSkills(char, *skills))
    return dict((r.char.name, r) for r in result)


def make_skills() -> None:
    all_skills = parse_skills()
    result: dict[str, dict[int, Skill]] = {}
    for char, char_skills in all_skills.items():
        skills: dict[int, Skill] = {}
        skill_list = [char_skills.active_skill, char_skills.passive_skill, char_skills.ultimate_skill,
                      char_skills.awakening1, char_skills.awakening2, char_skills.awakening3]
        for index, skill in enumerate(skill_list, 1):
            skills[index] = skill
        skills[9] = char_skills.tactical_skill
        result[char] = skills
    # upload_skill_icons()
    save_lua_table("Module:Skill/data", result)


def upload_skill_icons():
    skill_root = global_resources_root / "Skill"
    subprocess.run(["magick", "mogrify", "-fill", "#efcb5d", "-colorize", "100%", "*.png"],
                   shell=True, check=True, cwd=skill_root)
    requests: list[UploadRequest] = []
    for char_id, char_name in char_id_mapper.items():
        for num in [1, 2, 3, 9]:
            source = skill_root / f"T_Dynamic_Skill_{char_id}{num:02}.png"
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
    role_json = get_table_global("Role")
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
        templates = get_templates_by_name(parsed, "StringEnergyNetwork")
        if len(templates) != 1 :
            print("Template StringEnergyNetwork not found on " + char_name)
            continue
        t = templates[0]
        char_string_energy_network(char_id, char_name, growth_bomb, i18n, i18n_skill, p, role_json, skill_json, t)
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
        elif 'Key' in growth_dict:
            key = growth_dict['Key']
            if key not in i18n and key == 'Part_String':
                key = "Part_Survive"
            formatted = i18n[key]
        else:
            return "FIXME"
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
        add_arg("icon", f"{char_name} Skill {skill_index + 1}.png")

        skill_growths = char_growth[localization_keys[skill_index]]
        for index, skill_growth in enumerate(skill_growths, 1):
            if index == 3:
                break
            add_arg(f"text{index}", get_formatted_string(skill_growth))
            add_arg(f"cost{index}", 250)
        t.set_arg(f"group{arg_index}", str(part) + "\n")
        arg_index += 1
    localization_keys = ["ShieldDesc", "SurviveDesc"]
    for i, part_index in enumerate([4, 5]):
        part = wtp.Template("{{StringEnergyNetwork/group}}")
        add_arg("type", 3)
        upgrade_name = get_formatted_string(char_growth['PartName'][part_index])
        add_arg("name", upgrade_name)

        shield_growths = char_growth[localization_keys[i]]
        for index, shield_growth in enumerate(shield_growths, 1):
            if index == 3:
                break
            add_arg(f"text{index}", get_formatted_string(shield_growth))
            add_arg(f"cost{index}", 250)
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
        name = i18n_skill.get(f'{wake_id}_Name', None)
        text = i18n_skill[f'{wake_id}_Intro']
        if name is not None:
            add_arg("name", name)
        add_arg("text", text)
        part.set_arg(" number", str(wake_index) + " ", before="name")
        t.set_arg(f"wake{wake_index}", str(part) + "\n")


@dataclass
class StringEnergyNetworkStats:
    rate_of_fire: int
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
        char_name = char_id_mapper.get(role_id, None)
        if char_name is None:
            continue
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
    make_skills()
    generate_string_energy_network()
    make_string_energy_network_stats()


if __name__ == "__main__":
    main()

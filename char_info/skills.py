import re

import wikitextparser as wtp
from pywikibot import Page, FilePage
from wikitextparser import parse

from global_config import char_id_mapper
from utils.asset_utils import resource_root
from utils.general_utils import get_table, en_name_to_zh, get_id_by_char, \
    get_weapon_name, get_default_weapon_id, get_char_pages, pick_string, pick_two, get_table_global
from utils.json_utils import get_game_json
from utils.lang import get_language
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import bwiki, s
from utils.wtp_utils import get_templates_by_name


def generate_skills():
    lang = get_language()
    skill_texts = get_game_json(lang)['Skill']
    skill_table = get_table("Skill")
    requests: list[UploadRequest] = []
    for char_id, char_name in char_id_mapper.items():
        for num in range(1, 4):
            source = resource_root / "Skill" / f"T_Dynamic_Skill_{char_id}{num:02}.png"
            target = FilePage(s, f"File:{char_name}_Skill_{num}.png")
            req = UploadRequest(source, target, text="", comment="batch upload skill icons")
            requests.append(req)
    process_uploads(requests)

    for char_id, char_name, p in get_char_pages(lang=lang):
        templates = []
        valid = True
        parsed = wtp.parse(p.text)
        for t in parsed.templates:
            if t.name.strip() == "Skill":
                break
        else:
            print("No skill template found for " + char_name)
            continue

        def add_arg(name, value):
            if t.has_arg(name) and value.strip() == "":
                return
            t.set_arg(name, value + "\n")

        for skill_num in range(1, 4):
            key = char_id * 10 + skill_num

            try:
                name_cn = skill_table[key]['Name']['SourceString']
                description_cn = skill_table[key]['Intro']['SourceString']
                add_arg(f"Name{skill_num}", pick_two(skill_texts.get(f"{key}_Name"), name_cn))
                add_arg(f"DisplayName{skill_num}", pick_two(skill_texts.get(f"{key}_DisplayName"),  ""))
                add_arg(f"Description{skill_num}", pick_two(skill_texts.get(f"{key}_Intro"), description_cn))
            except Exception:
                valid = False
                break

            templates.append(str(t))
        if not valid:
            continue
        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate skills", minor=False)


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
    lang = get_language()
    i18n = get_game_json(lang)['ST_GrowthDefine']
    i18n_skill = get_game_json(lang)['Skill']
    role_json = get_table_global("Role")
    skill_json = get_table_global("Skill")
    growth_bomb = get_table_global("Growth_Bomb")
    for char_id, char_name, p in get_char_pages(lang=lang):
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
            return

        try:
            char_string_energy_network(char_id, char_name, growth_bomb, i18n, i18n_skill, p, role_json, skill_json, t)
        except Exception as e:
            print(f"Failed to process string energy network for {char_name} due to {e}")
            continue

        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
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
        t.set_arg(f"wake{wake_index}", str(part) + "\n")


def main():
    # generate_skills()
    generate_string_energy_network()


if __name__ == "__main__":
    main()


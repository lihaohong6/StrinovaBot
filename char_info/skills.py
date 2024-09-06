import re

import wikitextparser as wtp
from pywikibot import Page, FilePage

from global_config import char_id_mapper
from utils.asset_utils import resource_root
from utils.general_utils import get_game_json, get_table, en_name_to_zh, get_id_by_char, \
    get_weapon_name, get_default_weapon_id, get_char_pages
from utils.lang_utils import get_language
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import bwiki, s


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
                add_arg(f"Name{skill_num}", skill_texts[f"{key}_Name"])
                add_arg(f"DisplayName{skill_num}", skill_texts[f"{key}_DisplayName"])
                add_arg(f"Description{skill_num}", skill_texts[f"{key}_Intro"])
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
    i18n = get_game_json(lang)['Growth_Bomb']
    i18n_skill = get_game_json(lang)['Skill']
    role_json = get_table("Role")
    skill_json = get_table("Skill")
    for char_id, char_name, p in get_char_pages(lang=lang):
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


def main():
    generate_skills()
    generate_string_energy_network()


if __name__ == "__main__":
    main()


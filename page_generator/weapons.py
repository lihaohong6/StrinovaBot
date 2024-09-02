import re
from dataclasses import dataclass
from enum import Enum

import wikitextparser as wtp
from pywikibot import Page, FilePage
from pywikibot.pagegenerators import PreloadingGenerator
from wikitextparser import Template

from global_config import char_id_mapper
from utils.upload_utils import upload_file
from utils.general_utils import get_game_json, get_table, get_game_json_cn, get_default_weapon_id
from utils.wiki_utils import bwiki, s


@dataclass
class Weapon:
    id: int
    name: str
    name_cn: str
    unlock: str
    description: str
    parent: int
    type: str = ""
    file: str = ""


def get_weapons_by_type(weapon_type: str) -> list[Weapon]:
    i18n = get_game_json()['Weapon']
    i18n_cn = get_game_json_cn()['Weapon']
    weapons = get_table("Weapon")
    result = []
    for k, v in weapons.items():
        if weapon_type not in v['Slot']:
            continue
        try:
            weapon_id = k
            name_key = f"{weapon_id}_Name"
            name = i18n[name_key]
            name_cn = i18n_cn[name_key]
            unlock = i18n.get(f"{weapon_id}_GainParam2", "" if v['Default'] != 1 else "Available by default")
            description = i18n[f"{weapon_id}_Tips"]
            parent = v['SubType']
            result.append(Weapon(weapon_id, name, name_cn, unlock, description, parent))
        except KeyError:
            continue
    return result


def make_weapon_infobox(weapon: Weapon, t: Template):
    def add_arg(name: str, value):
        value = str(value)
        if value.strip() == "" and t.has_arg(name):
            return
        t.set_arg(name, value + "\n")

    add_arg("Name", weapon.name)
    add_arg("NameCN", weapon.name_cn)
    add_arg("Type", weapon.type)
    add_arg("Unlock", weapon.unlock)
    add_arg("Description", weapon.description)
    add_arg("File", weapon.file)
    return t


class WeaponType(Enum):
    PRIMARY = "Primary weapon"
    SECONDARY = "Secondary weapon"
    GRENADE = "Grenade"


def process_infobox(page: Page, weapon: Weapon, weapon_id_to_char_name: dict[int, str], weapon_type: WeaponType):
    if weapon.id not in weapon_id_to_char_name and weapon_type != WeaponType.PRIMARY:
        file_name = f"Weapon {weapon.name}.png"
        source_page = FilePage(bwiki(), f"File:武器-{weapon.name_cn}.png")
        target_page = FilePage(s, f"File:{file_name}")
        if not target_page.exists():
            if not source_page.exists():
                print(f"{weapon.name_cn} not found on bwiki")
                return

            upload_file(target=target_page, url=source_page.get_file_url(),
                        summary="upload weapon image",
                        text="Image sourced from bwiki under CC BY-NC-SA 4.0")
        weapon.file = file_name
    elif weapon.id in weapon_id_to_char_name:
        char_name = weapon_id_to_char_name[weapon.id]
        weapon.file = f"{char_name} GrowthWeapon.png"
    else:
        print(f"Skipping {weapon.name}")
        return
    parsed = wtp.parse(page.text)
    add_template = False
    for t in parsed.templates:
        if t.name.strip() == "WeaponInfobox":
            break
    else:
        t = wtp.Template("{{WeaponInfobox\n}}")
        add_template = True
    make_weapon_infobox(weapon, t)
    text = str(parsed)
    if "{{WeaponNavbox}}" not in text:
        text += "\n\n{{WeaponNavbox}}"
    if add_template:
        text = str(t) + text
    page.text = text


def make_damage_section(p: Page, bwiki_page: Page):
    text = bwiki_page.text
    result_list = re.findall(r"\|(头部|上身|下身)(10|30|50)米伤害=(\d+)", text)
    if len(result_list) != 9:
        print("Skipping " + bwiki_page.title() + " because there's no damage section")
        return
    result = ['{| class="wikitable"',
              "|+Base Damage",
              "! !! 10m !! 30m !! 50m",
              f"|-\n| Head || {' || '.join(r[2] for r in result_list[0:3])}",
              f"|-\n| Body || {' || '.join(r[2] for r in result_list[3:6])}",
              f"|-\n| Legs || {' || '.join(r[2] for r in result_list[6:9])}",
              "|}"]
    text = p.text
    parsed = wtp.parse(text)
    result = "\n".join(result)
    for section in parsed.sections:
        if section.title is not None and section.title == "Damage":
            section.contents = result
            p.text = str(parsed)
            return
    p.text = p.text.replace("{{WeaponNavbox", "==Damage==\n" + result + "\n" + "{{WeaponNavbox")


def process_weapon_pages():
    types = [WeaponType.PRIMARY, WeaponType.SECONDARY, WeaponType.GRENADE]
    strings = ["Primary", "Secondary", "Grenade"]
    weapon_id_to_char_name = {}

    for char_id, char_name in char_id_mapper.items():
        weapon_id = get_default_weapon_id(char_id)
        weapon_id_to_char_name[weapon_id] = char_name

    for i, weapon_type in enumerate(types):
        weapons = get_weapons_by_type(strings[i])
        cn_name_to_bwiki_page = {}
        pages = [Page(bwiki(), w.name_cn) for w in weapons]
        gen = PreloadingGenerator(pages)
        for page in gen:
            cn_name_to_bwiki_page[page.title()] = page
        for w in weapons:
            if w.parent != w.id:
                print(f"Skipping {w.name}")
                continue
            w.type = weapon_type.value
            p = Page(s, w.name)
            original = p.text
            # process_infobox(p, w, weapon_id_to_char_name, weapon_type)
            bwiki_page = cn_name_to_bwiki_page[w.name_cn]
            make_damage_section(p, bwiki_page)
            if p.text.strip() != original:
                p.save(summary="weapon page")


def main():
    process_weapon_pages()


if __name__ == '__main__':
    main()

from dataclasses import dataclass

import wikitextparser as wtp
from pywikibot import Page, FilePage
from wikitextparser import Template

from global_config import char_id_mapper
from utils.uploader import upload_file
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


def make_all_weapons():
    types = ["Primary weapon", "Secondary weapon", "Grenade"]
    strings = ["Primary", "Secondary", "Grenade"]
    weapon_id_to_char_name = {}

    for char_id, char_name in char_id_mapper.items():
        weapon_id = get_default_weapon_id(char_id)
        weapon_id_to_char_name[weapon_id] = char_name

    for i, weapon_type in enumerate(types):
        weapons = get_weapons_by_type(strings[i])
        for w in weapons:
            if w.parent != w.id:
                print(f"Skipping {w.name}")
                continue
            w.type = weapon_type
            if w.id not in weapon_id_to_char_name and weapon_type != types[0]:
                file_name = f"Weapon {w.name}.png"
                source_page = FilePage(bwiki(), f"File:武器-{w.name_cn}.png")
                target_page = FilePage(s, f"File:{file_name}")
                if not target_page.exists():
                    if not source_page.exists():
                        print(f"{w.name_cn} not found on bwiki")
                        continue

                    upload_file(target=target_page, url=source_page.get_file_url(),
                                summary="upload weapon image",
                                text="Image sourced from bwiki under CC BY-NC-SA 4.0")
                w.file = file_name
            elif w.id in weapon_id_to_char_name:
                char_name = weapon_id_to_char_name[w.id]
                w.file = f"{char_name} GrowthWeapon.png"
            else:
                print(f"Skipping {w.name}")
                continue

            p = Page(s, w.name)
            parsed = wtp.parse(p.text)
            add_template = False
            for t in parsed.templates:
                if t.name.strip() == "WeaponInfobox":
                    break
            else:
                t = wtp.Template("{{WeaponInfobox\n}}")
                add_template = True
            make_weapon_infobox(w, t)
            text = str(parsed)
            if "{{WeaponNavbox}}" not in text:
                text += "\n\n{{WeaponNavbox}}"
            if add_template:
                text = str(t) + text
            if p.text.strip() != text.strip():
                p.text = text
                p.save(summary="weapon page")


def main():
    make_all_weapons()


if __name__ == '__main__':
    main()

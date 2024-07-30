from dataclasses import dataclass

from pywikibot import Page, FilePage
import wikitextparser as wtp
from pywikibot.site._upload import Uploader
from wikitextparser import Template

from utils import get_game_json, get_table, get_game_json_cn, s, char_id_mapper, get_default_weapon_id, bwiki


@dataclass
class Weapon:
    id: int
    name: str
    name_cn: str
    unlock: str
    description: str
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
            result.append(Weapon(weapon_id, name, name_cn, unlock, description))
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
            w.type = weapon_type
            if w.id not in weapon_id_to_char_name:
                file_name = f"Weapon {w.name}.png"
                source_page = FilePage(bwiki(), f"File:武器-{w.name_cn}.png")
                target_page = FilePage(s, f"File:{file_name}")
                if not target_page.exists():
                    if not source_page.exists():
                        print(f"{w.name_cn} not found on bwiki")
                        continue
                    Uploader(s, target_page, source_url=source_page.get_file_url(),
                             comment="upload weapon image",
                             text="Image sourced from bwiki under CC BY-NC-SA 4.0").upload()
                w.file = file_name
            else:
                char_name = weapon_id_to_char_name[w.id]
                w.file = f"{char_name} GrowthWeapon.png"

            p = Page(s, w.name)
            t = Template("{{WeaponInfobox\n}}")
            make_weapon_infobox(w, t)
            p.text = str(t) + "\n\n{{WeaponNavbox}}"
            p.save(summary="Batch create weapon pages")


def main():
    make_all_weapons()


if __name__ == '__main__':
    main()
import re
from dataclasses import dataclass
from enum import Enum

import wikitextparser as wtp
from pywikibot import Page, FilePage
from pywikibot.pagegenerators import PreloadingGenerator
from wikitextparser import Template

from global_config import char_id_mapper
from utils.upload_utils import upload_file, UploadRequest, upload_item_icons, process_uploads
from utils.general_utils import get_table, get_default_weapon_id
from utils.json_utils import get_game_json, get_game_json_cn
from utils.wiki_utils import bwiki, s


@dataclass
class Weapon:
    id: int
    name_en: str
    name_cn: str
    quality: int
    unlock: str
    description: str
    parent: "Weapon" = None
    type: str = ""
    file: str = ""
    file_scope: FilePage | None = None
    file_screenshot: FilePage | None = None

    def get_variant_bwiki_screenshot_name(self):
        return f"{self.parent.name_cn}-{self.name_cn}.png".replace(" ", "_")

    def get_variant_bwiki_scope_name(self):
        return f"瞄准镜样式 {self.parent.name_cn}{self.name_cn}.png".replace(" ", "_")

    def get_variant_screenshot_name(self):
        return f"{self.parent.name_en} {self.name_en} screenshot.png".replace(" ", "_")

    def get_variant_scope_name(self):
        return f"{self.parent.name_en} {self.name_en} scope.png".replace(" ", "_")

    def get_icon_name(self):
        return f"Item Icon {self.id}.png"


def get_weapons_by_type(weapon_type: str) -> list[Weapon]:
    i18n = get_game_json()['Weapon']
    i18n = get_game_json()['Goods'] | i18n
    i18n_cn = get_game_json_cn()['Weapon']
    weapons = get_table("Weapon")
    result = []
    weapon_dict: dict[int, Weapon] = {}
    parent_dict: dict[int, int] = {}
    for k, v in weapons.items():
        if weapon_type not in v['Slot']:
            continue
        try:
            weapon_id = k
            name_key = f"{weapon_id}_Name"
            name = i18n.get(name_key, "")
            name_cn = v['Name']['SourceString']
            quality = v['Quality']
            unlock = i18n.get(f"{weapon_id}_GainParam2", "" if v['Default'] != 1 else "Available by default")
            description = i18n.get(f"{weapon_id}_Desc", i18n.get(f"{weapon_id}_Tips", v['Tips']['SourceString']))
            parent = v['SubType']
            parent_dict[weapon_id] = parent
            w = Weapon(weapon_id, name, name_cn, quality, unlock, description)
            result.append(w)
            weapon_dict[w.id] = w
        except KeyError:
            continue
    for w in result:
        w.parent = weapon_dict[parent_dict[w.id]]
    return result


def make_weapon_infobox(weapon: Weapon, t: Template):
    def add_arg(name: str, value):
        value = str(value)
        if value.strip() == "" and t.has_arg(name):
            return
        t.set_arg(name, value + "\n")

    add_arg("Name", weapon.name_en)
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
        file_name = f"Weapon {weapon.name_en}.png"
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
        print(f"Skipping {weapon.name_en}")
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


def process_weapon_pages(*args):
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
            if w.parent.id != w.id or w.name_en == "":
                print(f"Skipping {w.name_en} ({w.name_cn})")
                continue
            w.type = weapon_type.value
            p = Page(s, w.name_en)
            original = p.text
            # process_infobox(p, w, weapon_id_to_char_name, weapon_type)
            bwiki_page = cn_name_to_bwiki_page[w.name_cn]
            make_damage_section(p, bwiki_page)
            if p.text.strip() != original:
                p.save(summary="weapon page")


def upload_weapon_variants(weapons: list[Weapon]) -> list[Weapon]:
    failed_uploads = upload_item_icons([w.id for w in weapons], text="[[Category:Weapon icons]]", big=True)
    weapons = [w for w in weapons if w.id not in failed_uploads]
    return weapons
    # bwiki_pages: list[FilePage] = [FilePage(bwiki(), f"File:{w.get_variant_bwiki_screenshot_name()}")
    #                                for w in weapons] + \
    #                               [FilePage(bwiki(), f"File:{w.get_variant_bwiki_scope_name()}")
    #                                for w in weapons]
    # existing: dict[str, FilePage] = dict((p.title(with_ns=False, underscore=True), p)
    #                                      for p in PreloadingGenerator(bwiki_pages) if p.exists())
    # upload_requests: list[UploadRequest] = []
    # for w in weapons:
    #     if w.get_variant_bwiki_screenshot_name() in existing:
    #         fp = FilePage(s, "File:" + w.get_variant_screenshot_name())
    #         w.file_screenshot = fp
    #         if not fp.exists():
    #             url = existing[w.get_variant_bwiki_screenshot_name()].get_file_url()
    #             upload_file(f"Image sourced from bwiki under CC BY-NC-SA 4.0.\n\n[[Category:Weapon screenshots]]", fp, url=url)
    #     if w.get_variant_bwiki_scope_name() in existing:
    #         fp = FilePage(s, "File:" + w.get_variant_scope_name())
    #         w.file_scope = fp
    #         if not fp.exists():
    #             url = existing[w.get_variant_bwiki_scope_name()].get_file_url()
    #             upload_file(f"Image sourced from bwiki under CC BY-NC-SA 4.0.\n\n[[Category:Weapon scopes]]", fp, url=url)
    # process_uploads(upload_requests)


def process_weapon_skins(*args):
    weapons = dict((w.id, w) for w in get_weapons_by_type("Primary"))

    children: dict[int, list[Weapon]] = {}
    for w in weapons.values():
        parent = w.parent
        if parent.id == w.id:
            continue
        if parent.id not in children:
            children[parent.id] = []
        children[parent.id].append(w)
    uploaded_weapons = set(w.id for w in upload_weapon_variants([w for w in weapons.values() if w.id != w.parent.id]))
    for weapon_id, variants in children.items():
        variants = [v for v in variants if v.id in uploaded_weapons]
        weapon = weapons[weapon_id]
        if weapon.name_en == "":
            print(f'{weapon.name_cn} does not have a EN name')
            continue
        p = Page(s, weapon.name_en)
        parsed = wtp.parse(p.text)
        for t in parsed.templates:
            if t.name.strip() == "WeaponSkins":
                break
        else:
            print(f"{weapon.name_en} does not have skin template")
            continue
        t.string = "{{WeaponSkins\n}}"
        make_weapon_skins_template(t, list(sorted(variants, key=lambda x: x.quality, reverse=True)))
        text = str(parsed)
        if p.text.strip() != text.strip():
            p.text = text
            p.save("update weapon skins")


def make_weapon_skins_template(t: wtp.Template, weapon_list: list[Weapon]):
    result: list[dict[str, str]] = []
    for w in weapon_list:
        d = {
            'Name': w.name_en if w.name_en != "" else w.name_cn,
            'Description': w.description,
            'Icon': w.get_icon_name(),
            'Quality': str(w.quality)
        }
        if w.file_screenshot is not None:
            d['Screenshot'] = w.file_screenshot.title(with_ns=False, underscore=True)
        if w.file_scope is not None:
            d['Scope'] = w.file_scope.title(with_ns=False, underscore=True)
        result.append(d)
    for index, weapon_dict in enumerate(result, 1):
        for key, value in weapon_dict.items():
            t.set_arg(f"{key}{index}", value + "\n")


def main():
    process_weapon_skins()


if __name__ == '__main__':
    main()

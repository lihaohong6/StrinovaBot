import re
from dataclasses import dataclass
from enum import Enum

import wikitextparser as wtp
from pywikibot import Page, FilePage
from pywikibot.pagegenerators import PreloadingGenerator
from wikitextparser import Template

from global_config import char_id_mapper
from utils.general_utils import get_table, get_default_weapon_id, save_json_page
from utils.json_utils import get_all_game_json
from utils.lang import CHINESE, ENGLISH
from utils.lang_utils import get_multilanguage_dict
from utils.upload_utils import upload_file, upload_item_icons, UploadRequest, process_uploads
from utils.wiki_utils import bwiki, s


@dataclass
class Weapon:
    id: int
    name: dict[str, str]
    quality: int
    unlock: dict[str, str]
    description: dict[str, str]
    char: str = None
    parent: "Weapon" = None
    type: str = ""
    file: str = ""
    file_scope: FilePage | None = None
    file_screenshot: FilePage | None = None

    @property
    def name_cn(self):
        return self.name[CHINESE.code]

    @property
    def name_en(self):
        return self.name.get(ENGLISH.code)

    def get_variant_bwiki_screenshot_name(self):
        return f"{self.parent.name_cn}-{self.name_cn}.png".replace(" ", "_")

    def get_variant_bwiki_scope_name(self):
        if self.parent is not None:
            return f"瞄准镜样式 {self.parent.name_cn}{self.name_cn}.png".replace(" ", "_")
        return f"瞄准镜样式 {self.name_cn}.png".replace(" ", "_")

    def get_variant_screenshot_name(self):
        return f"{self.parent.name_cn} {self.name_cn} screenshot.png".replace(" ", "_")

    def get_variant_scope_name(self):
        if self.parent is not None:
            return f"{self.parent.name_cn} {self.name_cn} scope.png".replace(" ", "_")
        return f"{self.name_cn} scope.png".replace(" ", "_")

    def get_icon_name(self):
        return f"Item Icon {self.id}.png"

    @property
    def icon(self):
        return "File:" + self.get_icon_name()


def get_weapons_by_type(weapon_type: str = None) -> list[Weapon]:
    i18n = get_all_game_json('Weapon')
    i18n = get_all_game_json('Goods') | i18n
    weapons = get_table("Weapon")
    result = []
    weapon_dict: dict[int, Weapon] = {}
    parent_dict: dict[int, int] = {}
    for k, v in weapons.items():
        if weapon_type is not None and weapon_type not in v['Slot']:
            continue
        try:
            weapon_id = k
            name_key = f"{weapon_id}_Name"
            name = get_multilanguage_dict(i18n, name_key, extra=v['Name']['SourceString'])
            quality = v['Quality']
            unlock = get_multilanguage_dict(i18n, f"{weapon_id}_GainParam2",
                                            default=None if v['Default'] != 1 else "Available by default")
            description = get_multilanguage_dict(i18n, f"{weapon_id}_Tips",
                                                 extra=v.get('Tips', {}).get('LocalizedString', None))
            parent = v['SubType']
            parent_dict[weapon_id] = parent
            w = Weapon(weapon_id, name, quality, unlock, description)
            result.append(w)
            weapon_dict[w.id] = w
        except KeyError:
            continue
    for w in result:
        w.parent = weapon_dict.get(parent_dict.get(w.id, None), None)
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
        for w in weapons:
            if w.parent.id != w.id or w.name_en is None or w.name_en == "":
                continue
            w.type = weapon_type.value
            p = Page(s, w.name_en)
            original = p.text
            process_infobox(p, w, weapon_id_to_char_name, weapon_type)
            if p.text.strip() != original:
                p.save(summary="weapon page")


def upload_weapon_variants(weapons: list[Weapon]) -> list[Weapon]:
    failed_uploads = upload_item_icons([w.id for w in weapons], text="[[Category:Weapon icons]]")
    weapons = [w for w in weapons if w.id not in failed_uploads]
    bwiki_pages: list[FilePage] = (
            # [FilePage(bwiki(), f"File:{w.get_variant_bwiki_screenshot_name()}")
            #  for w in weapons] +
            [FilePage(bwiki(), f"File:{w.get_variant_bwiki_scope_name()}")
             for w in weapons])
    existing: dict[str, FilePage] = dict((p.title(with_ns=False, underscore=True), p)
                                         for p in PreloadingGenerator(bwiki_pages) if p.exists())
    upload_requests: list[UploadRequest] = []
    for w in weapons:
        # ss_name = w.get_variant_bwiki_screenshot_name()
        # if ss_name in existing:
        #     fp = FilePage(s, "File:" + w.get_variant_screenshot_name())
        #     w.file_screenshot = fp
        #     bwiki_page = existing[ss_name]
        #     upload_requests.append(UploadRequest(
        #         bwiki_page,
        #         fp,
        #         f"Image sourced from bwiki under CC BY-NC-SA 4.0. Link: {bwiki_page.title(as_link=True)}\n\n"
        #         f"[[Category:Weapon screenshots]]"
        #     ))
        scope_name = w.get_variant_bwiki_scope_name()
        if scope_name in existing:
            fp = FilePage(s, "File:" + w.get_variant_scope_name())
            w.file_scope = fp
            bwiki_page = existing[scope_name]
            upload_requests.append(UploadRequest(
                bwiki_page,
                fp,
                f"Image sourced from bwiki under CC BY-NC-SA 4.0. Link: {bwiki_page.title(as_link=True)}\n\n"
                f"[[Category:Weapon scopes]]"
            ))
    process_uploads(upload_requests)
    return weapons


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
    result: dict[str, list[dict]] = {}
    for weapon_id, variants in children.items():
        variants = [v for v in variants if v.id in uploaded_weapons]
        variants.sort(key=lambda x: x.quality, reverse=True)
        weapon = weapons[weapon_id]
        name_en = weapon.name_en
        if name_en is None or name_en == "":
            print(f'{weapon.name_cn} does not have a EN name')
            continue
        lst = []
        result[name_en] = lst
        for v in variants:
            lst.append({
                'id': v.id,
                'name': v.name,
                'quality': v.quality,
                'unlock': v.unlock,
                'description': v.description,
                'icon': v.get_icon_name(),
                'scope': v.get_variant_scope_name() if v.file_scope is not None else "",
                'parent': -1 if v.parent is None else v.parent.id
            })
    save_json_page("Module:WeaponSkins/data.json", result)


def main():
    process_weapon_pages()
    process_weapon_skins()


if __name__ == '__main__':
    main()

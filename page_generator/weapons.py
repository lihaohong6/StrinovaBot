from dataclasses import dataclass
from enum import Enum
from functools import cache

from pywikibot import FilePage
from pywikibot.pagegenerators import PreloadingGenerator

from global_config import char_id_mapper
from utils.asset_utils import global_resources_root
from utils.general_utils import get_char_id_to_weapon_id, split_dict
from utils.json_utils import get_all_game_json, get_table
from utils.lang import CHINESE, ENGLISH
from utils.lang_utils import get_multilanguage_dict, get_text
from utils.upload_utils import upload_item_icons, UploadRequest, process_uploads
from utils.wiki_utils import bwiki, s, save_json_page


class WeaponType(Enum):
    PRIMARY = "Primary Weapon"
    SECONDARY = "Secondary Weapon"
    GRENADE = "Grenade"

    def get_string(self):
        return self.value.split(" ")[0]


@dataclass
class Weapon:
    id: int
    name: dict[str, str]
    quality: int
    unlock: dict[str, str]
    description: dict[str, str]
    char: str = None
    parent: "Weapon" = None
    type: WeaponType = None
    file: str = ""
    file_scope: FilePage | None = None
    file_screenshot: FilePage | None = None

    @property
    def name_cn(self):
        return self.name[CHINESE.code]

    @property
    def name_en(self):
        return self.name.get(ENGLISH.code, None)

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

    def file_page(self) -> FilePage:
        return FilePage(s, "File:" + self.get_variant_scope_name())


@cache
def parse_weapons() -> dict[int, Weapon]:
    i18n = get_all_game_json('Weapon')
    i18n = get_all_game_json('Goods') | i18n
    unlock_i18n = get_all_game_json("ST_ModuleName")
    weapons = get_table("Weapon")
    weapon_dict: dict[int, Weapon] = {}
    parent_dict: dict[int, int] = {}
    for k, v in weapons.items():
        type_list = [weapon_type for weapon_type in WeaponType if weapon_type.get_string() in v['Slot']]
        if len(type_list) == 0:
            continue
        assert len(type_list) == 1
        weapon_type = type_list[0]
        weapon_id = k
        name = get_text(i18n, v['Name'])
        quality = v['Quality']
        unlock = None
        if "GainParam2" in v:
            gain_param = v["GainParam2"]
            # can't handle primary weapons right now
            if "SourceFmt" in gain_param and weapon_type is not WeaponType.PRIMARY:
                unlock = get_multilanguage_dict(unlock_i18n, gain_param["SourceFmt"]["Key"],
                                                converter=lambda x: x.replace("{0}",
                                                                              str(gain_param["Arguments"][0]['Value'])))
        if unlock is None:
            unlock = get_multilanguage_dict(i18n, f"{weapon_id}_GainParam2",
                                            default=None)
        description = get_text(i18n, v['Tips'])
        parent = v['SubType']
        parent_dict[weapon_id] = parent
        w = Weapon(weapon_id, name, quality, unlock, description, type=weapon_type)
        weapon_dict[w.id] = w
    for w in weapon_dict.values():
        w.parent = weapon_dict.get(parent_dict.get(w.id, None), None)
        if w.parent is not None and w.parent.id == w.id:
            w.parent = None

    weapon_id_to_char_name = {}
    for char_id, weapon_id in get_char_id_to_weapon_id().items():
        weapon_id_to_char_name[weapon_id] = char_id_mapper[char_id]

    for w in weapon_dict.values():
        if w.id in weapon_id_to_char_name:
            w.char = weapon_id_to_char_name[w.id]
        else:
            w.char = weapon_id_to_char_name.get(w.parent.id if w.parent is not None else -1, None)

    for w in weapon_dict.values():
        if w.type == WeaponType.PRIMARY and w.parent is None:
            w.file = f"File:{w.char} GrowthWeapon.png"
        else:
            w.file = f"File:Weapon {w.name_en}.png"

    return weapon_dict


def get_weapons_by_type(weapon_type: WeaponType | None = None) -> list[Weapon]:
    return [w for w in parse_weapons().values() if weapon_type is None or w.type == weapon_type]


def upload_weapon_images(weapons: list[Weapon]):
    raise RuntimeError("Do not call this function: all primary weapons are already taken care of by "
                       "another function; secondary weapons and grenades should undergo minimal changes.")
    weapons = [w for w in weapons if w.type == WeaponType.PRIMARY and w.parent is None]
    requests = []
    for weapon in weapons:
        file_name = f"Weapon {weapon.name_en}.png"
        source_page = FilePage(bwiki(), f"File:武器-{weapon.name_cn}.png")
        target_page = FilePage(s, f"File:{file_name}")
        requests.append(UploadRequest(source_page, target_page,
                                      text=f"Image sourced from bwiki under CC BY-NC-SA 4.0 ({source_page.full_url()})"))
    process_uploads(requests)


def process_weapon_pages(*args):
    weapon_list = list(parse_weapons().values())
    weapon_list = [w for w in weapon_list if w.parent is None and w.name_en is not None]
    obj: dict[str, dict] = {}
    for w in weapon_list:
        weapon = {}
        fields = ['name', 'description', 'file', 'unlock']
        for f in fields:
            weapon[f] = getattr(w, f)
        weapon['type'] = w.type.value
        obj[w.name_en] = weapon
    save_json_page("Module:Weapon/data.json", obj)


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
        fp = w.file_page()
        if scope_name in existing or w.quality >= 3:
            w.file_scope = fp
        if scope_name in existing:
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
    weapons = dict((w.id, w) for w in get_weapons_by_type(WeaponType.PRIMARY))

    children: dict[int, list[Weapon]] = {}
    for w in weapons.values():
        parent = w.parent
        if parent is None or parent.id == w.id:
            continue
        if parent.id not in children:
            children[parent.id] = []
        children[parent.id].append(w)
    uploaded_weapons = set(w.id for w in upload_weapon_variants([w for w in weapons.values()
                                                                 if w.parent is not None and w.parent.id != w.id]))
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
    dicts = list(split_dict(result))
    for index, d in enumerate(dicts, 1):
        save_json_page(f"Module:WeaponSkins/data{index}.json", d)


def upload_weapon_white_icons():
    weapons = [w for w in get_weapons_by_type() if w.parent is None]
    req = []
    for w in weapons:
        source = global_resources_root / "Weapon" / "WeaponIconWhite" / f"T_Dynamic_WeaponWhite_{w.id}.png"
        if not source.exists():
            print(w.name_en)
            continue
        target = f"{w.name_en} icon white.png"
        req.append(UploadRequest(source, target, "[[Category:Weapon white icons]]"))
    # Ignore dups for now because of Lawine's weapon name change
    process_uploads(req, ignore_dup=True)



def main():
    process_weapon_pages()
    process_weapon_skins()
    upload_weapon_white_icons()


if __name__ == '__main__':
    main()

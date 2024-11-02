import json
from dataclasses import dataclass
from heapq import merge

import wikitextparser as wtp
from pywikibot import FilePage, Page
from pywikibot.pagegenerators import PreloadingGenerator

from utils.asset_utils import portrait_root, skin_back_root, local_asset_root, resource_root
from utils.general_utils import get_table, get_char_by_id, get_cn_wiki_skins, \
    en_name_to_zh, cn_name_to_en, save_json_page, pick_string_length, merge_dict2
from utils.json_utils import get_all_game_json
from utils.lang import CHINESE
from utils.lang_utils import get_multilanguage_dict
from utils.upload_utils import upload_file, UploadRequest, process_uploads
from utils.wiki_utils import bwiki, s


def generate_emotes():
    @dataclass
    class Emote:
        id: int
        name: dict[str, str]
        text: dict[str, str]

    goods_table = get_table("Goods")
    i18n = get_all_game_json('Goods')
    items: dict[str, list[Emote]] = {}
    upload_requests: list[UploadRequest] = []
    for k, v in goods_table.items():
        if v['ItemType'] != 13:
            continue
        name_source = v['Name']['SourceString']
        name_chs = name_source.split("-")[0]
        name_en = cn_name_to_en(name_chs)
        if name_en is None:
            print(f"{name_source} has no EN character name")
            continue
        lst = items.get(name_en, [])
        emote = Emote(k,
                      get_multilanguage_dict(i18n, f'{k}_Name', extra=v['Name']['SourceString']),
                      get_multilanguage_dict(i18n, f'{k}_Desc', extra=v['Desc']['SourceString']))
        lst.append(emote)
        items[name_en] = lst
        upload_requests.append(UploadRequest(resource_root / "Emote" / f"T_Dynamic_Emote_{emote.id}.png",
                                             FilePage(s, f"File:Emote_{emote.id}.png"),
                                             '[[Category:Emotes]]',
                                             "batch upload emotes"))
    process_uploads(upload_requests)
    save_json_page("Module:Emote/data.json", items)


@dataclass
class SkinInfo:
    id: list[int]
    quality: int
    name: dict[str, str]
    description: dict[str, str]
    portrait: str = ""
    back: str = ""

    @property
    def name_cn(self) -> str:
        return self.name[CHINESE.code]

    def get_bwiki_screenshot_front_title(self, char_name: str):
        return f"File:{char_name}时装-{self.name_cn}.png"

    def get_mh_screenshot_front_title(self, char_name: str):
        return f"File:{char_name} Skin {self.name_cn}.png"

    def get_mh_screenshot_back_title(self, char_name: str):
        return f"File:{char_name} Skin Back {self.name_cn}.png"

    def get_mh_portrait_title(self, char_name: str):
        return f"File:{char_name} Skin Portrait {self.name_cn}.png"


def parse_skin_tables() -> dict[str, list[SkinInfo]]:
    skins_table = get_table("RoleSkin")
    store_skins_table = get_table("Goods")
    skins: dict[str, list[SkinInfo]] = {}

    def add_skin(char_name, skin_id, quality, name, description):
        lst = skins.get(char_name, [])
        # avoid dups
        duplicates = [skin for skin in lst if skin.name[CHINESE.code] == name[CHINESE.code]]
        if len(duplicates) > 0:
            assert len(duplicates) == 1
            d = duplicates[0]
            d.id.append(skin_id)
            if d.quality != quality:
                print(f"Quality mismatch for {char_name}: {skin_id} and {d.id}")
                d.quality = 0 if min(quality, d.quality) == 0 else max(quality, d.quality)
                d.description = merge_dict2(d.description, description)
            return
        lst.append(SkinInfo([skin_id], quality, name, description))
        skins[char_name] = lst

    for k, v in skins_table.items():
        skin_id = k
        name = {CHINESE.code: v['NameCn']['SourceString']}
        quality = v['Quality']
        char_name = get_char_by_id(v['RoleId'])
        if char_name is None:
            continue
        description = {CHINESE.code: v['Description'].get("SourceString", "")}
        add_skin(char_name, skin_id, quality, name, description)
    cn_skin_name_to_char_name = get_cn_wiki_skins()
    for k, v in store_skins_table.items():
        # 4: skin; 8: IDCard
        if v['ItemType'] not in {4, 8}:
            continue
        skin_id = v['Id']
        name_cn = v['Name']['SourceString']
        quality = v['Quality']
        if name_cn not in cn_skin_name_to_char_name:
            continue
        char_name = cn_name_to_en(cn_skin_name_to_char_name[name_cn])
        assert char_name is not None
        add_skin(char_name, skin_id, quality,
                 {CHINESE.code: name_cn},
                 {CHINESE.code: v['Desc'].get('SourceString', "")})
    return skins


def upload_skins(char_name: str, skin_list: list[SkinInfo]) -> list[SkinInfo]:
    @dataclass
    class Skin:
        source: FilePage
        target: FilePage
        skin: SkinInfo

    name_zh = en_name_to_zh[char_name]
    skins = [Skin(FilePage(bwiki(), skin.get_bwiki_screenshot_front_title(name_zh)),
                  FilePage(s, skin.get_mh_screenshot_front_title(char_name)),
                  skin)
             for skin in skin_list]

    existing_source = set(p.title()
                          for p in PreloadingGenerator(skin.source for skin in skins)
                          if p.exists())
    existing_targets = set(p.title()
                           for p in PreloadingGenerator(skin.target for skin in skins)
                           if p.exists())

    skin_list: list[SkinInfo] = []
    for skin in skins:
        if skin.target.title() not in existing_targets:
            if skin.source.title() not in existing_source:
                continue
            upload_file(text=f"Taken from [https://wiki.biligame.com/klbq/"
                             f"{skin.source.title(with_ns=True, underscore=True)} bwiki], "
                             f"this image is licensed under CC BY-NC-SA 4.0."
                             f"[[Category:Skin screenshots]]\n[[Category:{char_name} images]]",
                        target=skin.target,
                        summary="upload file from bwiki",
                        url=skin.source.get_file_url())
        skin_list.append(skin.skin)

    process_portraits(char_name, name_zh, skin_list)
    process_back_images(char_name, name_zh, skin_list)

    return skin_list


def process_portraits(char_name: str, name_zh: str, skin_list: list[SkinInfo]):
    # process portraits
    targets = [FilePage(s, skin.get_mh_portrait_title(char_name)) for skin in skin_list]
    existing_targets = set(p.title()
                           for p in PreloadingGenerator(targets)
                           if p.exists())
    for index, skin in enumerate(skin_list):
        target = targets[index]
        if target.title() not in existing_targets:
            possible_sources = [
                portrait_root / f"{name_zh}时装立绘-{skin.name_cn}.png",
                portrait_root / f"{name_zh.split('·')[0]}时装立绘-{skin.name_cn}.png",
                local_asset_root / f"{char_name} Skin Portrait {skin.name_cn}.png",
            ]
            for source in possible_sources:
                if source.exists():
                    break
            else:
                continue
            upload_file(text="[[Category:Skin portraits]]",
                        target=target,
                        summary="upload portrait file",
                        file=source)
        skin.portrait = skin.name_cn


def process_back_images(char_name: str, name_zh: str, skin_list: list[SkinInfo]):
    # process portraits
    targets = [FilePage(s, skin.get_mh_screenshot_back_title(char_name)) for skin in skin_list]
    existing_targets = set(p.title()
                           for p in PreloadingGenerator(targets)
                           if p.exists())
    for index, skin in enumerate(skin_list):
        target = targets[index]
        if target.title() not in existing_targets:
            source = skin_back_root / f"{name_zh}时装背面-{skin.name_cn}.png"
            if not source.exists():
                source = skin_back_root / f"{name_zh.split('·')[0]}时装背面-{skin.name_cn}.png"
                if not source.exists():
                    print(source.name + " not found!!!")
                    continue
            upload_file(text="[[Category:Skin back screenshots]]",
                        target=target,
                        summary="upload skin screenshot",
                        file=source)
        skin.back = skin.name_cn


def localize_skins(skin_list: list[SkinInfo]):
    i18n = merge_dict2(get_all_game_json('RoleSkin'), get_all_game_json('Goods'))
    for skin in skin_list:
        name = skin.name
        description = skin.description
        for skin_id in skin.id:
            name = merge_dict2(name, get_multilanguage_dict(i18n, key=f'{skin_id}_NameCn'))
            name = merge_dict2(name, get_multilanguage_dict(i18n, key=f'{skin_id}_Name'))
            description = merge_dict2(description, get_multilanguage_dict(i18n, key=f'{skin_id}_Description'))
            description = merge_dict2(description, get_multilanguage_dict(i18n, key=f'{skin_id}_Desc'))
        skin.name = name
        skin.description = description


def make_skin_template(t: wtp.Template, char_name: str, skin_list: list[SkinInfo]) -> None:
    raise RuntimeError("This function is obsolete")
    skin_list.sort(key=lambda x: x.quality if x.quality != 0 else 100, reverse=True)
    skin_list: list[SkinInfo] = upload_skins(char_name, skin_list)

    skin_counter = 1

    def add_arg(name, value, after: str = None):
        # if (t.has_arg(name) and value.strip() == "") or value.strip() == "!NoTextFound!":
        #     return
        t.set_arg(name, value + "\n", after=after)

    for skin in skin_list:
        name_local = skin.name_local
        description = skin.description_local
        add_arg(f"Name{skin_counter}", name_local)
        add_arg(f"Quality{skin_counter}", str(skin.quality))
        add_arg(f"Description{skin_counter}", description)
        add_arg(f"Back{skin_counter}", skin.back, after=f"Description{skin_counter}")
        add_arg(f"Portrait{skin_counter}", skin.portrait, after=f"Description{skin_counter}")
        add_arg(f"CNName{skin_counter}", skin.name_cn, after=f"Description{skin_counter}")
        skin_counter += 1


def generate_skins():
    skins = parse_skin_tables()
    for char_name, skin_list in skins.items():
        localize_skins(skin_list)
        skin_list.sort(key=lambda x: x.quality if x.quality != 0 else 100, reverse=True)
        skin_list2: list[SkinInfo] = upload_skins(char_name, skin_list)
        skin_list.clear()
        skin_list.extend(skin_list2)

    p = Page(s, "Module:CharacterSkins/data.json")
    original_json = json.loads(p.text)

    for char_name, skin_list in skins.items():
        name_cn_to_localization: dict[str, tuple[dict, dict]] = {}
        for skin in original_json.get(char_name, []):
            name_cn_to_localization[skin['name']['cn']] = (skin['name'], skin['description'])
        for skin in skin_list:
            if skin.name_cn not in name_cn_to_localization:
                continue
            original_names, original_descriptions = name_cn_to_localization[skin.name_cn]
            skin.name = merge_dict2(skin.name, original_names)
            skin.description = merge_dict2(skin.description, original_descriptions)

    save_json_page("Module:CharacterSkins/data.json", skins)
    print("Skins done")


if __name__ == '__main__':
    generate_skins()
    generate_emotes()

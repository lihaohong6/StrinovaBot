import json
from dataclasses import dataclass
from functools import cache

from pywikibot import FilePage, Page
from pywikibot.pagegenerators import PreloadingGenerator

from utils.asset_utils import resource_root
from utils.general_utils import get_table, get_char_by_id, get_cn_wiki_skins, \
    en_name_to_zh, cn_name_to_en, save_json_page, merge_dict2
from utils.json_utils import get_all_game_json
from utils.lang import CHINESE
from utils.lang_utils import get_multilanguage_dict
from utils.upload_utils import upload_file, UploadRequest, process_uploads, upload_item_icons
from utils.wiki_utils import bwiki, s


@dataclass
class Emote:
    id: int
    quality: int
    name: dict[str, str]
    text: dict[str, str]

    @property
    def icon(self):
        return f"File:Emote_{self.id}.png"

    @property
    def description(self):
        return self.text

    @property
    def get_local_path(self):
        return f"Emote/T_Dynamic_Emote_{self.id}.png"


def parse_emotes() -> dict[str, list[Emote]]:
    goods_table = get_table("Emote")
    i18n = get_all_game_json('Emote')
    items: dict[str, list[Emote]] = {}
    for k, v in goods_table.items():
        # if v['ItemType'] != 13:
        #     continue
        name_source = v['Name']['SourceString']
        role_id = v['RoleSkinId'] // 1000 % 1000
        name_en = get_char_by_id(role_id)
        if name_en is None:
            print(f"{name_source} has no EN character name")
            continue
        lst = items.get(name_en, [])
        emote = Emote(k,
                      v['Quality'],
                      get_multilanguage_dict(i18n, f'{k}_Name', extra=name_source),
                      get_multilanguage_dict(i18n, f'{k}_Desc', extra=v['Desc']['SourceString']))
        lst.append(emote)
        items[name_en] = lst
    return items


def generate_emotes():
    upload_requests: list[UploadRequest] = []
    emotes = parse_emotes()
    for char_name, emote_list in emotes.items():
        for emote in emote_list:
            upload_requests.append(UploadRequest(resource_root / emote.get_local_path,
                                                 FilePage(s, emote.icon),
                                                 '[[Category:Emotes]]',
                                                 "batch upload emotes"))
    process_uploads(upload_requests)
    save_json_page("Module:Emote/data.json", emotes)


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

    def get_mh_screenshot_front_title(self, char_name: str):
        return f"File:{char_name} Skin {self.name_cn}.png"

    def get_bwiki_screenshot_front_title(self, char_name: str):
        return f"File:{char_name}时装-{self.name_cn}.png"

    def get_mh_screenshot_back_title(self, char_name: str):
        return f"File:{char_name} Skin Back {self.name_cn}.png"

    def get_bwiki_screenshot_back_title(self, char_name: str):
        return f"File:{char_name}时装背面-{self.name_cn}.png"

    def get_mh_portrait_title(self, char_name: str):
        return f"File:{char_name} Skin Portrait {self.name_cn}.png"

    def get_bwiki_portrait_title(self, char_name: str):
        return f"File:{char_name}-{self.name_cn}立绘.png"

    @property
    def icon(self):
        if len(self.id) == 1:
            return f"File:Item Icon {self.id[0]}.png"
        else:
            good_id = [sid for sid in self.id if str(sid).startswith("20")]
            assert len(good_id) == 1
            return f"File:Item Icon {good_id[0]}.png"


@cache
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
            if skin_id not in d.id:
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

    for _, skin_list in skins.items():
        localize_skins(skin_list)
    return skins


@dataclass
class SkinUpload:
    source: FilePage
    target: FilePage
    skin: SkinInfo


def upload_skins(char_name: str, skin_list: list[SkinInfo]) -> list[SkinInfo]:
    name_zh = en_name_to_zh[char_name]
    skin_uploads = [SkinUpload(FilePage(bwiki(), skin.get_bwiki_screenshot_front_title(name_zh)),
                               FilePage(s, skin.get_mh_screenshot_front_title(char_name)),
                               skin)
                    for skin in skin_list]

    skin_list = process_skin_upload_requests(char_name, skin_uploads)

    skin_uploads = [SkinUpload(FilePage(bwiki(), skin.get_bwiki_screenshot_back_title(name_zh)),
                               FilePage(s, skin.get_mh_screenshot_back_title(char_name)),
                               skin)
                    for skin in skin_list]
    for skin in process_skin_upload_requests(char_name, skin_uploads,
                                             cat="Skin back screenshots"):
        skin.back = skin.name_cn

    skin_uploads = [SkinUpload(FilePage(bwiki(), skin.get_bwiki_portrait_title(name_zh)),
                               FilePage(s, skin.get_mh_portrait_title(char_name)),
                               skin)
                    for skin in skin_list]
    for skin in process_skin_upload_requests(char_name, skin_uploads,
                                             cat="Skin portraits"):
        skin.portrait = skin.name_cn

    icons: list[int] = []
    for skin in skin_list:
        ids = [sid for sid in skin.id if str(sid).startswith("20")]
        icons.extend(ids)
    upload_item_icons(icons)

    return skin_list


def process_skin_upload_requests(char_name: str, skins: list[SkinUpload],
                                 default_text: str = None,
                                 cat: str = "Skin screenshots",
                                 summary: str = "upload file from bwiki") -> list[SkinInfo]:
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
            text = default_text \
                if default_text is not None \
                else (f"Taken from [https://wiki.biligame.com/klbq/"
                      f"{skin.source.title(with_ns=True, underscore=True)} bwiki], "
                      f"this image is licensed under CC BY-NC-SA 4.0."
                      f"[[Category:{char_name} images]]")
            text += f"\n[[Category:{cat}]]"
            upload_file(text=text,
                        target=skin.target,
                        summary=summary,
                        url=skin.source.get_file_url())
        skin_list.append(skin.skin)
    return skin_list


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


def generate_skins():
    skins = parse_skin_tables()
    for char_name, skin_list in skins.items():
        skin_list.sort(key=lambda x: x.quality if x.quality != 0 else 100, reverse=True)
        skin_list2: list[SkinInfo] = upload_skins(char_name, skin_list)
        skin_list.clear()
        skin_list.extend(skin_list2)

    skin_data_page = Page(s, "Module:CharacterSkins/data.json")
    original_json = json.loads(skin_data_page.text)

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

    save_json_page(skin_data_page, skins)
    print("Skins done")


if __name__ == '__main__':
    generate_emotes()
    generate_skins()

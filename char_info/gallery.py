import json
import subprocess
from dataclasses import dataclass
from functools import cache

from pywikibot import FilePage, Page
from pywikibot.pagegenerators import PreloadingGenerator

from utils.dict_utils import merge_dict2
from utils.file_utils import temp_file_dir, temp_download_dir
from utils.general_utils import get_char_by_id, en_name_to_zh, download_file
from utils.json_utils import get_all_game_json, get_table
from utils.lang import CHINESE
from utils.lang_utils import get_multilanguage_dict
from utils.upload_utils import upload_file, upload_item_icons
from utils.wiki_utils import bwiki, s, save_json_page


@dataclass
class SkinInfo:
    id: int
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
        return f"File:{char_name}时装-{self.name_cn}.jpg"

    def get_mh_screenshot_back_title(self, char_name: str):
        return f"File:{char_name} Skin Back {self.name_cn}.png"

    def get_bwiki_screenshot_back_title(self, char_name: str):
        return f"File:{char_name}时装-{self.name_cn} 背面.jpg"

    def get_mh_portrait_title(self, char_name: str):
        return f"File:{char_name} Skin Portrait {self.name_cn}.png"

    def get_bwiki_portrait_title(self, char_name: str):
        return f"File:{char_name}-{self.name_cn}立绘.png"

    @property
    def icon(self):
        return f"File:Item Icon {self.id}.png"


@cache
def parse_skin_tables() -> dict[str, list[SkinInfo]]:
    skins_table = get_table("RoleSkin")
    skins: dict[str, list[SkinInfo]] = {}

    for k, v in skins_table.items():
        skin_id = k
        name = {CHINESE.code: v['NameCn']['SourceString']}
        quality = v['Quality']
        char_name = get_char_by_id(v['RoleId'])
        if char_name is None:
            continue
        description = {CHINESE.code: v['Description'].get("SourceString", "")}
        lst = skins.get(char_name, [])
        lst.append(SkinInfo(skin_id, quality, name, description))
        skins[char_name] = lst

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
        icons.append(skin.id)
    upload_item_icons(icons)

    return skin_list


def upload_skin_screenshot(source_url: str, target: FilePage, text: str, summary: str) -> None:
    source_ext = source_url.split(".")[-1]
    assert source_ext in ["jpg", "jpeg", "png", "webp"]
    target_ext = target.title().split(".")[-1]
    if source_ext == target_ext:
        upload_file(text, target, summary, file=source_url)
        return
    source_file = temp_download_dir / f"temp.{source_ext}"
    download_file(source_url, source_file)
    temp_file = temp_file_dir / f"temp.{target_ext}"
    subprocess.run(["magick", source_file, temp_file], check=True)
    assert temp_file.exists()
    upload_file(text, target, summary=summary, file=temp_file)
    source_file.unlink()
    temp_file.unlink()


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
            upload_skin_screenshot(skin.source.get_file_url(), skin.target, text, summary)
        skin_list.append(skin.skin)
    return skin_list


def localize_skins(skin_list: list[SkinInfo]):
    i18n = merge_dict2(get_all_game_json('RoleSkin'), get_all_game_json('Goods'))
    for skin in skin_list:
        name = skin.name
        description = skin.description
        skin_id = skin.id
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
    generate_skins()

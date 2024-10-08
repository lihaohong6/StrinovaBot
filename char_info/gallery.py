from dataclasses import dataclass
from functools import reduce

import wikitextparser as wtp
from pywikibot import FilePage
from pywikibot.pagegenerators import PreloadingGenerator

from utils.asset_utils import portrait_root, skin_back_root, local_asset_root, resource_root
from utils.general_utils import get_table, get_char_by_id, get_cn_wiki_skins, \
    en_name_to_zh, get_char_pages, cn_name_to_en
from utils.json_utils import get_game_json
from utils.lang import get_language, ENGLISH
from utils.upload_utils import upload_file, UploadRequest, process_uploads
from utils.wiki_utils import bwiki, s


def generate_emotes():
    @dataclass
    class Emote:
        id: int
        name: str
        text: str

    lang = get_language()
    goods_table = get_table("Goods")
    i18n = get_game_json(lang)['Goods']
    items: dict[str, list[Emote]] = {}
    upload_requests: list[UploadRequest] = []
    for k, v in goods_table.items():
        if v['ItemType'] != 13:
            continue
        name_chs = v['Name']['SourceString'].split("-")[0]
        name_en = cn_name_to_en(name_chs)
        if name_en is None:
            print(f"{name_chs} has no EN name")
            continue
        lst = items.get(name_en, [])
        emote = Emote(k,
                      i18n.get(f'{k}_Name', v['Name']['SourceString']),
                      i18n.get(f'{k}_Desc', v['Desc']['SourceString']))
        lst.append(emote)
        items[name_en] = lst
        upload_requests.append(UploadRequest(resource_root / "Emote" / f"T_Dynamic_Emote_{emote.id}.png",
                                             FilePage(s, f"File:Emote_{emote.id}.png"),
                                             '[[Category:Emotes]]',
                                             "batch upload emotes"))
    process_uploads(upload_requests)

    for char_id, name, p in get_char_pages("/gallery", lang=lang):
        emote_list = items[name]
        gallery = ['<gallery mode="packed">']
        for emote in emote_list:
            split = emote.name.split("-")
            emote_name = "-".join(split[1:]).strip()
            gallery.append(f"Emote_{emote.id}.png|'''{emote_name}'''<br/>{emote.text}")
        gallery.append("</gallery>")
        parsed = wtp.parse(p.text)
        for section in parsed.sections:
            if section.title is not None and section.title.strip() == "Emotes":
                string = "\n".join(gallery) + "\n\n"
                gallery_tags = section.get_tags('gallery')
                if len(gallery_tags) > 0:
                    assert len(gallery_tags) == 1
                    gallery_tags[0].string = string
                else:
                    section.contents = string
                break
        else:
            continue
        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate emotes", minor=False)
    print("Emotes done.")


@dataclass
class SkinInfo:
    id: list[int]
    quality: int
    name_cn: str
    description_cn: str
    name_en: str = ""
    name_local: str = ""
    description_local: str = ""
    portrait: str = ""
    back: str = ""

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

    def add_skin(char_name, skin_id, quality, name_cn, description_cn):
        lst = skins.get(char_name, [])
        # avoid dups
        duplicates = [s for s in lst if s.name_cn == name_cn]
        if len(duplicates) > 0:
            assert len(duplicates) == 1
            d = duplicates[0]
            d.id.append(skin_id)
            if d.quality != quality:
                print(f"Quality mismatch for {char_name}: {skin_id} and {d.id}")
                d.quality = 0 if min(quality, d.quality) == 0 else max(quality, d.quality)
                if len(description_cn) > len(d.description_cn):
                    d.description_cn = description_cn
            return
        lst.append(SkinInfo([skin_id], quality, name_cn, description_cn))
        skins[char_name] = lst

    for k, v in skins_table.items():
        skin_id = k
        name_cn = v['NameCn']['SourceString']
        quality = v['Quality']
        char_name = get_char_by_id(v['RoleId'])
        if char_name is None:
            continue
        if 'SourceString' not in v['Description']:
            continue
        add_skin(char_name, skin_id, quality, name_cn, v['Description']['SourceString'])
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
        add_skin(char_name, skin_id, quality, name_cn, v['Desc']['SourceString'])
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
    lang = get_language()
    i18n_local = get_game_json(lang)['RoleSkin'] | get_game_json(lang)['Goods']
    i18n_en = get_game_json(ENGLISH)['RoleSkin'] | get_game_json(ENGLISH)['Goods']
    for skin in skin_list:
        # get en name and local name
        names = []
        for i18n in [i18n_en, i18n_local]:
            # reset description so that en descriptions will be discarded
            descriptions = []
            name = None
            for skin_id in skin.id:
                k1 = f'{skin_id}_NameCn'
                k2 = f'{skin_id}_Name'
                if k1 in i18n:
                    name = i18n[k1]
                    description = i18n[f'{skin_id}_Description']
                    descriptions.append(description)
                if k2 in i18n:
                    name = i18n[k2]
                    description = i18n.get(f'{skin_id}_Desc', "")
                    descriptions.append(description)
            if name is None or name == '!NoTextFound!':
                name = skin.name_cn
            descriptions = [d for d in descriptions if d != '!NoTextFound!']
            if len(descriptions) == 0:
                descriptions.append(skin.description_cn)
            names.append(name)
        name_en, name_local = names
        skin.name_en = name_en
        skin.name_local = name_local
        skin.description_local = reduce(lambda x, y: x if len(x) > len(y) else y, descriptions, "")


def make_skin_template(t: wtp.Template, char_name: str, skin_list: list[SkinInfo]) -> None:
    skin_list.sort(key=lambda x: x.quality if x.quality != 0 else 100, reverse=True)
    localize_skins(skin_list)
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
    lang = get_language()
    skins = parse_skin_tables()

    for char_id, char_name, p in get_char_pages("/gallery", lang=lang):
        if char_name not in skins:
            print("No skin found for " + char_name)
            continue
        skin_list = skins[char_name]
        if char_name not in en_name_to_zh:
            print("Skipping character " + char_name + " due to lack of en-zh name mapping")
            continue

        parsed = wtp.parse(p.text)
        for template in parsed.templates:
            if template.name.strip() == "CharacterSkins":
                t = template
                break
        else:
            print("Template CharacterSkins not found on " + char_name)
            continue

        t.string = "{{CharacterSkins\n}}"
        make_skin_template(t, char_name, skin_list)

        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate skins", minor=True)
    print("Skins done")


if __name__ == '__main__':
    generate_skins()
    generate_emotes()

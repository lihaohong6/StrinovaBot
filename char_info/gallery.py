import re
from dataclasses import dataclass
from functools import reduce

import wikitextparser as wtp
from pywikibot import Page, FilePage
from pywikibot.pagegenerators import PreloadingGenerator

from uploader import upload_file
from utils import get_table, get_game_json, zh_name_to_en, load_json, get_char_by_id, get_cn_wiki_skins, \
    en_name_to_zh
from wiki_utils import bwiki, s


def generate_emotes():
    goods_table = get_table("Goods")
    i18n = get_game_json()['Goods']
    items: dict[str, list[int]] = {}
    for k, v in goods_table.items():
        if v['ItemType'] != 6:
            continue
        name_chs = v['Name']['SourceString'].split("-")[0]
        name_en = zh_name_to_en(name_chs)
        if name_en is None:
            continue
        lst = items.get(name_en, [])
        lst.append(k)
        items[name_en] = lst

    for name, item_list in items.items():
        gallery = ['<gallery mode="packed">']
        for item in item_list:
            key = f'{item}_Name'
            if key not in i18n:
                continue
            emote_name = i18n[key]
            emote_name = re.search(f"^{name} ?- ?(.*)", emote_name).group(1)
            description = i18n[f'{item}_Desc']
            gallery.append(f"Emote_{item}.png|'''{emote_name}'''<br/>{description}")
        gallery.append("</gallery>")
        p = Page(s, name)
        parsed = wtp.parse(p.text)
        for section in parsed.sections:
            if section.title is not None and section.title.strip() == "Emotes":
                section.contents = "\n".join(gallery) + "\n\n"
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
    description_en: str = ""


def parse_skin_tables():
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
        char_name = zh_name_to_en(cn_skin_name_to_char_name[name_cn])
        add_skin(char_name, skin_id, quality, name_cn, v['Desc']['SourceString'])
    return skins


def upload_skins(char_name: str, skin_list: list[SkinInfo]) -> list[SkinInfo]:
    @dataclass
    class Skin:
        source: FilePage
        target: FilePage
        skin: SkinInfo

    name_zh = en_name_to_zh[char_name]
    skins = [Skin(FilePage(bwiki(), f"File:{name_zh}时装-{skin.name_cn}.png"),
                  FilePage(s, f"File:{char_name} Skin {skin.name_en}.png"),
                  skin) for skin in skin_list]

    existing_source = set(p.title()
                          for p in PreloadingGenerator(skin.source for skin in skins)
                          if p.exists())
    existing_target = set(p.title()
                          for p in PreloadingGenerator(skin.target for skin in skins)
                          if p.exists())

    skin_list: list[SkinInfo] = []
    for skin in skins:
        if skin.target.title() not in existing_target:
            if skin.source.title() not in existing_source:
                continue
            upload_file(skin.source.get_file_url(), skin.target,
                        text=f"Taken from [https://wiki.biligame.com/klbq/"
                             f"{skin.source.title(with_ns=True, underscore=True)} bwiki], "
                             f"this image is licensed under CC BY-NC-SA 4.0."
                             f"[[Category:Skin screenshots]]",
                        summary="upload file from bwiki")
        skin_list.append(skin.skin)
    return skin_list


def localize_skins(skin_list):
    i18n_skin = get_game_json()['RoleSkin']
    i18n_store = get_game_json()['Goods']
    for skin in skin_list:
        descriptions = []
        name_en = None
        for skin_id in skin.id:
            k1 = f'{skin_id}_NameCn'
            k2 = f'{skin_id}_Name'
            if k1 in i18n_skin:
                name_en = i18n_skin[k1]
                description = i18n_skin[f'{skin_id}_Description']
                descriptions.append(description)
            if k2 in i18n_store:
                name_en = i18n_store[k2]
                description = i18n_store.get(f'{skin_id}_Desc', "")
                descriptions.append(description)
        if name_en is None:
            name_en = skin.name_cn
            descriptions = [skin.description_cn]
        skin.name_en = name_en
        skin.description_en = reduce(lambda x, y: x if len(x) > len(y) else y, descriptions, "")


def make_skin_template(t: wtp.Template, char_name: str, skin_list: list[SkinInfo]) -> None:
    skin_list.sort(key=lambda x: x.quality if x.quality != 0 else 100, reverse=True)
    localize_skins(skin_list)
    skin_list: list[SkinInfo] = upload_skins(char_name, skin_list)

    skin_counter = 1

    def add_arg(name, value):
        if (t.has_arg(name) and value.strip() == "") or value.strip() == "!NoTextFound!":
            return
        t.set_arg(name, value + "\n")

    for skin in skin_list:
        name_en = skin.name_en
        description = skin.description_en
        add_arg(f"Name{skin_counter}", name_en)
        add_arg(f"Quality{skin_counter}", str(skin.quality))
        add_arg(f"Description{skin_counter}", description)
        skin_counter += 1


def generate_skins():
    skins = parse_skin_tables()

    for char_name, skin_list in skins.items():
        if char_name not in en_name_to_zh:
            print("Skipping character " + char_name)
            continue

        p = Page(s, char_name)
        parsed = wtp.parse(p.text)
        for template in parsed.templates:
            if template.name.strip() == "CharacterSkins":
                t = template
                break
        else:
            print("Template CharacterSkins not found on " + char_name)
            continue

        make_skin_template(t, char_name, skin_list)

        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate skins", minor=True)
    print("Skins done")


if __name__ == '__main__':
    generate_skins()

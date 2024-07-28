import re
from dataclasses import dataclass

import wikitextparser as wtp
from pywikibot import Page, FilePage

from utils import get_table, get_game_json, zh_name_to_en, s, load_json, get_char_by_id, get_cn_wiki_skins, \
    en_name_to_zh, bwiki


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


def generate_skins():
    @dataclass
    class SkinInfo:
        id: int
        quality: int
        name_cn: str

    skins_table = load_json("json/CSV/RoleSkin.json")[0]['Rows']
    store_skins_table = load_json("json/CSV/Goods.json")[0]['Rows']
    i18n_skin = get_game_json()['RoleSkin']
    i18n_store = get_game_json()['Goods']
    skins: dict[str, list[SkinInfo]] = {}

    def add_skin(char_name, skin_id, quality, name_cn):
        lst = skins.get(char_name, [])
        # avoid dups
        if any(s.name_cn == name_cn for s in lst):
            return
        lst.append(SkinInfo(skin_id, quality, name_cn))
        skins[char_name] = lst

    for k, v in skins_table.items():
        skin_id = k
        name_cn = v['NameCn']['SourceString']
        quality = v['Quality']
        char_name = get_char_by_id(v['RoleId'])
        if char_name is None:
            continue
        add_skin(char_name, skin_id, quality, name_cn)
    cn_skin_name_to_char_name = get_cn_wiki_skins()
    for k, v in store_skins_table.items():
        if v['ItemType'] != 8:
            continue
        skin_id = v['Id']
        name_cn = v['Name']['SourceString']
        quality = v['Quality']
        if name_cn not in cn_skin_name_to_char_name:
            continue
        char_name = zh_name_to_en(cn_skin_name_to_char_name[name_cn])
        add_skin(char_name, skin_id, quality, name_cn)

    for char_name, skin_list in skins.items():
        for skin in skin_list:
            if skin.quality == 0:
                skin.quality = 10
        skin_list.sort(key=lambda x: x.quality, reverse=True)

        p = Page(s, char_name)
        parsed = wtp.parse(p.text)
        t = None
        for template in parsed.templates:
            if template.name.strip() == "CharacterSkins":
                t = template
                break
        else:
            print("Template CharacterSkins not found on " + char_name)
            continue

        skin_counter = 1

        def add_arg(name, value):
            if (t.has_arg(name) and value.strip() == "") or value.strip() == "!NoTextFound!":
                return
            t.set_arg(name, value + "\n")

        for skin in skin_list:
            k1 = f'{skin.id}_NameCn'
            k2 = f'{skin.id}_Name'
            if k1 in i18n_skin:
                name_en = i18n_skin[k1]
                description = i18n_skin[f'{skin.id}_Description']
            elif k2 in i18n_store:
                name_en = i18n_store[k2]
                description = i18n_store.get(f'{skin.id}_Desc', "")
            else:
                continue
            if char_name not in en_name_to_zh:
                continue
            name_zh = en_name_to_zh[char_name]
            target_file = FilePage(s, f"{char_name} Skin {name_en}.png")
            if not target_file.exists():
                source_file = FilePage(bwiki(), f"{name_zh}时装-{skin.name_cn}.png")
                if not source_file.exists():
                    continue
                s.upload(target_file, source_url=source_file.get_file_url(), comment="upload file from bwiki",
                         text=f"Taken from [https://wiki.biligame.com/klbq/{source_file.title(with_ns=True, underscore=True)} bwiki], "
                              f"this image is licensed under CC BY-NC-SA 4.0."
                              f"[[Category:Skin screenshots]]")

            add_arg(f"Name{skin_counter}", name_en)
            add_arg(f"Quality{skin_counter}", str(skin.quality))
            add_arg(f"Description{skin_counter}", description)
            skin_counter += 1

        if p.text.strip() == str(parsed).strip():
            continue
        p.text = str(parsed)
        p.save(summary="generate skins", minor=False)
    print("Skins done")

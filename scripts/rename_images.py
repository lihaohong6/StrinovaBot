from pathlib import Path
from shutil import copyfile

from pywikibot import Page

from char_info.gallery import parse_skin_tables, localize_skins, parse_emotes
from utils.asset_utils import resource_root
from utils.lang import set_language
from utils.wiki_utils import s


def rename_outfits():
    set_language('en')

    skins = parse_skin_tables()
    for char_name, skin_list in skins.items():
        localize_skins(skin_list)
        for skin in skin_list:
            assert skin.name_cn != ""
            original = skin.get_mh_portrait_title(char_name)
            skin.name_en = skin.name_cn
            renamed = skin.get_mh_portrait_title(char_name)
            if original != renamed:
                original = Page(s, original)
                renamed = Page(s, renamed)
                if original.exists() and not renamed.exists():
                    original.move(renamed.title(with_ns=True), 'batch rename files')


def rename_emotes():
    out_path = Path("files/emotes")
    out_path.mkdir(parents=True, exist_ok=True)
    emotes = parse_emotes()
    for char_name, emote_list in emotes.items():
        for emote in emote_list:
            local_path = resource_root / emote.get_local_path
            if local_path.exists() and 'en' in emote.name:
                name_en = emote.name['en']
                name_en = "".join(filter(lambda c: c.isalnum() or c == " " or c == "-", name_en))
                copyfile(local_path, out_path / f"{name_en}.png")



if __name__ == '__main__':
    rename_emotes()

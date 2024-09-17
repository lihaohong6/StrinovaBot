from pywikibot import Page

from char_info.gallery import parse_skin_tables, localize_skins
from global_config import char_id_mapper
from utils.lang import set_language
from utils.wiki_utils import s

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


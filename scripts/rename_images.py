from char_info.gallery import parse_skin_tables, localize_skins
from utils.lang import set_language

set_language('en')

skins = parse_skin_tables()
for char_id, skin_list in skins.items():
    localize_skins(skin_list)
    for s in skin_list:
        print(f"{s.name_en} -> {s.name_cn}")


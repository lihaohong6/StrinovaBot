from char_info.gallery import parse_skin_tables, SkinInfo
from utils.json_utils import get_table_global

def get_shop_daily_picks() -> list[SkinInfo]:
    skin_table = get_table_global("RoleSkin")
    skins: dict[int, SkinInfo] = {}
    result: list[SkinInfo] = []
    for _, skin_list in parse_skin_tables().items():
        for skin in skin_list:
            skins[skin.id] = skin
    for k, v in skin_table.items():
        param = v.get("GainParam2", {}).get("Key", None)
        if param is None:
            continue
        if param != "DailyShop":
            continue
        result.append(skins[k])
    return result

def main():
    skins = get_shop_daily_picks()
    skins.sort(key=lambda s: s.quality, reverse=True)
    for skin in skins:
        print("{{Item|" + skin.name.get("en", "")  + "}}", end="\n\n")


if __name__ == '__main__':
    main()
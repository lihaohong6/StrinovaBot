import re
from dataclasses import dataclass, field

import wikitextparser as wtp
from pywikibot import Page, FilePage
from pywikibot.pagegenerators import PreloadingGenerator

from global_config import characters_with_dorms
from page_generator.badges import get_all_badges, Badge
from page_generator.decal import get_all_decals, Decal
from page_generator.items import parse_items, Item
from utils.asset_utils import resource_root
from utils.general_utils import get_table, get_char_by_id, make_tab_group, get_char_pages, save_json_page
from utils.json_utils import get_game_json, get_all_game_json
from utils.lang import LanguageVariants, get_language, CHINESE, available_languages
from utils.lang_utils import get_multilanguage_dict, StringConverters, compose
from utils.upload_utils import upload_item_icons, UploadRequest, process_uploads
from utils.wiki_utils import s


@dataclass
class Gift:
    id: int
    name: dict[str, str] = field(default_factory=dict)
    quality: int | str = -1
    file: str = ""
    description: dict[str, str] = field(default_factory=dict)
    characters: dict[str, tuple[int, int]] = field(default_factory=dict)
    best_characters: list[str] = field(default_factory=list)


def get_gifts() -> dict[int, Gift]:
    gift_json = get_table("RoleFavorabilityGiftPresent")
    gift_dict: dict[int, Gift] = {}
    for gift in gift_json.values():
        gift_id = gift['Gift']
        char_id = gift['RoleId']
        char_name = get_char_by_id(char_id)
        if char_name not in characters_with_dorms:
            continue
        favorability = gift['Favorability']
        like_level = gift['LikeLevel']
        if gift_id not in gift_dict:
            gift_dict[gift_id] = Gift(gift_id)
        gift_dict[gift_id].characters[char_name] = (favorability, like_level)
    return gift_dict


def generate_gifts():
    gift_dict: dict[int, Gift] = get_gifts()
    item_table = get_table("Item")
    gifts = list(gift_dict.values())
    i18n = get_all_game_json("Item")
    for gift in gifts:
        g = item_table[gift.id]
        gift.file = re.search(r"_(\d+)$", g['IconItem']['AssetPathName']).group(1)
        gift.quality = g['Quality']
        name_cn = g['Name']['SourceString']
        gift.name = get_multilanguage_dict(i18n, f"{gift.id}_Name", extra=name_cn)
        desc_cn = g['Desc']['SourceString']
        gift.description = get_multilanguage_dict(i18n, f"{gift.id}_Desc", extra=desc_cn)

    gifts = [g
             for g in sorted(gifts, key=lambda t: t.quality, reverse=True)
             if g.file != "10001"]
    for gift in gifts:
        max_favorability = max(map(lambda t: t[0], gift.characters.values()))
        gift.best_characters = list(
            map(lambda t: t[0],
                filter(lambda t: t[1][0] == max_favorability and t[0] in characters_with_dorms,
                       gift.characters.items())))
        if len(gift.best_characters) == len(characters_with_dorms):
            gift.best_characters = ["Everyone"]

    upload_item_icons([g.file for g in gifts], "[[Category:Gift icons]]", "batch upload gift icons")

    # quality_table = get_quality_table()
    # for g in gifts.values():
    #     g.quality = quality_table[int(g.quality)]

    p = Page(s, "Module:CharacterGifts/data2.json")
    save_json_page(p, gifts)

    for lang in LanguageVariants:
        all_recipients = PreloadingGenerator(Page(s, char + lang.value.page_suffix) for char in characters_with_dorms)
        for p in all_recipients:
            char_name = p.title().split("/")[0]
            parsed = wtp.parse(p.text)
            for t in parsed.templates:
                if t.name.strip() == "CharacterGifts":
                    break
            else:
                print("Gift template not found on " + p.title())
                continue
            if t.has_arg("1"):
                continue
            t.set_arg("1", char_name, positional=True)
            p.text = str(parsed)
            p.save("enable character gift")


@dataclass
class PledgeItem:
    id: int
    file: str
    name: dict[str, str]
    description: dict[str, str]
    story: dict[str, str]


def generate_bond_items():
    i18n = get_all_game_json("PledgeItem")
    items_table = get_table("PledgeItem")
    items: dict[str, list[PledgeItem]] = {}
    upload_lst: list[int | str] = []
    for k, v in items_table.items():
        role_id = v['OwnerRoleId']
        char_name = get_char_by_id(role_id)
        try:
            name = get_multilanguage_dict(i18n, f"{k}_Name", extra=v['Name']['SourceString'])
            desc = get_multilanguage_dict(i18n, f"{k}_Desc", extra=v['Desc']['SourceString'])
            story = get_multilanguage_dict(i18n, f"{k}_ItemStory", extra=v['ItemStory']['SourceString'])
            item = PledgeItem(v['Id'], v['ItemIcon']['AssetPathName'].split("_")[-1],
                              name,
                              desc,
                              story)
            if char_name not in items:
                items[char_name] = []
            items[char_name].append(item)
            upload_lst.append(item.file)
        except KeyError:
            continue
    upload_item_icons(upload_lst, "[[Category:Bond item icons]]", "batch upload bond item icons")
    save_json_page("Module:BondItems/data.json", items, summary="update bond items")


def generate_friendship_gifts():
    @dataclass
    class FriendshipReward:
        name: dict[str, str]
        quality: int
        quantity: int
        image: str
    table = get_table("RoleFavorabilityEvent")
    friendship_gifts: dict[int, dict[int, list[FriendshipReward]]] = {}
    items = parse_items()
    badges = get_all_badges()
    decals = get_all_decals()
    upload_requests: list[UploadRequest] = []
    i18n = get_all_game_json("RoleFavorabilityEvent")
    for v in table.values():
        role_id = v['RoleId']
        level = v['FavoLevel']
        if role_id not in friendship_gifts:
            friendship_gifts[role_id] = {}
        if level not in friendship_gifts[role_id]:
            friendship_gifts[role_id][level] = []
        emoticon_path = v["EmoticonsPicture"].get("AssetPathName", None)
        reward: FriendshipReward
        if emoticon_path is None or emoticon_path == "None":
            prizes = v['FavoPrize']
            assert len(prizes) == 1
            prize: dict = prizes[0]
            item_id = prize['ItemId']
            item_amount = prize['ItemAmount']
            item: Item | Badge | Decal
            if item_id in items:
                item = items[item_id]
            elif item_id in badges:
                item = badges[item_id]
            elif item_id in decals:
                item = decals[item_id]
            else:
                raise RuntimeError(f"Item {item_id} not found")
            reward = FriendshipReward(item.name, item.quality, item_amount, item.file)
        else:
            source_name = emoticon_path.split(".")[-1]
            source = resource_root / "Emote" / "ApartmentEmotePack" / (source_name + ".png")
            file_name = f"File:Emoticon pack {source_name.split('_')[-1]}"
            upload_requests.append(UploadRequest(source, FilePage(s, file_name), '[[Category:Emoticon pack icons]]'))

            emoticon_dict = v['FavoPrizeName']
            reward = FriendshipReward({}, 1, 1, file_name)
            reward.name = get_multilanguage_dict(i18n, emoticon_dict['Key'])
            reward.name[CHINESE.code] = emoticon_dict['SourceString']
        friendship_gifts[role_id][level].append(reward)

    process_uploads(upload_requests)
    p = Page(s, "Module:FriendshipReward/data.json")
    save_json_page(p, friendship_gifts)


if __name__ == "__main__":
    generate_gifts()
    generate_bond_items()
    # Not ready yet
    # generate_friendship_gifts()

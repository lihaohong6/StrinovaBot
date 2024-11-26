import re
from dataclasses import dataclass, field
from functools import cache

import wikitextparser as wtp
from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from global_config import characters_with_dorms
from page_generator.items import get_all_items
from utils.general_utils import get_table, get_char_by_id, save_json_page, \
    get_table_global
from utils.json_utils import get_all_game_json
from utils.lang import LanguageVariants
from utils.lang_utils import get_multilanguage_dict
from utils.upload_utils import upload_item_icons
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


@cache
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


@dataclass
class FriendshipReward:
    name: dict[str, str]
    quality: int
    quantity: int
    image: str


@dataclass
class FriendshipRewardGroup:
    rewards: list[FriendshipReward] = field(default_factory=list)
    condition: dict[str, str] = field(default_factory=dict)


def parse_friendship_rewards():
    friendship_gifts: dict[int, dict[int, list[FriendshipRewardGroup]]] = {}
    items = get_all_items()
    i18n = get_all_game_json("RoleFavorabilityMission")

    def make_rewards(role_id: int, level: int, prize_list: list[dict], cond: dict[str, str] = None):
        if role_id not in friendship_gifts:
            friendship_gifts[role_id] = {}
        if level not in friendship_gifts[role_id]:
            friendship_gifts[role_id][level] = []
        result = []
        for prize in prize_list:
            item_id = prize['ItemId']
            item_amount = prize['ItemAmount']
            item = items.get(item_id)
            assert item is not None, f"Item with id {item_id} not found"
            result.append(FriendshipReward(item.name, item.quality, item_amount, item.icon))
        friendship_gifts[role_id][level].append(FriendshipRewardGroup(result, cond))

    table1 = get_table_global("RoleFavorabilityEvent")

    for v in table1.values():
        prizes = v['FavoPrize']
        make_rewards(v['RoleId'], v['FavoLevel'], prizes)

    table2 = get_table_global("RoleFavorabilityMission")

    for v in table2.values():
        prizes = v['Prize']
        desc = get_multilanguage_dict(i18n, v["Desc"]["Key"], extra=v["Desc"]["SourceString"])
        make_rewards(v['RoleId'], v['RoleLevel'], prizes, desc)

    return friendship_gifts


def generate_friendship_gifts():
    gifts = parse_friendship_rewards()
    # upload_requests: list[UploadRequest] = []
    # for gift_dict in gifts.values():
    #     for level, gift in gift_dict.items():
    #         source = resource_root / "Emote" / "ApartmentEmotePack" / (source_name + ".png")
    #         upload_requests.append(UploadRequest(source, FilePage(s, file_name), '[[Category:Emoticon pack icons]]'))
    # process_uploads(upload_requests)
    save_json_page("Module:FriendshipReward/data.json", gifts)


if __name__ == "__main__":
    generate_gifts()
    generate_bond_items()
    generate_friendship_gifts()

import dataclasses
import json
import re
from dataclasses import dataclass, field

import wikitextparser as wtp
from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from global_config import characters_with_dorms, char_id_mapper
from uploader import upload_item_icons, upload_item
from utils import get_game_json, get_table, get_char_by_id, make_tab_group
from wiki_utils import s


@dataclass
class Gift:
    id: int
    name: str = ""
    quality: int | str = -1
    file: str = ""
    description: str = ""
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

    i18n = get_game_json()['Item']
    gift_dict: dict[int, Gift] = get_gifts()
    item_table = get_table("Item")
    gifts = list(gift_dict.values())
    for gift in gifts:
        g = item_table[gift.id]
        gift.file = re.search(r"_(\d+)$", g['IconItem']['AssetPathName']).group(1)
        gift.quality = g['Quality']
        gift.name = g['Name']['SourceString']
        gift.description = g['Desc']['SourceString']
        key = f"{gift.id}_Name"
        if key in i18n:
            gift.name = i18n[key]
            gift.description = i18n[f"{gift.id}_Desc"]

    gifts = [g
             for g in sorted(gifts, key=lambda t: t.quality, reverse=True)
             if g.file != "10001"]
    for gift in gifts:
        max_favorability = max(map(lambda t: t[0], gift.characters.values()))
        gift.best_characters = list(
            map(lambda t: t[0],
                filter(lambda t: t[1][0] == max_favorability and t[0] in characters_with_dorms, gift.characters.items())))
        if len(gift.best_characters) == len(characters_with_dorms):
            gift.best_characters = ["Everyone"]

    upload_item_icons([g.file for g in gifts], cat="Gift icons")

    # quality_table = get_quality_table()
    # for g in gifts.values():
    #     g.quality = quality_table[int(g.quality)]

    class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            return super().default(o)

    p = Page(s, "Module:CharacterGifts/data.json")
    text = json.dumps(gifts, cls=EnhancedJSONEncoder)
    if p.text.strip() == text:
        return
    p.text = text
    p.save(summary="update gift data")

    all_recipients = PreloadingGenerator(Page(s, char) for char in characters_with_dorms)
    for p in all_recipients:
        char_name = p.title()
        parsed = wtp.parse(p.text)
        for t in parsed.templates:
            if t.name.strip() == "CharacterGifts":
                break
        else:
            raise RuntimeError("Template not found on " + char_name)
        if t.has_arg("1"):
            continue
        t.set_arg("1", char_name, positional=True)
        p.text = str(parsed)
        p.save("enable character gift")


def generate_bond_items():
    @dataclass
    class Item:
        id: int
        file: str
        name: str
        description: str
        story: str

        def to_template(self):
            return f"{{{{ BondItem | file={self.file} " \
                   f"| description={self.description} | story={self.story} }}}}"

    i18n = get_game_json()['PledgeItem']
    items_table = get_table("PledgeItem")
    id_to_items: dict[int, list[Item]] = {}
    for k, v in items_table.items():
        role_id = v['OwnerRoleId']
        try:
            item = Item(v['Id'], v['ItemIcon']['AssetPathName'].split("_")[-1],
                        i18n[f"{k}_Name"], i18n[f"{k}_Desc"], i18n[f"{k}_ItemStory"])
            if "NoTextFound" in item.name:
                continue
            if role_id not in id_to_items:
                id_to_items[role_id] = []
            id_to_items[role_id].append(item)
        except KeyError:
            continue
    for role_id, items in id_to_items.items():
        char_name = char_id_mapper[role_id]
        p = Page(s, char_name)
        parsed = wtp.parse(p.text)
        for t in parsed.templates:
            if t.name.strip() == "BondItems":
                break
        else:
            raise RuntimeError("Template not found on " + char_name)
        tabs = wtp.Template("{{Tab/tabs}}")
        contents = wtp.Template("{{Tab/content}}")
        group_name = make_tab_group(f"BondItems{char_name}")
        tabs.set_arg("group", group_name)
        contents.set_arg("group", group_name)
        for item in items:
            tabs.set_arg("", item.name, positional=True)
            contents.set_arg("", item.to_template() + "\n", positional=True)
            upload_item(item.file, cat="Bond item icons")
        t.set_arg("1", "\n" + str(tabs) + "\n" + str(contents) + "\n", positional=True)
        if p.text.strip() != str(parsed).strip():
            p.text = str(parsed)
            p.save("generate bond items")


if __name__ == "__main__":
    # generate_gifts()
    generate_bond_items()

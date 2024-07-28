import dataclasses
import json
import re
from dataclasses import dataclass, field

import wikitextparser as wtp
from pywikibot import Page

from utils import get_game_json, get_table, get_char_by_id, s


def generate_gifts():
    @dataclass
    class Gift:
        id: int
        name: str = ""
        quality: int | str = -1
        file: str = ""
        description: str = ""
        characters: dict[str, tuple[int, int]] = field(default_factory=dict)
        best_characters: list[str] = field(default_factory=list)

    i18n = get_game_json()['Item']
    gift_json = get_table("RoleFavorabilityGiftPresent")
    gift_dict: dict[int, Gift] = {}
    for gift in gift_json.values():
        gift_id = gift['Gift']
        char_id = gift['RoleId']
        char_name = get_char_by_id(char_id)
        favorability = gift['Favorability']
        like_level = gift['LikeLevel']
        if gift_id not in gift_dict:
            gift_dict[gift_id] = Gift(gift_id)
        gift_dict[gift_id].characters[char_name] = (favorability, like_level)
    item_table = get_table("Item")
    gifts = list(gift_dict.values())
    for gift in gifts:
        g = item_table[gift.id]
        gift.file = re.search(r"_(\d+)$", g['IconItem']['AssetPathName']).group(1)
        gift.quality = g['Quality']
        gift.name = i18n[f"{gift.id}_Name"]
        gift.description = i18n[f"{gift.id}_Desc"]

    gifts = [g
             for g in sorted(gifts, key=lambda t: t.quality, reverse=True)
             if g.file != "10001"]
    all_recipients = set(gifts[0].characters.keys())
    for g in gifts:
        all_recipients.intersection_update(set(g.characters.keys()))
        # upload_item(g.file)
    for gift in gifts:
        max_favorability = max(map(lambda t: t[0], gift.characters.values()))
        gift.best_characters = list(
            map(lambda t: t[0],
                filter(lambda t: t[1][0] == max_favorability and t[0] in all_recipients, gift.characters.items())))
        if len(gift.best_characters) == len(all_recipients):
            gift.best_characters = ["Everyone"]

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

    for char_name in all_recipients:
        p = Page(s, char_name)
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

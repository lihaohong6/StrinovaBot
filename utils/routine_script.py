import json

from pywikibot import Page

from global_config import char_id_mapper
from utils.general_utils import get_quality_table
from utils.upload_utils import upload_item_icons
from utils.wiki_utils import s


def upload_voice_icons():
    upload_item_icons([f"22{char_id}001" for char_id in char_id_mapper.keys()])


def generate_quality_table():
    quality_table = get_quality_table()
    text = json.dumps(quality_table)
    p = Page(s, "Module:CharacterGifts/rarity.json")
    if p.text.strip() == text:
        return
    p.text = text
    p.save(summary="update rarity data")
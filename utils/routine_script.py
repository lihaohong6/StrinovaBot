from global_config import char_id_mapper
from utils.upload_utils import upload_item_icons


def upload_voice_icons():
    upload_item_icons([f"22{char_id}001" for char_id in char_id_mapper.keys()])

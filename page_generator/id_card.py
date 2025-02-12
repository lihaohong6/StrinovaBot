import enum
from dataclasses import dataclass, field
from functools import cache

from utils.asset_utils import resource_root, global_resources_root
from utils.general_utils import get_table, get_table_global, save_json_page
from utils.json_utils import get_all_game_json
from utils.lang_utils import get_multilanguage_dict, compose, StringConverters
from utils.upload_utils import UploadRequest, process_uploads


class IdCardType(enum.Enum):
    FRAME = "Frame"
    AVATAR = "Avatar"
    UNKNOWN = ""


@dataclass
class IdCard:
    id: int
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    unlock: dict[str, str] = field(default_factory=dict)
    quality: int = -1
    type: IdCardType = IdCardType.UNKNOWN

    @property
    def icon(self):
        return f"File:Item Icon {self.id}.png"

    @property
    def full_file(self):
        return f"File:IdCard {self.id}.png"


@cache
def get_all_id_cards(use_cn: bool = True) -> dict[int, IdCard]:
    id_card_json = get_table("IdCard") if use_cn else get_table_global("IdCard")
    i18n = get_all_game_json("IdCard")
    id_cards: dict[int, IdCard] = {}
    for id_card_id, v in id_card_json.items():
        id_card_type = IdCardType.AVATAR if "::Avatar" in v['Type'] else IdCardType.FRAME
        try:
            id_card = IdCard(id_card_id)
            id_card.type = id_card_type
            id_card.name = get_multilanguage_dict(i18n, f"{id_card.id}_Name", extra=v['Name']['SourceString'])
            id_card.description = get_multilanguage_dict(
                i18n, f"{id_card.id}_Desc", extra=v['Desc']['SourceString'],
                converter=compose(StringConverters.basic_converter, StringConverters.newline_to_br))
            id_card.quality = v['Quality']
            id_card.unlock = get_multilanguage_dict(
                i18n, f"{id_card.id}_GainParam2", extra=v['GainParam2'].get('SourceString', None),
                converter=compose(StringConverters.basic_converter, StringConverters.all_caps_remove))
            id_cards[id_card_id] = id_card
        except Exception:
            pass
    return id_cards


def upload_all_id_cards(id_cards: dict[int, IdCard], use_cn: bool = True):
    if use_cn:
        root = resource_root / "IdCard"
    else:
        root = global_resources_root / "IdCard"
    avatar_root = root / "Appearance"
    frame_root = root / "Background"
    requests: list[UploadRequest] = []
    for d in id_cards.values():

        if d.type == IdCardType.AVATAR:
            cur_root = avatar_root
        elif d.type == IdCardType.FRAME:
            cur_root = frame_root
        else:
            raise RuntimeError(f"Unknown type {d.type}")
        source_icon = cur_root / f"T_Dynamic_IdCard_{d.id}_icon.png"
        suffix = "" if d.type == IdCardType.AVATAR else "_L"
        source_full = cur_root / f"T_Dynamic_IdCard_{d.id}{suffix}.png"

        if not source_icon.exists() or not source_full.exists():
            continue
        requests.append(UploadRequest(source_icon,
                                      d.icon,
                                      '[[Category:Item icons]]'))
        requests.append(UploadRequest(source_full,
                                      d.full_file,
                                      '[[Category:IdCard images]]'))
    process_uploads(requests)


def make_id_cards():
    id_cards = get_all_id_cards()
    upload_all_id_cards(id_cards)
    id_cards = get_all_id_cards(use_cn=False)
    upload_all_id_cards(id_cards, use_cn=False)
    avatars = dict((k, v) for k, v in id_cards.items() if v.type == IdCardType.AVATAR)
    save_json_page("Module:IdCard/data.json", avatars)
    frames = dict((k, v) for k, v in id_cards.items() if v.type == IdCardType.FRAME)
    save_json_page("Module:IdCard/frames.json", frames)


def main():
    make_id_cards()


if __name__ == '__main__':
    main()
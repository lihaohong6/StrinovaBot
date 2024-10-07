from dataclasses import dataclass, field
from pathlib import Path

from pywikibot import FilePage

from utils.asset_utils import resource_root
from utils.general_utils import get_table
from utils.json_utils import get_all_game_json
from utils.lang import CHINESE
from utils.lang_utils import get_multilanguage_dict
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s


@dataclass
class IdCard:
    id: int
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    quality: int = -1

    @property
    def icon_file(self):
        return f"File:Item Icon {self.id}.png"

    @property
    def full_file(self):
        return f"File:IdCard {self.id}.png"


def localize_id_cards(id_cards: list[IdCard]):
    table_name = "IdCard"
    i18n = get_all_game_json(table_name)
    for id_card in id_cards:
        id_card.name |= get_multilanguage_dict(i18n, f"{id_card.id}_Name")
        id_card.description |= get_multilanguage_dict(i18n, f"{id_card.id}_Desc")


def get_all_id_cards() -> dict[int, IdCard]:
    id_card_json = get_table("IdCard")
    id_cards: dict[int, IdCard] = {}
    for id_card_id, v in id_card_json.items():
        if "::Avatar" not in v['Type']:
            continue
        try:
            id_card = IdCard(id_card_id)
            id_card.name[CHINESE.code] = v['Name']['SourceString']
            id_card.description[CHINESE.code] = v['Desc']['SourceString']
            id_card.quality = v['Quality']
            id_cards[id_card_id] = id_card
        except Exception:
            pass
    localize_id_cards(list(id_cards.values()))
    return id_cards


def upload_all_id_cards():
    root = resource_root / "IdCard" / "Appearance"
    id_cards = get_all_id_cards()
    requests: list[UploadRequest] = []
    for d in id_cards.values():
        source_icon = root / f"T_Dynamic_IdCard_{d.id}_icon.png"
        source_full = root / f"T_Dynamic_IdCard_{d.id}.png"
        if not source_full.exists() or not source_icon.exists():
            continue
        requests.append(UploadRequest(source_icon,
                                      d.icon_file,
                                      '[[Category:Item icons]]'))
        requests.append(UploadRequest(source_full,
                                      d.full_file,
                                      '[[Category:IdCard images]]'))
    process_uploads(requests)


def main():
    upload_all_id_cards()



if __name__ == '__main__':
    main()
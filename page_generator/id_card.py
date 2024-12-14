from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from pywikibot import FilePage

from utils.asset_utils import resource_root
from utils.general_utils import get_table, get_table_global, save_json_page
from utils.json_utils import get_all_game_json
from utils.lang import CHINESE
from utils.lang_utils import get_multilanguage_dict, compose, StringConverters
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s


@dataclass
class IdCard:
    id: int
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    unlock: dict[str, str] = field(default_factory=dict)
    quality: int = -1

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
        if "::Avatar" not in v['Type']:
            continue
        try:
            id_card = IdCard(id_card_id)
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


def upload_all_id_cards(id_cards: dict[int, IdCard]):
    root = resource_root / "IdCard" / "Appearance"
    requests: list[UploadRequest] = []
    for d in id_cards.values():
        source_icon = root / f"T_Dynamic_IdCard_{d.id}_icon.png"
        source_full = root / f"T_Dynamic_IdCard_{d.id}.png"
        if not source_full.exists() or not source_icon.exists():
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
    save_json_page("Module:IdCard/data.json", id_cards)


def main():
    make_id_cards()


if __name__ == '__main__':
    main()
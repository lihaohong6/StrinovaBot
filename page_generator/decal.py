from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from pywikibot import FilePage

from utils.asset_utils import resource_root, global_resources_root
from utils.general_utils import get_table, save_json_page, get_table_global
from utils.json_utils import get_all_game_json
from utils.lang import CHINESE
from utils.lang_utils import get_multilanguage_dict, StringConverters, compose
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s


@dataclass
class Decal:
    id: int
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    quality: int = -1

    @property
    def file(self):
        return f"File:Decal {self.id}.png"

    @property
    def icon(self):
        return self.file


@cache
def get_all_decals(use_cn: bool = True) -> dict[int, Decal]:
    if use_cn:
        decal_json = get_table("Decal")
    else:
        decal_json = get_table_global("Decal")
    decals: dict[int, Decal] = {}
    i18n = get_all_game_json("Decal")
    for decal_id, v in decal_json.items():
        decal = Decal(decal_id)
        decals[decal_id] = decal
        decal.name = get_multilanguage_dict(i18n, f"{decal.id}_Name",
                                            extra=v['Name']['SourceString'])
        decal.description = get_multilanguage_dict(
            i18n, f"{decal.id}_Desc",
            converter=compose(StringConverters.basic_converter,
                              StringConverters.newline_to_br),
            extra=v['Desc']['SourceString'])
        decal.quality = v['Quality']
    return decals


def upload_all_decals(decals: dict[int, Decal]):
    requests: list[UploadRequest] = []
    for d in decals.values():
        source = resource_root / "Decal" / "PaintingListDecal" / f"T_Dynamic_Decal_{d.id}.png"
        if not source.exists():
            source = global_resources_root / "Decal" / "PaintingListDecal" / f"T_Dynamic_Decal_{d.id}.png"
            if not source.exists():
                continue
        requests.append(UploadRequest(source,
                                      FilePage(s, d.file),
                                      '[[Category:Decal icons]]'))
    process_uploads(requests)


def make_all_decals():
    en_decals = get_all_decals(use_cn=False)
    upload_all_decals(en_decals)
    save_json_page("Module:Decal/data.json", en_decals)


def main():
    make_all_decals()


if __name__ == '__main__':
    main()

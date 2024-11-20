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


def localize_decals(decals: list[Decal]):
    i18n = get_all_game_json("Decal")
    for decal in decals:
        decal.name |= get_multilanguage_dict(i18n, f"{decal.id}_Name")
        decal.description |= get_multilanguage_dict(i18n, f"{decal.id}_Desc")


def get_all_decals() -> dict[int, Decal]:
    decal_json = get_table("Decal")
    decals: dict[int, Decal] = {}
    for decal_id, v in decal_json.items():
        decal = Decal(decal_id)
        decals[decal_id] = decal
        decal.name[CHINESE.code] = v['Name']['SourceString']
        decal.description[CHINESE.code] = v['Desc']['SourceString']
        decal.quality = v['Quality']
    localize_decals(list(decals.values()))
    return decals


def upload_all_decals():
    decals = get_all_decals()
    requests: list[UploadRequest] = []
    for d in decals.values():
        source = resource_root / "Decal" / "PaintingListDecal" / f"T_Dynamic_Decal_{d.id}.png"
        if not source.exists():
            continue
        requests.append(UploadRequest(source,
                                      FilePage(s, d.file),
                                      '[[Category:Decal icons]]'))
    process_uploads(requests)


def main():
    upload_all_decals()



if __name__ == '__main__':
    main()
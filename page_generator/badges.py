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
class Badge:
    id: int
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    quality: int = -1
    type: int = -1
    gain: dict[str, str] = field(default_factory=dict)

    @property
    def file(self):
        return f"File:Achievement {self.id}.png"


def localize_badges(badges: list[Badge]):
    table_name = "Badge"
    i18n = get_all_game_json(table_name)
    for badge in badges:
        badge.name |= get_multilanguage_dict(i18n, f"{badge.id}_Name")
        badge.description |= get_multilanguage_dict(i18n, f"{badge.id}_Desc")
        badge.gain |= get_multilanguage_dict(i18n, f"{badge.id}_GainParam2")


def get_all_badges() -> dict[int, Badge]:
    badge_json = get_table("Badge")
    badges: dict[int, Badge] = {}
    for badge_id, v in badge_json.items():
        badge = Badge(badge_id)
        badges[badge_id] = badge
        badge.name[CHINESE.code] = v['Name']['SourceString']
        badge.description[CHINESE.code] = v['Desc']['SourceString']
        badge.gain[CHINESE.code] = v['GainParam2'].get('SourceString', "")
        badge.quality = v['Quality']
        badge.type = v['BadgeType']
    localize_badges(list(badges.values()))
    return badges


def upload_all_badges():
    raise RuntimeError("This shouldn't be necessary because all badges are covered by achievements")
    badges = get_all_badges()
    requests: list[UploadRequest] = []
    for b in badges.values():
        source = resource_root / "Achievement" / f"T_Dynamic_Achievement_{b.id}.png"
        if not source.exists():
            continue
        requests.append(UploadRequest(source,
                                      FilePage(s, b.file),
                                      '[[Category:Achievement icons]]'))
    process_uploads(requests)


def main():
    upload_all_badges()


if __name__ == '__main__':
    main()
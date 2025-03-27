from dataclasses import dataclass, field
from functools import cache

from pywikibot import FilePage

from utils.asset_utils import resource_root
from utils.json_utils import get_all_game_json, get_table
from utils.lang_utils import get_text
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

    @property
    def icon(self):
        return self.file


@cache
def get_all_badges() -> dict[int, Badge]:
    badge_json = get_table("Badge")
    i18n = get_all_game_json("Badge")
    badges: dict[int, Badge] = {}
    for badge_id, v in badge_json.items():
        badge = Badge(badge_id)
        badges[badge_id] = badge
        badge.name = get_text(i18n, v["Name"])
        badge.description = get_text(i18n, v["Desc"])
        badge.gain = get_text(i18n, v["GainParam2"])
        badge.quality = v['Quality']
        badge.type = v['BadgeType']
    return badges


def upload_all_badges():
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
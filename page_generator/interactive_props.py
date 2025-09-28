from dataclasses import dataclass, field
from functools import cache

from utils.json_utils import get_table, get_all_game_json
from utils.lang_utils import get_text
from utils.upload_utils import UploadRequest, process_uploads, upload_item_icons


@dataclass
class InteractiveProp:
    id: int
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    quality: int = 0

    @property
    def file(self):
        return f"File:Item Icon {self.id}.png"

    @property
    def icon(self):
        return self.file


@cache
def parse_interactive_props() -> list[InteractiveProp]:
    interactive_prop_json = get_table("InteractiveProps")
    i18n = get_all_game_json("InteractiveProps")
    result = []
    for prop, v in interactive_prop_json.items():
        prop = InteractiveProp(prop)
        prop.name = get_text(i18n, v["InteractivepropsName"])
        prop.description = get_text(i18n, v["Content"])
        result.append(prop)
    return result


def upload_interactive_props():
    props = parse_interactive_props()
    upload_item_icons([p.id for p in props],
                      text='[[Category:Interactive props]]',
                      summary='batch upload interactive props')


def process_interactive_props():
    upload_interactive_props()


def main():
    process_interactive_props()


if __name__ == '__main__':
    main()

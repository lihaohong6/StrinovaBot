from dataclasses import dataclass
from typing import Iterable

from pywikibot import Page
from pywikibot.data.api import PageGenerator

from utils.asset_utils import resource_root
from utils.general_utils import get_table, get_table_global
from utils.json_utils import get_all_game_json
from utils.lang import ENGLISH, get_language
from utils.lang_utils import get_multilanguage_dict
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s


@dataclass
class Map:
    id: int
    name: dict[str, str]
    description: dict[str, str]
    intro: str
    minimap: str

    @property
    def name_en(self):
        return self.name[ENGLISH.code]

    @property
    def intro_file(self):
        return f"File:Intro {self.name_en}.png"

    @property
    def minimap_file(self):
        return f"File:Minimap {self.name_en}.png"


def parse_maps():
    table = get_table_global("MapCfg")
    i18n = get_all_game_json("ST_MapCfg")
    result: dict[int, Map] = {}
    for map_id, v in table.items():
        name = get_multilanguage_dict(i18n, f"Name_{map_id}")
        description = get_multilanguage_dict(i18n, f"Desc_{map_id}")
        intro = v["IconMapIntro"]["AssetPathName"].split(".")[-1]
        minimap = v['Minimap2d']['AssetPathName'].split(".")[-1]
        if len(name) > 1:
            result[map_id] = Map(map_id, name, description, intro, minimap)
            # print(name['en'], v['Type'], v['Order'])
    return result


def upload_maps(maps: Iterable[Map]) -> list[Map]:
    requests = []
    succeeded_maps = []
    for m in maps:
        source1 = resource_root / f"Map/Introduce/{m.intro}.png"
        source2 = resource_root / f"Map/Mini2D/{m.minimap}.png"
        if not source1.exists() or not source2.exists():
            print(f"{m.name_en} does not have a corresponding map file")
            continue
        requests.append(UploadRequest(source1, m.intro_file, "[[Category:Map intro images]]"))
        requests.append(UploadRequest(source2, m.minimap_file, "[[Category:Minimaps]]"))
        succeeded_maps.append(m)
    process_uploads(requests)
    return succeeded_maps


def make_map_pages(maps: Iterable[Map]):
    lang = get_language()
    for m in maps:
        name_en = m.name_en
        p = Page(s, name_en + lang.page_suffix)
        if p.exists():
            continue
        result = ["{{MapTop|description=" + m.description[lang.code] + "}}",
                  "Game modes: "]
        gallery = [
            "=={{translate|Gallery}}==",
            "<gallery>",
            f"{m.minimap_file}|Minimap",
            f"File:Minimap {m.name_en} annotated.png|Annotated minimap",
            "</gallery>"
        ]
        result.append("\n".join(gallery))
        result.append("{{MapBottom}}")
        p.text = "\n\n".join(result)
        p.save("Create maps")


def main():
    maps = parse_maps().values()
    maps = upload_maps(maps)
    make_map_pages(maps)


if __name__ == '__main__':
    main()
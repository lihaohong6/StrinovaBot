from dataclasses import dataclass

from pywikibot import FilePage

from utils.asset_utils import resource_root
from utils.general_utils import get_char_by_id
from utils.json_utils import get_table, get_all_game_json, get_table_global
from utils.lang_utils import get_text
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s, save_json_page


@dataclass
class Emote:
    id: int
    quality: int
    name: dict[str, str]
    text: dict[str, str]

    @property
    def icon(self):
        return f"File:Emote_{self.id}.png"

    @property
    def description(self):
        return self.text

    @property
    def get_local_path(self):
        return f"Emote/T_Dynamic_Emote_{self.id}.png"


def get_emote_exceptions() -> dict[int, str]:
    exception_table: dict[str, list[int]] = {
        'Leona': [60000140, 60000141, 60000166, 60000167, 60000168],
        'Fragrans': [60000157, 60000158],
        'Eika': [60000161, 60000174],
        'Bai Mo': [60000162, 60000163],
        'Mara': [60000159, 60000160, 60000171, 60000172, 60000173],
        'Celestia': [60000175, 60000176],
        'Reiichi': [60000169, 60000170],
        'Yugiri': [60000164, 60000165],
        'Chiyo': [60000355, 60000356],
        'Yvette': [60000000 + i for i in range(360, 371)],
        'Kokona': [60000000 + i for i in range(371, 377)],
        "NOONEHASTHIEEMOTE": [60000000 + i for i in range(339, 355)],
    }
    result: dict[int, str] = {}
    for char_name, emote_list in exception_table.items():
        for emote_id in emote_list:
            result[emote_id] = char_name
    return result


def parse_emotes() -> dict[str, list[Emote]]:
    goods_table = get_table("Emote")
    i18n = get_all_game_json('Emote')
    items: dict[str, list[Emote]] = {}
    emote_exceptions = get_emote_exceptions()
    for k, v in goods_table.items():
        # if v['ItemType'] != 13:
        #     continue
        name_source = v['Name']['SourceString']
        # This algorithm sometimes mis-classifies emotes
        if k in emote_exceptions:
            name_en = emote_exceptions[k]
        else:
            role_id = v['RoleSkinId'] // 1000 % 1000
            name_en = get_char_by_id(role_id)
        if name_en is None:
            print(f"{name_source} has no EN character name")
            continue
        lst = items.get(name_en, [])
        emote = Emote(k,
                      v['Quality'],
                      get_text(i18n, v['Name']),
                      get_text(i18n, v['Desc']))
        lst.append(emote)
        items[name_en] = lst
    return items


def generate_emotes():
    upload_requests: list[UploadRequest] = []
    emotes = parse_emotes()
    for char_name, emote_list in emotes.items():
        for emote in emote_list:
            icon = emote.icon
            upload_requests.append(UploadRequest(resource_root / emote.get_local_path,
                                                 FilePage(s, icon),
                                                 '[[Category:Emotes]]',
                                                 "batch upload emotes"))
    process_uploads(upload_requests)
    save_json_page("Module:Emote/data.json", emotes)


def main():
    generate_emotes()


if __name__ == "__main__":
    main()

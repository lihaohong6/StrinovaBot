import json
from pathlib import Path

from utils.asset_utils import localization_root, csv_root, string_table_root, global_csv_root
from utils.lang import Language, LanguageVariants

json_cache: dict[str, dict | None] = {}


def load_json(file: str | Path) -> dict | None:
    if isinstance(file, str):
        file_str = file
        file = Path(file)
    else:
        file_str = str(file.absolute())
    if file_str not in json_cache:
        if file.exists():
            json_cache[file_str] = json.load(open(file, "r", encoding="utf-8"))
        else:
            json_cache[file_str] = None
    return json_cache[file_str]


def get_game_json(language: Language = LanguageVariants.ENGLISH.value):
    return load_json(localization_root / f"{language.game_json_dir}/Game.json")


def get_game_json_cn():
    return load_json(localization_root / "zh-Hans/Game.json")


def get_game_json_ja():
    return load_json(localization_root / "ja/Game.json")


def get_all_game_json(table_name: str) -> dict[str, dict]:
    i18n: dict[str, dict] = {}
    for lang in LanguageVariants:
        lang = lang.value
        r = get_game_json(language=lang)
        if r is not None:
            i18n[lang.code] = r[table_name]
    return i18n


table_cache: dict[str, dict] = {}


def get_table(file_name: str) -> dict[int, dict]:
    if file_name in table_cache:
        return table_cache[file_name]
    table = dict((int(k), v) for k, v in load_json(csv_root / f"{file_name}.json")['Rows'].items())
    table_cache[file_name] = table
    return table


def get_string_table(file_name: str) -> dict[int, str]:
    if file_name in table_cache:
        return table_cache[file_name]
    table = load_json(string_table_root / f"{file_name}.json")['StringTable']['KeysToMetaData']
    table_cache[file_name] = table
    return table


def get_table_global(file_name: str) -> dict[int, dict]:
    table_entry = "EN" + file_name
    if table_entry in table_cache:
        return table_cache[table_entry]
    json_data = load_json(global_csv_root / f"{file_name}.json")
    if json_data is None:
        raise FileNotFoundError(f"File {file_name}.json not found")
    table = dict((int(k), v) for k, v in json_data['Rows'].items())
    table_cache[table_entry] = table
    return table

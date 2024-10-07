import json
from pathlib import Path

from utils.asset_utils import localization_root
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

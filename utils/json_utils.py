import json
from pathlib import Path

from utils.asset_utils import localization_root
from utils.lang import Language, LanguageVariants

json_cache: dict[str, dict] = {}


def load_json(file: str | Path):
    if isinstance(file, str):
        file_str = file
    else:
        file_str = str(file.absolute())
    if file_str not in json_cache:
        json_cache[file_str] = json.load(open(file, "r", encoding="utf-8"))
    return json_cache[file_str]


def get_game_json(language: Language = LanguageVariants.ENGLISH.value):
    return load_json(localization_root / f"{language.game_json_dir}/Game.json")


def get_game_json_cn():
    return load_json(localization_root / "zh-Hans/Game.json")


def get_game_json_ja():
    return load_json(localization_root / "ja/Game.json")

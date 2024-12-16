import json
import re
from functools import cache

from pywikibot import Page

from char_info.skills import parse_string_energy_network_stats
from global_config import char_id_mapper, internal_names
from page_generator.maps import parse_maps
from page_generator.weapons import parse_weapons
from utils.general_utils import save_json_page, merge_dict, camp_id_to_string
from utils.json_utils import get_all_game_json
from utils.lang import Language, ENGLISH
from utils.lang_utils import get_multilanguage_dict, char_name_table, StringConverters
from utils.wiki_utils import s


@cache
def get_translations() -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    i18n_1 = get_all_game_json("ST_RoleName")
    i18n_2 = get_all_game_json("Goods")
    for char_id, char_name in char_id_mapper.items():
        internal_name: str | list[str] = [name for name, id in internal_names.items() if id == char_id]
        assert len(internal_name) >= 1
        if len(internal_name) > 1:
            internal_name = internal_name[-1]
        else:
            internal_name = internal_name[0]
        translated_names = get_multilanguage_dict(i18n_1, internal_name, default="")
        translated_names2 = get_multilanguage_dict(i18n_2, f"{char_id}_Name", default="")
        merged = merge_dict(translated_names, translated_names2, check=True)
        for lang, val in merged.items():
            if val.strip() == "":
                merged[lang] = char_name
        result[char_name] = merged
    for lang, overrides in char_name_table.items():
        for char_id, localized_name in overrides.items():
            result[char_id_mapper[char_id]][lang] = localized_name

    # faction names
    i18n = get_all_game_json("RoleTeam")
    for camp_id, camp_name in camp_id_to_string.items():
        result[camp_name] = get_multilanguage_dict(i18n, f"{camp_id}_NameCn", default=camp_name)

    weapons = parse_weapons()
    for w in weapons.values():
        if w.parent is None:
            result[w.name_en] = w.name

    # maps
    maps = parse_maps().values()
    for m in maps:
        result[m.name_en] = m.name

    # game modes
    i18n = get_all_game_json("PlayerSeasonData")
    for i in range(1, 6):
        d = get_multilanguage_dict(i18n, f"{i}_Name", converter=StringConverters.all_caps_remove)
        result[d[ENGLISH.code]] = d

    # skills
    i18n = get_all_game_json("ST_Common")
    for i in range(1, 4):
        d = get_multilanguage_dict(i18n, f"SkillTypeName_{i}")
        result[d[ENGLISH.code]] = d

    # Weapon types
    for i in [21, 22, 24]:
        d = get_multilanguage_dict(i18n, f"ItemTypeNameKey_{i}")
        result[d[ENGLISH.code]] = d

    # string energy network upgrades
    i18n = merge_dict(get_all_game_json("ST_GrowthDefine"), get_all_game_json("ST_InGame"))
    attributes = list(parse_string_energy_network_stats().values())[0].keys()
    # If something got changed, panic
    assert len(attributes) == 10
    for a in attributes:
        result[a] = get_multilanguage_dict(i18n, a)

    # Damage locations
    i18n = get_all_game_json("ST_UINonResidentFunctionsBattleData")
    result['Head'] = get_multilanguage_dict(i18n, "Header")
    result['Body'] = get_multilanguage_dict(i18n, "UpperBody")
    result['Legs'] = get_multilanguage_dict(i18n, "LowerBody")
    return result


def translate(original: str, lang: Language) -> str | None:
    return get_translations().get(original, {}).get(lang.code, None)


def generate_translations():
    result = get_translations()
    save_json_page("Module:Translate/data.json", result)


def transition_translation():
    pages = {
        'ru': Page(s, "Template:Translate/ru").text,
        'ja': Page(s, "Template:Translate/ja").text
    }

    result: dict[str, dict[str, str]] = {}

    for lang, text in pages.items():
        for line in text.split("\n"):
            r = re.search(r"\|(.+)=(.*)(\n|$)", line)
            if r is None:
                continue
            key, value = r.group(1), r.group(2)
            if key not in result:
                result[key] = {}
            result[key][lang] = value

    print(json.dumps(result, indent=4, ensure_ascii=False))


if __name__ == '__main__':
    generate_translations()

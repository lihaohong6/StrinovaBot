from global_config import char_id_mapper, internal_names
from utils.general_utils import save_json_page, merge_dict, camp_id_to_string
from utils.json_utils import get_all_game_json
from utils.lang_utils import get_multilanguage_dict, char_name_table


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
    return result


def generate_translations():
    result = get_translations()
    save_json_page("Module:Translate/data.json", result)


if __name__ == '__main__':
    generate_translations()

from dataclasses import dataclass, field

from utils.asset_utils import string_table_root
from utils.json_utils import get_game_json, load_json, get_table, get_table_global


@dataclass
class Setting:
    name_cn: str
    name_en: str
    tips: str
    options: list[str] = field(default_factory=list)


def get_settings():
    settings = get_table_global("Setting")
    i18n = get_game_json()['ST_Setting']
    string_table = load_json(string_table_root / "ST_Setting.json")['StringTable']['KeysToMetaData']
    current_type = ""
    current_title = ""
    result: dict[str, dict[str, list[Setting]]] = {}
    for k, v in settings.items():
        t = v['Type']
        if t != current_type:
            current_type = t
            if current_type not in result:
                result[current_type] = {}
        if 'Title' not in v or isinstance(v['Title'], str):
            continue
        title_key = v['Title'].get('Key', None)
        if title_key is not None and title_key != current_title:
            current_title = i18n.get(title_key, v['Title'].get('SourceString'))
            if current_title not in result[current_type]:
                result[current_type][current_title] = []
        tips_key = v['Tips']['Key']
        tips = "" if 'Key' not in v['Tips'] else i18n.get(tips_key, string_table[tips_key])
        name_key = v['Name']['Key']
        setting = Setting(string_table[name_key],
                          i18n.get(name_key, ""),
                          tips)
        if len(v['Options']) > 0:
            options = []
            for o in v['Options']:
                options.append(i18n.get(o['Key'], string_table[o['Key']]))
            setting.options = options
        result[current_type][current_title].append(setting)
    return result


def main():
    settings = get_settings()
    result = []
    for title, s1 in settings.items():
        result.append(f"=={title}==")
        for s_type, setting_list in s1.items():
            result.append(f"==={s_type}===")
            result.append("{{Settings | ")
            for setting in setting_list:
                setting.tips = setting.tips.strip().replace('\n', '<br/>')
                if len(setting.options) > 0:
                    setting.tips = "Options: " + ", ".join(setting.options) + "<br/><br/>" + setting.tips
                result.append(f"{{{{Settings/row | cn={setting.name_cn} | en={setting.name_en} | tips={setting.tips} }}}}")
            result.append("}}")
    print("\n".join(result))


if __name__ == "__main__":
    main()
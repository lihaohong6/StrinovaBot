import json
import re

import wikitextparser as wtp
from wikitextparser import Template

from audio.audio_utils import get_json_path, parse_path
from utils.general_utils import get_char_pages
from utils.json_utils import load_json
from utils.lang import get_language, Language, languages_with_audio


def pull_from_miraheze():
    lang = get_language()
    for char_id, char_name, page in get_char_pages("/audio", lang=lang):
        if not page.exists():
            print(page.title() + " does not exist")
            continue
        json_file = get_json_path(char_name)
        assert json_file.exists(), f"{json_file} does not exist"
        existing = load_json(json_file)
        path_to_voice: dict[str, dict] = {}
        for v in existing.values():
            path_to_voice[v['path']] = v
        parsed = wtp.parse(page.text)
        templates = []
        for t in parsed.templates:
            if t.name.strip().lower() == "voice/row":
                templates.append(t)
        changed = False
        for t in templates:
            args = ["FileCN", "FileJA", "FileEN"]
            args = [t.get_arg(arg) for arg in args if t.has_arg(arg)]
            assert len(args) >= 1, f"For char {char_name}, there is no arg in {t}"
            path = re.sub(r"^[A-Z]{2}_", "", args[0].value).replace(".ogg", "").strip()
            assert path in path_to_voice
            voice = path_to_voice[path]
            res = merge_template_with_voice(t, voice, lang)
            changed = res or changed
        if not changed:
            print("No change for " + char_name)
            continue
        json.dump(existing, open(json_file, "w", encoding="utf-8"), ensure_ascii=False, indent=4)
        print("Overwriting " + char_name)


def merge_template_with_voice(template: Template, voice: dict, lang: Language):
    changed = False
    mapping = {
        "Title": ["title", lang.code]
    }
    for audio_lang in languages_with_audio():
        mapping[f'Text{audio_lang.code.upper()}'] = ["transcription", audio_lang.code]
        mapping[f'Trans{audio_lang.code.upper()}'] = ["translation", audio_lang.code, lang.code]
    parsed_path = parse_path(voice['path'])
    assert parsed_path, f"{voice['path']} cannot be parsed"
    regular_titles = set(v for v in parsed_path.title.values() if len(v) > 0)
    for k, json_keys in mapping.items():
        arg = template.get_arg(k)
        if arg is None:
            continue
        arg = arg.value.strip()

        def get_val(keys: list[str]) -> str | None:
            temp: dict | str | None = voice
            for key in keys:
                temp = temp.get(key, None)
                if temp is None:
                    return None
            return temp

        def set_val(keys: list[str], value: str) -> None:
            temp = voice
            for key in keys[:-1]:
                prev = temp
                temp = temp.get(key, None)
                if temp is None:
                    prev[key] = {}
                    temp = prev.get(key, None)
            temp[keys[-1]] = value

        if arg != "" and arg != get_val(json_keys):
            if k == "Title" and arg in regular_titles:
                continue
            set_val(json_keys, arg)
            changed = True
    return changed


if __name__ == "__main__":
    pull_from_miraheze()

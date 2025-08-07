import json
import pickle
import re
from typing import Any

from pywikibot import Page

from audio.audio_parser import role_voice, match_custom_triggers
from audio.audio_utils import VoiceJson, get_json_path, Trigger
from audio.voice import Voice, VoiceUpgrade
from global_config import char_id_mapper, get_characters
from utils.dict_utils import merge_dict
from utils.file_utils import cache_dir
from utils.general_utils import get_bwiki_char_pages
from utils.json_utils import load_json
from utils.wiki_utils import bwiki


def merge_results(previous: VoiceJson, current: VoiceJson, discard_non_local: bool = False) -> VoiceJson:
    """
    Goal: use current as base and override certain attributes with previous
    :return: merged dict
    """
    result: dict[str, dict[str, Any]] = {}
    for voice in current.values():
        result[voice['path']] = voice
    for voice in previous.values():
        path = voice['path']
        if path not in result:
            if not discard_non_local:
                result[path] = voice
                voice['non_local'] = True
            else:
                continue
            print(f"{path} not in current. Prev: {voice}")
        for k, v in voice.items():
            if k in {'transcription', 'title', 'translation'}:
                result[path][k] = merge_dict(v, result[path][k])
    return current


def make_character_json(triggers: list[Trigger], char_id: int, discard: bool = False) -> None:
    def voice_filter(v: Voice):
        return v.role_id == 0 or v.role_id == char_id

    result: dict[int, dict[str, Any]] = {}
    attributes = ["path", "file", "transcription", "translation"]

    for t in triggers:
        for v in t.voices:
            if not voice_filter(v):
                continue
            titles = v.title.copy()
            # Title is supposed to be empty if it's the same as the trigger
            for k, v in titles.items():
                titles[k] = ""
            # titles.update(t.name)
            obj = {"id": v.id[0],
                   'title': titles}
            for attribute in attributes:
                obj[attribute] = getattr(v, attribute)
            result[obj['id']] = obj

    char_name = char_id_mapper[char_id]
    previous_path = get_json_path(char_name)
    if previous_path.exists():
        previous = load_json(previous_path)
    else:
        previous = {}
    # json files are stored with string keys instead of int keys
    previous = dict((int(k), v) for k, v in previous.items())
    result = merge_results(previous=previous,
                           current=result,
                           discard_non_local=discard)
    with open(get_json_path(char_name), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


def get_bwiki_audio_text() -> dict[str, str]:
    import wikitextparser as wtp
    result: dict[str, str] = {}
    cache_file = cache_dir / "bwiki_audio_text.pickle"
    if cache_file.exists():
        return pickle.load(cache_file.open("rb"))
    for char_id, char_name, page in get_bwiki_char_pages():
        parsed = wtp.parse(page.text)
        for section in parsed.sections:
            if section.title is not None and "角色台词" in section.title:
                break
        else:
            print("Audio section not found on " + page.title())
            continue
        if "/语音台词" in str(section):
            page = Page(bwiki(), page.title() + "/语音台词")
            text = page.text
        else:
            text = str(section)
        result[char_name] = text
    pickle.dump(result, cache_file.open("wb"))
    return result


def match_role_voice_with_bwiki(voices: list[Voice]):
    bwiki_texts: dict[str, str] = get_bwiki_audio_text()
    for char in get_characters():
        text = bwiki_texts.get(char.name, None)
        if text is None:
            continue
        text_seen: set[str] = set()
        for v in voices:
            if char.id != v.role_id:
                continue
            digits = re.search(r"(\d{3})(_|$)", v.path)
            # if (digits is None or
            #         ((v.path[-2:] in {"_a", "_b", "_c"}) and
            #          "red" not in v.path and
            #          "org" not in v.path)):
            #     continue
            digits = digits.group(1)
            upgrade = v.upgrade
            results = re.findall(f"语音-{digits}" + r"(CN|JP)([^|]+)\|([^|<}}{{\\]+)", text, re.DOTALL)
            if len(results) == 0:
                continue
            for r in results:
                result_upgrade = VoiceUpgrade.ORG if "org" in r[1] else \
                    (VoiceUpgrade.RED if "red" in r[1] else VoiceUpgrade.REGULAR)
                if upgrade != result_upgrade:
                    continue
                res: str = r[2].strip()
                if res in text_seen:
                    continue
                text_seen.add(res)
                if r[0] == "CN":
                    v.text_cn = res
                else:
                    v.text_jp = res


def make_json():
    voices = role_voice()
    # noinspection PyUnreachableCode
    if False:
        # Do not call this function: CC BY-NC-SA 4.0
        match_role_voice_with_bwiki(list(voices.values()))
    triggers = match_custom_triggers(list(voices.values()))
    for char_id, char_name in char_id_mapper.items():
        make_character_json(triggers, char_id, discard=False)


def main():
    make_json()


if __name__ == "__main__":
    main()

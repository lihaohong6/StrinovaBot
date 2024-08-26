import re

import json
import os
import subprocess
from pathlib import Path
from sys import argv
from typing import Any

from pywikibot import FilePage, Page
from pywikibot.pagegenerators import PreloadingGenerator, GeneratorFactory

from audio.audio_parser import VoiceUpgrade, Voice, Trigger, in_game_triggers, in_game_triggers_upgrade, role_voice, \
    match_custom_triggers
from data.conversion_table import VoiceType
from global_config import char_id_mapper, internal_names
from utils.asset_utils import audio_root, wav_root_cn
from data.conversion_table import voice_conversion_table
from utils.general_utils import get_bwiki_char_pages, load_json
from utils.uploader import upload_file
from utils.wiki_utils import s, bwiki

import wikitextparser as wtp


def audio_convert():
    output_root = Path("files/audio")
    output_root.mkdir(exist_ok=True, parents=True)
    for file in audio_root.rglob("*.txtp"):
        file_name = file.name
        out_path = output_root.joinpath(file.relative_to(audio_root))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path = out_path.parent.joinpath(file_name.replace(".txtp", ".wav"))
        subprocess.call(["vgmstream-cli.exe", file, "-o", out_path], stdout=open(os.devnull, 'wb'))


def pick_two(a: str, b: str) -> str:
    """
    Pick a string. Prefer the first one but use the second one if the first is empty.
    :param a:
    :param b:
    :return:
    """
    if "NoTextFound" in a:
        a = ""
    if "NoTextFound" in b:
        b = ""
    if a.strip() in {"", "?", "彩蛋"}:
        return b
    return a


def pick_string(strings: list[str]) -> str:
    i = len(strings) - 2
    while i >= 0:
        strings[i] = pick_two(strings[i], strings[i + 1])
        i -= 1
    return strings[0]


def upload_audio(source: Path, target: FilePage, text: str):
    assert source.exists()
    temp_file = Path("temp.ogg")
    subprocess.run(["ffmpeg", "-i", source, "-c:a", "libopus", "-y", temp_file],
                   check=True,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL
                   )
    upload_file(text=text, target=target, file=temp_file)
    temp_file.unlink()


def upload_audio_file(voices: list[Voice], char_name: str):
    for v in voices:
        path_cn = audio_root.joinpath("Chinese").joinpath(f"{v.file_cn}")
        assert path_cn.exists(), f"{path_cn} does not exist"
        v.file_page_cn = f"CN_{v.path}.ogg"
        path_jp = audio_root.joinpath("Japanese").joinpath(f"{v.file_jp}")
        if v.file_jp != "" and path_jp.exists():
            v.file_page_jp = f"JP_{v.path}.ogg"
    gen = GeneratorFactory()
    gen.handle_args([f"-cat:{char_name} voice lines", "-ns:File"])
    gen = gen.getCombinedGenerator()
    existing: set[str] = set(p.title(underscore=True, with_ns=False) for p in gen)
    text = f"[[Category:{char_name} voice lines]]"
    for v in voices:
        assert v.file_page_cn != ""
        if v.file_page_cn not in existing:
            path = audio_root.joinpath("Chinese").joinpath(f"{v.file_cn}")
            upload_audio(path, FilePage(s, "File:" + v.file_page_cn), text)
        # FIXME: Vox_SelectCharacter-0208-event.wav is for Michele in CN but for Yvette in JP;
        #  do not upload Japanese files for now
        if v.file_page_jp not in existing and v.file_page_jp != "":
            path = audio_root.joinpath("Japanese").joinpath(f"{v.file_jp}")
            upload_audio(path, FilePage(s, "File:" + v.file_page_jp), text)


def make_character_json(triggers: list[Trigger], char_id: int):
    def voice_filter(v: Voice):
        return v.role_id == 0 or v.role_id == char_id

    result: dict[int, [dict[str, Any]]] = {}
    attributes = ["path", "file_cn", "file_jp", "text_cn", "text_en", "text_jp"]

    for t in triggers:
        for v in t.voices:
            if not voice_filter(v):
                continue
            title_cn = pick_string([t.name_cn, v.name_cn, t.description_cn])
            title_en = pick_string([t.name_en, v.name_en, t.description_en])
            obj = {"id": v.id[0], 'title_cn': '', 'title_en': '', '__title_hint': title_cn + "/" + title_en}
            for attribute in attributes:
                obj[attribute] = getattr(v, attribute)
            result[obj['id']] = obj

    char_name = char_id_mapper[char_id]
    with open(f"audio/data/{char_name}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


def make_table(triggers: list[Trigger]):
    result = ['{{Voice/start}}']
    for t in triggers:
        for voice in t.voices:
            title = pick_string([voice.name_en, t.name_en, t.name_cn])

            title_extra = ""
            if "red" in voice.path:
                title_extra = " (legendary skin)"
            if "org" in voice.path:
                title_extra = " (dorm skin)"

            args = [
                ("Title", f"{title}{title_extra}"),
                ("FileCN", f"CN_{voice.path}.ogg"),
                ("TextCN", voice.text_cn),
                ("TextEN", voice.text_en),
            ]

            if voice.file_page_jp != "":
                args.append(("FileJP", f"JP_{voice.path}.ogg"))
                args.append(("TextJP", voice.text_jp))

            result.append("{{Voice/row | " + " | ".join(f"{k}={v}" for k, v in args) + " }}")
    result.append('{{Voice/end}}')
    return "\n".join(result)


def load_json_voices(char_name: str) -> list[Voice]:
    voices_json = load_json("audio/data/" + char_name + ".json")
    voices = []
    for voice_id, voice_data in voices_json.items():
        voice = Voice([int(voice_id)])
        for k, v in voice_data.items():
            setattr(voice, k, v)
        voice.id = [voice.id]
        voices.append(voice)
    return voices


def make_character_audio_page(char_id: int):
    result = ["{{CharacterAudioTop}}"]
    char_name = char_id_mapper[char_id]
    voices = load_json_voices(char_name)
    upload_audio_file(voices, char_name)
    triggers = match_custom_triggers(voices)
    for voice_type in VoiceType:
        t_list = [t for t in triggers if t.type.value == voice_type.value]
        result.append(f"=={voice_type.value}==")
        table = make_table(t_list)
        result.append(table)
        result.append("")
    p = Page(s, f"{char_name}/audio")
    p.text = "\n".join(result)
    p.save("Generate audio page")


def parse_system_voice():
    """
    InGameSystemVoiceTrigger.json
    InGameSystemVoiceUpgrade.json (for Kanami)
    Files with prefix "Vox_Communicate"
    :return:
    """
    pass


def match_role_voice_with_bwiki(voices: list[Voice]):
    import wikitextparser as wtp
    for char_id, char_name, page in get_bwiki_char_pages():
        parsed = wtp.parse(page.text)
        for section in parsed.sections:
            if section.title is not None and section.title == "角色台词":
                break
        else:
            print("Audio section not found on " + page.title())
            continue
        if "/语音台词" in str(section):
            page = Page(bwiki(), page.title() + "/语音台词")
            text = page.text
        else:
            text = str(section)
        for v in voices:
            if char_id != v.role_id:
                continue
            digits = re.search(r"(\d{3})(_|$)", v.path)
            if digits is None or (v.path.endswith("_a") and "red" not in v.path and "org" not in v.path):
                continue
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
                if r[0] == "CN":
                    v.text_cn = res
                else:
                    v.text_jp = res


def make_json():
    voices = role_voice()
    match_role_voice_with_bwiki(list(voices.values()))
    triggers = match_custom_triggers(list(voices.values()))
    for char_id, char_name in char_id_mapper.items():
        make_character_json(triggers, char_id)


def test_audio():
    voices = role_voice()
    triggers = in_game_triggers()
    upgrades = in_game_triggers_upgrade()
    custom_triggers = match_custom_triggers(list(voices.values()))
    can_be_triggered: set[int] = set()
    missing_1 = 0
    for t in triggers + upgrades + custom_triggers:
        for vid in t.voice_id:
            can_be_triggered.add(vid)
            if vid not in voices:
                # print(f"{vid} can be triggered by {t} but is not in a voice file")
                missing_1 += 1
        # if hasattr(t, "voices"):
        #     for v in t.voices:
        #         if v.id[0] in can_be_triggered:
        #             print(t.id, t.description_cn, "is a duplicate trigger")
        #         can_be_triggered.add(v.id[0])

    nums = [num for table in voice_conversion_table.values() for num in table.keys()]

    missing_2 = 0
    orphans = []
    for k, v in voices.items():
        # if k in can_be_triggered:
        #     continue
        # if v.name_cn != "":
        #     continue
        if v.path.startswith("Vox_") and v.path.split("_")[1] in internal_names:
            for c in nums:
                if c in v.path:
                    break
            else:
                # print(f"Orphan voice: {v}")
                missing_2 += 1
                orphans.append(v)
        else:
            missing_2 += 1
            orphans.append(v)
    print(f"Missing voice files: {missing_1}. Missing trigger {missing_2}")
    voices_non_orphan = [v for k, v in voices.items() if k in can_be_triggered]
    print(f"Non-orphan voice-lines: {len(voices_non_orphan)}")
    print("\n".join(str(o) for o in orphans))

    # TODO:
    #  Role.json: UnlockVoiceId, AppearanceVoiceId, EquipSecondWeaponVoiceId, EquipGrenadeVoiceId
    exists = set()
    while True:
        cond = input("Cond: ")
        for v in voices.values():
            conditions = ["_" + cond.strip()]
            if any(c in v.path for c in conditions):
                if v.path in exists:
                    continue
                exists.add(v.path)
                print(v.path + "    " + v.file)
                os.startfile(wav_root_cn / v.file)


def make_character_audio_pages():
    for char_id, char_name in char_id_mapper.items():
        if char_name == "Fuchsia":
            make_character_audio_page(char_id)


def pull_from_miraheze():
    pages = PreloadingGenerator(generator=(Page(s, f"{char_name}/audio") for char_name in char_id_mapper.values()))
    for page in pages:
        if not page.exists():
            print(page.title() + " does not exist")
            continue
        char_name = page.title().split("/")[0]
        json_file = Path(f"audio/data/{char_name}.json")
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
            path = t.get_arg("FileCN").value.replace("CN_", "").replace(".ogg", "").strip()
            assert path in path_to_voice
            voice = path_to_voice[path]
            mapping = {
                "TextCN": "text_cn",
                "TextEN": "text_en",
                "TextJP": "text_jp"
            }
            for k, v in mapping.items():
                arg = t.get_arg(k)
                if arg is None:
                    continue
                arg = arg.value.strip()
                if arg != "" and arg != voice[v]:
                    voice[v] = arg
                    changed = True
        if not changed:
            print("No change for " + char_name)
            continue
        json.dump(existing, open(json_file, "w", encoding="utf-8"), ensure_ascii=False, indent=4)
        print("Overwriting " + char_name)


def main():
    commands = {
        "push": make_character_audio_pages,
        "gen": make_json,
        "pull": pull_from_miraheze,
        "test": test_audio,
    }
    commands[argv[1]]()


if __name__ == "__main__":
    main()

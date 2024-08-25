import re

import json
import os
import subprocess
from dataclasses import dataclass, fields, field
from enum import Enum
from pathlib import Path
from typing import Any

from pywikibot import FilePage, Page
from pywikibot.pagegenerators import PreloadingGenerator, GeneratorFactory

from data.conversion_table import VoiceType
from global_config import char_id_mapper, internal_names
from utils.asset_utils import audio_root, audio_event_root, wav_root_cn, wav_root_jp
from data.conversion_table import voice_conversion_table
from utils.general_utils import get_table, get_game_json, get_bwiki_char_pages, load_json
from utils.uploader import upload_file
from utils.wiki_utils import s, bwiki


def audio_convert():
    output_root = Path("files/audio")
    output_root.mkdir(exist_ok=True, parents=True)
    for file in audio_root.rglob("*.txtp"):
        file_name = file.name
        out_path = output_root.joinpath(file.relative_to(audio_root))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path = out_path.parent.joinpath(file_name.replace(".txtp", ".wav"))
        subprocess.call(["vgmstream-cli.exe", file, "-o", out_path], stdout=open(os.devnull, 'wb'))


class VoiceUpgrade(Enum):
    REGULAR = ""
    ORG = "org"
    RED = "red"


@dataclass
class Voice:
    id: list[int]
    role_id: int = -1
    quality: int = -1
    name_cn: str = ""
    name_en: str = ""
    text_cn: str = ""
    text_en: str = ""
    text_jp: str = ""
    path: str = ""
    file_cn: str = ""
    file_jp: str = ""
    file_page_cn: str = ""
    file_page_jp: str = ""
    upgrade: VoiceUpgrade = VoiceUpgrade.REGULAR

    def merge(self, o: "Voice"):
        assert self.file_cn == o.file_cn and self.path == o.path
        assert len(o.id) == 1
        self.id.append(o.id[0])
        for f in fields(self):
            if f.type == str:
                a1 = getattr(self, f.name)
                a2 = getattr(o, f.name)
                if a1 == a2:
                    continue
                if a1 == "":
                    setattr(self, f.name, a2)
                raise RuntimeError(str(self) + "\n" + str(o))
        if self.role_id != o.role_id:
            if self.role_id == 999:
                self.role_id = o.role_id


@dataclass
class Trigger:
    id: int
    type: VoiceType
    name_cn: str = ""
    name_en: str = ""
    description_cn: str = ""
    description_en: str = ""
    voice_id: list[int] = field(default_factory=list)
    # 0: applicable for all
    # otherwise: applicable to a single character
    role_id: int = 0
    voices: list[Voice] = field(default_factory=list)
    children: list["UpgradeTrigger"] = field(default_factory=list)

    def merge(self, o: "Trigger"):
        assert self.id == o.id and self.type == o.type
        for f in fields(self):
            if f.type == str:
                a1 = getattr(self, f.name)
                a2 = getattr(o, f.name)
                if a1 == a2:
                    continue
                if a1 == "":
                    setattr(self, f.name, a2)
                raise RuntimeError(str(self) + "\n" + str(o))
        if self.role_id != o.role_id:
            if self.role_id == 999:
                self.role_id = o.role_id


@dataclass
class UpgradeTrigger:
    trigger: int
    voice_id: list[int]
    skins: list[int]


def find_audio_file(file_name: str, table: dict, bank_name_to_files: dict) -> str | None:
    assert len(table) > 0
    event_file = audio_event_root / f"{file_name}.json"
    if not event_file.exists():
        # print(event_file.name + " does not exist")
        return None
    data = load_json(event_file)["Properties"]
    bank_name = data["RequiredBank"]["ObjectName"].split("'")[1]
    short_id = str(data["ShortID"])
    if short_id not in table:
        # print(f"Short ID {short_id} is not in conversion table")
        return None
    ix = int(table[short_id])
    candidates = []
    if bank_name not in bank_name_to_files:
        # print(f"No file corresponding to bank name " + bank_name)
        return None
    for f in bank_name_to_files[bank_name]:
        if f"-{ix:04d}-" in f.name:
            candidates.append(f)
    if len(candidates) == 0:
        # print(f"No audio file found for {file_name} and bank {bank_name}")
        return None
    return candidates[0].name


def parse_bank(bank_file: Path, table: dict[str, str]):
    assert bank_file.exists()
    lines = open(bank_file, "r", encoding="utf-8").readlines()
    ix = None
    sid = None
    for line in lines:
        if "ix=" in line:
            ix = re.search(r'ix="(\d+)"', line).group(1)
        if 'ty="sid"' in line:
            sid = re.search(r'va="(\d+)"', line).group(1)
            if ix is not None:
                table[sid] = ix


def parse_banks_xml():
    sid_to_ix_cn = {}
    cn_bank_file = audio_root / "banks/cn_banks.xml"
    parse_bank(cn_bank_file, sid_to_ix_cn)
    sid_to_ix_ja = {}
    jp_bank_file = audio_root / "banks/ja_banks.xml"
    parse_bank(jp_bank_file, sid_to_ix_ja)
    return sid_to_ix_cn, sid_to_ix_ja


def map_bank_name_to_files(p: Path) -> dict[str, list[Path]]:
    table = {}
    for f in p.iterdir():
        bank_name = f.name.split("-")[0]
        if bank_name not in table:
            table[bank_name] = []
        table[bank_name].append(f)
    return table


def get_text(i18n, v):
    name_obj = v['VoiceName']
    key = name_obj.get("Key", None)
    if key is not None:
        name_cn = name_obj["SourceString"]
    else:
        name_cn = ""
    name_en = i18n.get(key, "")
    content_obj = v['Content']
    key = content_obj.get("Key", None)
    if key is not None:
        content_cn = content_obj["SourceString"]
    else:
        content_cn = ""
    content_en = i18n.get(key, "")
    return content_cn, content_en, name_cn, name_en


def in_game_triggers() -> list[Trigger]:
    i18n = get_game_json()['InGameVoiceTrigger']
    table = get_table("InGameVoiceTrigger")
    result: list[Trigger] = []
    for k, v in table.items():
        description_cn = v['Desc']['SourceString']
        description_en = i18n.get(v['Desc']['Key'], "")
        role_id: int = v['RoleId']
        voice_id: list[int] = [v['VoiceId']]
        if "RandomVoiceIds" in v:
            lst = v["RandomVoiceIds"]
            if len(lst) > 0:
                assert v['IsRandom']
                voice_id = lst
        result.append(
            Trigger(k, description_cn=description_cn, description_en=description_en, voice_id=voice_id, role_id=role_id,
                    type=VoiceType.BATTLE))
    return result


def in_game_triggers_upgrade() -> list[UpgradeTrigger]:
    table = get_table("InGameVoiceUpgrade")
    result: list[UpgradeTrigger] = []
    for k, v in table.items():
        trigger: int = v["TriggerInGameVoiceId"]
        voice_id: list[int] = v["RandomVoiceIdList"]
        skins: list[int] = v["RoleSkinIdList"]
        result.append(UpgradeTrigger(trigger, voice_id, skins))
    return result


def role_voice() -> dict[int, Voice]:
    table_cn, table_jp = parse_banks_xml()
    bank_name_to_files_cn = map_bank_name_to_files(wav_root_cn)
    bank_name_to_files_jp = map_bank_name_to_files(wav_root_jp)
    i18n = get_game_json()['RoleVoice']
    voice_table = get_table("RoleVoice")
    path_to_voice: dict[str, Voice] = {}

    voices = {}
    for k, v in voice_table.items():
        content_cn, content_en, name_cn, name_en = get_text(i18n, v)

        path = v["AkEvent"]["AssetPathName"].split(".")[-1]
        file_cn = find_audio_file(path, table_cn, bank_name_to_files_cn)
        if file_cn is None:
            continue
        file_jp = find_audio_file(path, table_jp, bank_name_to_files_jp)
        if file_jp is None:
            file_jp = ""
        upgrade = VoiceUpgrade.REGULAR
        if "org" in path:
            upgrade = VoiceUpgrade.ORG
        if "red" in path:
            upgrade = VoiceUpgrade.RED
        voice = Voice(id=[k],
                      role_id=v['RoleId'],
                      quality=v['Quality'],
                      name_cn=name_cn.strip(),
                      name_en=name_en.strip(),
                      text_cn=content_cn.strip(),
                      text_en=content_en.strip(),
                      path=path.strip(),
                      file_cn=file_cn.strip(),
                      file_jp=file_jp.strip(),
                      upgrade=upgrade)
        if path in path_to_voice:
            path_to_voice[path].merge(voice)
            voice = path_to_voice[path]
        else:
            path_to_voice[path] = voice
        voices[k] = voice
    return voices


def match_custom_triggers(voices: list[Voice]) -> list[Trigger]:
    triggers: dict[str, Trigger] = {}

    def make_trigger(key, name_cn, name_en, type: VoiceType):
        triggers[key] = Trigger(
            id=int(key),
            name_cn=name_cn,
            name_en=name_en,
            description_cn=name_cn,
            description_en=name_en,
            role_id=0,
            type=type,
        )

    for voice_type, table in voice_conversion_table.items():
        for key, names in table.items():
            make_trigger(key, names[0], names[1], voice_type)

    voice_found: set[tuple] = set()

    for v in voices:
        ids = tuple(v.id)
        if ids in voice_found:
            continue
        voice_found.add(ids)
        digits = re.search(r"(\d{3})(_|$)", v.path)
        if digits is None:
            continue
        digits = digits.group(1)
        if digits in triggers:
            triggers[digits].voices.append(v)
    return list(triggers.values())


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


def make_json(triggers: list[Trigger], char_id: int):
    def voice_filter(v: Voice):
        return v.role_id == 0 or v.role_id == char_id

    result: dict[int, [dict[str, Any]]] = {}
    attributes = ["path", "file_cn", "file_jp", "text_cn", "text_en", "text_jp"]

    for t in triggers:
        for v in t.voices:
            if not voice_filter(v):
                continue
            title_cn = pick_string([t.name_cn, v.name_cn, t.description_cn])
            obj = {"id": v.id[0], 'title_cn': '', 'title_en': '', '__title_hint': title_cn}
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
            results = re.findall(rf"语音-{digits}(CN|JP)([^|]+)\|([^|]+)", text, re.DOTALL)
            if len(results) == 0:
                continue
            for r in results:
                result_upgrade = VoiceUpgrade.ORG if "org" in r[1] else \
                    (VoiceUpgrade.RED if "red" in r[1] else VoiceUpgrade.REGULAR)
                if upgrade != result_upgrade:
                    continue
                if r[0] == "CN":
                    v.text_cn = r[2].strip()
                else:
                    v.text_jp = r[2].strip()


def make_character_audio_pages():
    voices = role_voice()
    match_role_voice_with_bwiki(list(voices.values()))
    # triggers = dict((t.id, t) for t in in_game_triggers())
    # upgrades = in_game_triggers_upgrade()
    # for upgrade in upgrades:
    #     if upgrade.trigger not in triggers:
    #         continue
    #     triggers[upgrade.trigger].children.append(upgrade)
    custom_triggers = match_custom_triggers(list(voices.values()))
    all_triggers = custom_triggers
    result = []
    for t in all_triggers:
        for voice_id in t.voice_id:
            if voice_id not in voices:
                break
            t.voices.append(voices[voice_id])
        else:
            result.append(t)
    for char_id, char_name in char_id_mapper.items():
        make_json(result, char_id)
        make_character_audio_page(char_id)


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


def main():
    make_character_audio_pages()
    # test_audio()
    pass


if __name__ == "__main__":
    main()

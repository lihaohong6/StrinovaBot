import re
from dataclasses import dataclass, fields, field
from enum import Enum
from pathlib import Path

from audio.data.conversion_table import VoiceType, voice_conversion_table, table_languages
from utils.asset_utils import audio_event_root_cn, audio_root, audio_event_root_global
from utils.general_utils import get_table
from utils.json_utils import load_json, get_all_game_json
from utils.lang import CHINESE, Language, languages_with_audio, ENGLISH
from utils.lang_utils import get_multilanguage_dict


class VoiceUpgrade(Enum):
    REGULAR = ""
    ORG = "org"
    RED = "red"


@dataclass
class Voice:
    id: list[int]
    role_id: int = -1
    quality: int = -1
    # title: displayed on the wiki
    title: dict[str, str] = field(default_factory=dict)
    # name: given by the game itself
    name: dict[str, str] = field(default_factory=dict)
    transcription: dict[str, str] = field(default_factory=dict)
    translation: dict[str, dict[str, str]] = field(default_factory=dict)
    path: str = ""
    file: dict[str, str] = field(default_factory=dict)
    file_page: dict[str, str] = field(default_factory=dict)
    upgrade: VoiceUpgrade = VoiceUpgrade.REGULAR

    def merge(self, o: "Voice"):
        assert self.path == o.path
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
            elif f.type == dict:
                raise RuntimeError("TODO: dict merge unimplemented")
        if self.role_id != o.role_id:
            if self.role_id == 999:
                self.role_id = o.role_id

    def get_file_page(self, lang: Language):
        return f"{lang.audio_code.upper()}_{self.path}.ogg"

    def set_file_page(self, lang: Language):
        self.file_page[lang.code] = self.get_file_page(lang)

    def path_digits(self) -> str | None:
        return get_voice_path_digits(self.path)

    @property
    def icon(self):
        assert self.role_id != 0
        return f"File:Item Icon 22{self.role_id}001.png"


def get_voice_path_digits(path: str) -> str | None:
    r = re.search(r"(\d{3})(_|$)", path)
    if r is None:
        return None
    return r.group(1)


@dataclass
class Trigger:
    id: int
    type: VoiceType
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
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
            elif f.type == dict:
                raise RuntimeError("TODO: dict merge unimplemented")
        if self.role_id != o.role_id:
            if self.role_id == 999:
                self.role_id = o.role_id


@dataclass
class UpgradeTrigger:
    trigger: int
    voice_id: list[int]
    skins: list[int]


def find_audio_file(event_file: Path, table: dict, bank_name_to_files: dict[str, list[Path]]) -> str | None:
    assert len(table) > 0
    if not event_file.exists():
        # print(event_file.name + " does not exist")
        return None
    json_data = load_json(event_file)
    if "Properties" not in json_data:
        json_data = json_data[0]
    data = json_data["Properties"]
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


def parse_banks_xml(lang: Language):
    sid_to_ix = {}
    bank_file = audio_root / f"banks/{lang.code}_banks.xml"
    parse_bank(bank_file, sid_to_ix)
    return sid_to_ix


def map_bank_name_to_files(p: Path) -> dict[str, list[Path]]:
    table = {}
    for f in p.iterdir():
        bank_name = f.name.split("-")[0]
        if bank_name not in table:
            table[bank_name] = []
        table[bank_name].append(f)
    return table


def get_text(i18n: dict[str, dict], v) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, str]]]:
    name_obj = v['VoiceName']
    key = name_obj.get("Key", None)
    title: dict[str, str] = get_multilanguage_dict(i18n, key, "", extra="" if key is None else name_obj["SourceString"])

    content_obj = v['Content']
    key = content_obj.get("Key", None)
    content = {
        CHINESE.code: "" if key is None else content_obj["SourceString"]
    } | get_multilanguage_dict(i18n, key, "")

    language_codes_with_audio = set(l.code for l in languages_with_audio())

    transcriptions = dict((k, v) for k, v in content.items() if k in language_codes_with_audio)
    translations = {}
    translations.update(dict((k, v) for k, v in content.items() if k not in language_codes_with_audio))
    return title, transcriptions, {CHINESE.code: translations}


def in_game_triggers() -> list[Trigger]:
    i18n = get_all_game_json('InGameVoiceTrigger')
    table = get_table("InGameVoiceTrigger")
    result: list[Trigger] = []
    for k, v in table.items():
        description = {CHINESE.code: v['Desc']['SourceString']} | get_multilanguage_dict(i18n, v['Desc']['Key'], "")
        role_id: int = v['RoleId']
        voice_id: list[int] = [v['VoiceId']]
        if "RandomVoiceIds" in v:
            lst = v["RandomVoiceIds"]
            if len(lst) > 0:
                assert v['IsRandom']
                voice_id = lst
        result.append(
            Trigger(k, description=description, voice_id=voice_id, role_id=role_id,
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


def parse_role_voice() -> dict[int, Voice]:
    """
    Lightweight version that does not deal with files.
    :return:
    """
    i18n = get_all_game_json('RoleVoice')
    voice_table = get_table("RoleVoice")

    voices = {}
    path_to_voice: dict[str, Voice] = {}
    for k, v in voice_table.items():
        name, transcription, translation = get_text(i18n, v)

        path: str = v["AkEvent"]["AssetPathName"].split(".")[-1]
        upgrade = VoiceUpgrade.REGULAR
        if "org" in path:
            upgrade = VoiceUpgrade.ORG
        if "red" in path:
            upgrade = VoiceUpgrade.RED
        voice = Voice(id=[k],
                      role_id=v['RoleId'],
                      quality=v['Quality'],
                      name=name,
                      transcription=transcription,
                      translation=translation,
                      path=path.strip(),
                      upgrade=upgrade)
        if path in path_to_voice:
            path_to_voice[path].merge(voice)
            voice = path_to_voice[path]
        else:
            path_to_voice[path] = voice
        voices[k] = voice
    return voices



def role_voice() -> dict[int, Voice]:
    tables: dict[str, dict] = {}
    bank_name_to_files: dict[str, dict[str, list[Path]]] = {}
    for lang in languages_with_audio():
        tables[lang.code] = parse_banks_xml(lang)
        bank_name_to_files[lang.code] = map_bank_name_to_files(audio_root / lang.audio_dir_name)

    voices = parse_role_voice()
    result: dict[int, Voice] = {}
    for k, voice in voices.items():
        path = voice.path
        files: dict[str, str] = {}
        failed = False
        for lang in languages_with_audio():
            if lang != ENGLISH:
                event_file = audio_event_root_cn / f"{path}.json"
            else:
                event_file = audio_event_root_global / f"{path}.json"
            audio_file = find_audio_file(event_file, tables[lang.code], bank_name_to_files[lang.code])
            if lang == CHINESE and audio_file is None:
                failed = True
                break
            if audio_file is None:
                audio_file = ""
            files[lang.code] = audio_file
        if failed:
            continue
        voice.file = files
        result[k] = voice
    return result


def match_custom_triggers(voices: list[Voice]) -> list[Trigger]:
    triggers: dict[str, Trigger] = {}

    def make_trigger(key, names: dict[str, str], type: VoiceType):
        triggers[key] = Trigger(
            id=int(key),
            name=names,
            description=names,
            role_id=0,
            type=type,
        )

    for voice_type, table in voice_conversion_table.items():
        for key, names in table.items():
            names_dict = dict(zip(table_languages, names))
            make_trigger(key, names_dict, voice_type)

    voice_found: set[tuple] = set()

    for v in voices:
        ids = tuple(v.id)
        if ids in voice_found:
            continue
        voice_found.add(ids)
        digits = v.path_digits()
        if digits is None:
            continue
        if digits in triggers:
            triggers[digits].voices.append(v)
    return list(triggers.values())

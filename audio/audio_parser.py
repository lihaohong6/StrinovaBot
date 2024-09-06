import re
from dataclasses import dataclass, fields, field
from enum import Enum
from pathlib import Path

from audio.data.conversion_table import VoiceType, voice_conversion_table
from utils.asset_utils import audio_event_root, audio_root, wav_root_cn, wav_root_jp
from utils.general_utils import load_json, get_game_json, get_table


class VoiceUpgrade(Enum):
    REGULAR = ""
    ORG = "org"
    RED = "red"


@dataclass
class Voice:
    id: list[int]
    role_id: int = -1
    quality: int = -1
    title_cn: str = ""
    title_en: str = ""
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


def find_audio_file(file_name: str, table: dict, bank_name_to_files: dict[str, list[Path]]) -> str | None:
    assert len(table) > 0
    event_file = audio_event_root / f"{file_name}.json"
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
                      title_cn=name_cn.strip(),
                      title_en=name_en.strip(),
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

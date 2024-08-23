import re

import json
import os
import subprocess
from dataclasses import dataclass, fields, field
from pathlib import Path

from conversion_table import VoiceType
from global_config import char_id_mapper, internal_names
from utils.asset_utils import audio_root, audio_event_root, wav_root
from conversion_table import voice_conversion_table
from utils.general_utils import get_table, get_game_json


def audio_convert():
    output_root = Path("files/audio")
    output_root.mkdir(exist_ok=True, parents=True)
    for file in audio_root.rglob("*.txtp"):
        file_name = file.name
        out_path = output_root.joinpath(file.relative_to(audio_root))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path = out_path.parent.joinpath(file_name.replace(".txtp", ".wav"))
        subprocess.call(["vgmstream-cli.exe", file, "-o", out_path], stdout=open(os.devnull, 'wb'))


@dataclass
class Voice:
    id: list[int]
    role_id: int
    quality: int
    name_cn: str = ""
    name_en: str = ""
    text_cn: str = ""
    text_en: str = ""
    text_jp: str = ""
    path: str = ""
    file: str = ""

    def merge(self, o: "Voice"):
        assert self.file == o.file and self.path == o.path
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
    title_cn: str = ""
    title_en: str = ""
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


sid_to_ix: dict[str, str] = {}
bank_name_to_files: dict[str, list[Path]] = {}


def find_audio_file(file_name: str) -> str | None:
    assert len(sid_to_ix) > 0
    event_file = audio_event_root / f"{file_name}.json"
    if not event_file.exists():
        # print(event_file.name + " does not exist")
        return None
    data = json.load(open(event_file, "r", encoding="utf-8"))["Properties"]
    bank_name = data["RequiredBank"]["ObjectName"].split("'")[1]
    short_id = str(data["ShortID"])
    if short_id not in sid_to_ix:
        # print(f"Short ID {short_id} is not in conversion table")
        return None
    ix = int(sid_to_ix[short_id])
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


def parse_banks_xml():
    cn_bank_file = audio_root / "banks/cn_banks.xml"
    assert cn_bank_file.exists()
    lines = open(cn_bank_file, "r", encoding="utf-8").readlines()
    ix = None
    sid = None
    for line in lines:
        if "ix=" in line:
            ix = re.search(r'ix="(\d+)"', line).group(1)
        if 'ty="sid"' in line:
            sid = re.search(r'va="(\d+)"', line).group(1)
            if ix is not None:
                sid_to_ix[sid] = ix


def map_bank_name_to_files(p: Path):
    for f in p.iterdir():
        bank_name = f.name.split("-")[0]
        if bank_name not in bank_name_to_files:
            bank_name_to_files[bank_name] = []
        bank_name_to_files[bank_name].append(f)


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
    parse_banks_xml()
    map_bank_name_to_files(wav_root)
    i18n = get_game_json()['RoleVoice']
    voice_table = get_table("RoleVoice")

    voices = {}
    for k, v in voice_table.items():
        content_cn, content_en, name_cn, name_en = get_text(i18n, v)

        path = v["AkEvent"]["AssetPathName"].split(".")[-1]
        file = find_audio_file(path)
        if file is None:
            continue

        voice = Voice(id=[k],
                      role_id=v['RoleId'],
                      quality=v['Quality'],
                      name_cn=name_cn,
                      name_en=name_en,
                      text_cn=content_cn,
                      text_en=content_en,
                      path=path,
                      file=file)
        voices[k] = voice
    return voices


def match_custom_triggers(voices: list[Voice]) -> list[Trigger]:
    triggers: dict[str, Trigger] = {}

    def make_trigger(key, name, type: VoiceType):
        triggers[key] = Trigger(
            id=int(key),
            name_cn=name,
            description_cn=name,
            description_en="",
            role_id=0,
            type=type,
        )

    for voice_type, table in voice_conversion_table.items():
        for key,name in table.items():
            make_trigger(key, name, voice_type)

    for v in voices:
        digits = re.search(r"(\d{3})(_|$)", v.path)
        if digits is None:
            continue
        digits = digits.group(1)
        if digits in triggers:
            triggers[digits].voices.append(v)
    return list(triggers.values())


def pick_string(a: str, b: str) -> str:
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
    if a == "":
        return b
    return a


def make_table(triggers: list[Trigger], char_id: int):
    result = ['<table class="wikitable">']
    for t in triggers:
        for voice in t.voices:
            if voice.role_id != 0 and voice.role_id != char_id:
                continue
            title = pick_string(pick_string(voice.name_en, voice.name_cn),
                                pick_string(t.description_en, t.description_cn))
            translation_cn = ""
            if voice.text_en != "":
                translation_cn = "<br/>" + voice.text_en

            result.append(
                f'<tr>'
                f'<td rowspan="2">{title}</td>'
                f'<td>Chinese</td>'
                f'<td>[[File:{voice.file}]]</td>'
                f'<td>{voice.text_cn}{translation_cn}</td>'
                f'</tr>')
            result.append(
                f'<tr>'
                f'<td>Japanese</td>'
                f'<td>[[File:{voice.file_jp}]]</td>'
                f'<td>{voice.text_jp}</td>'
                f'</tr>'
            )
    result.append('</table>')
    return "\n".join(result)


def make_character_audio_page(triggers: list[Trigger], char_id: int):
    result = []
    for voice_type in VoiceType:
        result.append(f"=={voice_type.value}==")
        table = make_table([t for t in triggers if t.type.value == voice_type.value],
                           char_id)
        result.append(table)
        result.append("")
    print("\n".join(result))


def parse_system_voice():
    """
    InGameSystemVoiceTrigger.json
    InGameSystemVoiceUpgrade.json (for Kanami)
    Files with prefix "Vox_Communicate"
    :return:
    """
    pass


def make_character_audio_pages():
    voices = role_voice()
    triggers = dict((t.id, t) for t in in_game_triggers())
    upgrades = in_game_triggers_upgrade()
    for upgrade in upgrades:
        if upgrade.trigger not in triggers:
            continue
        triggers[upgrade.trigger].children.append(upgrade)
    custom_triggers = match_custom_triggers(list(voices.values()))
    all_triggers = list(triggers.values()) + custom_triggers
    result = []
    for t in all_triggers:
        for voice_id in t.voice_id:
            if voice_id not in voices:
                break
            t.voices.append(voices[voice_id])
        else:
            result.append(t)
    for char_id, char_name in char_id_mapper.items():
        make_character_audio_page(result, char_id)
        break


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
                os.startfile(wav_root / v.file)


def main():
    test_audio()


if __name__ == "__main__":
    main()

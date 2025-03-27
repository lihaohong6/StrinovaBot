import pickle
import re
from dataclasses import dataclass, fields, field
from functools import cache
from pathlib import Path

from bs4 import BeautifulSoup

from audio.audio_utils import audio_is_silent
from audio.data.conversion_table import VoiceType, voice_conversion_table, table_languages
from audio.voice import VoiceUpgrade, Voice
from utils.asset_utils import audio_root, audio_event_root_global, global_export_root, global_wem_root
from utils.json_utils import load_json, get_all_game_json, get_table, get_table_global
from utils.lang import CHINESE, Language, languages_with_audio
from utils.lang_utils import get_multilanguage_dict


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
    for candidate in candidates:
        assert candidate.exists()
        return candidate.name
    return None


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


@cache
def parse_banks_xml(lang: Language | str):
    if isinstance(lang, Language):
        lang = lang.code
    sid_to_ix = {}
    bank_file = audio_root / f"banks/{lang}_banks.xml"
    parse_bank(bank_file, sid_to_ix)
    return sid_to_ix


cached_soup = None


def parse_bgm_banks_xml():
    global cached_soup
    from bs4 import BeautifulSoup
    if cached_soup is None:
        bank_file = audio_root / f"banks/cn_banks.xml"
        with open(bank_file, "r", encoding="utf-8") as f:
            text = f.read()
        cached_soup = BeautifulSoup(text, "xml")
    return cached_soup

fld_cache = None

def get_fld(soup: BeautifulSoup):
    global fld_cache
    if fld_cache is None:
        result: dict[str, dict[int, BeautifulSoup]] = {}
        for fld in soup.find_all("fld"):
            na = fld.attrs.get("na")
            if na not in {"key", "DirectParentID"}:
                continue
            if na not in result:
                result[na] = {}
            result[na][int(fld.attrs.get("va"))] = fld
        fld_cache = result
    return fld_cache


bgm_cache: dict[int, Path] = {}


def get_bgm_file_by_event_id(event_id: int) -> Path | None:
    global bgm_cache
    bgm_cache_location = Path("files/cache/bgm/table.pickle")
    if len(bgm_cache) == 0 and bgm_cache_location.exists():
        with open(bgm_cache_location, "rb") as f:
            bgm_cache = pickle.load(f)
    if event_id in bgm_cache:
        return bgm_cache[event_id]
    soup = parse_bgm_banks_xml()
    fld_table = get_fld(soup)
    try:
        target = fld_table["key"][event_id]
        sibling = target.parent.find("fld", attrs={"na": "audioNodeId"})
        va = sibling.attrs["va"]
        parent = fld_table["DirectParentID"][int(va)].parent.parent.parent.parent
        sibling = parent.find("fld", attrs={"na": "ulID"})
        va = sibling.attrs["va"]
        parent = fld_table["DirectParentID"][int(va)].parent.parent
        target = parent.find("obj", attrs={"na": "AkMediaInformation"}).find("fld", attrs={"na": "sourceID"})
        audio_id = target.attrs["va"]
    except Exception as e:
        print(f"Could not find event {event_id}: {e}")
        return None
    result_path = global_wem_root / "Wem" / "BGM_Date" / f"{audio_id}.wem"
    bgm_cache[event_id] = result_path
    bgm_cache_location.parent.mkdir(parents=True, exist_ok=True)
    with open(bgm_cache_location, "wb") as f:
        pickle.dump(bgm_cache, f)
    return result_path


@cache
def map_bank_name_to_files(p: Path) -> dict[str, list[Path]]:
    table = {}
    for f in p.iterdir():
        bank_name = f.name.split("-")[0]
        if bank_name not in table:
            table[bank_name] = []
        table[bank_name].append(f)
    return table


def get_audio_text(i18n: dict[str, dict], v) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, str]]]:
    name_obj = v['VoiceName']
    key = name_obj.get("Key", None)
    title: dict[str, str] = get_multilanguage_dict(i18n, key, "",
                                                   extra="" if key is None else name_obj["SourceString"])

    content_obj = v['Content']
    key = content_obj.get("Key", None)
    content = get_multilanguage_dict(i18n, key, "",
                                     extra="" if key is None else content_obj["SourceString"])

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
        description = get_audio_text(i18n, v['Desc'])
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
    voice_table = get_table_global("RoleVoice")

    voices = {}
    path_to_voice: dict[str, Voice] = {}
    for k, v in voice_table.items():
        name, transcription, translation = get_audio_text(i18n, v)

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
        failed = True
        for lang in languages_with_audio():
            event_file = audio_event_root_global / f"{path}.json"
            # FIXME: should source CN events too (as a bonus)
            # event_file = audio_event_root / f"{path}.json"
            audio_file = find_audio_file(event_file, tables[lang.code], bank_name_to_files[lang.code])
            if audio_file is None:
                audio_file = ""
            else:
                failed = False
            files[lang.code] = audio_file
        if failed:
            continue
        voice.file = files
        result[k] = voice
    return result


def apply_trigger_fix(triggers: list[Trigger]) -> None:
    """
    Another attempt at fixing the issue in https://github.com/bnnm/wwiser/issues/49
    An attempt has been made to reorder the bnk files, but a few bnk files contain a ton of audio files
    that include both originals and org/red. The internal names are all gibberish, so can't
    use internal names to sort them. This function detects this situation and lets the base voice steal
    the file of the derived event.
    """
    dont_steal_list = {"HuiXing.*066_org", "Lawine.*067_red", "Fuchsia.*066_red"}
    for t in triggers:
        if t.id not in [66, 67]:
            continue
        base_voice: dict[str, Voice] = {}
        extra_voice: dict[str, list[Voice]] = {}
        for v in t.voices:
            role_id = v.role_id
            key = f"{role_id}"
            is_derived = ("_org" in v.path or "_red" in v.path) and "_original" not in v.path
            if is_derived:
                if key not in extra_voice:
                    extra_voice[key] = []
                extra_voice[key].append(v)
            else:
                assert key not in base_voice
                base_voice[key] = v
        for key, voice in base_voice.items():
            if key not in extra_voice:
                continue
            for derived in extra_voice[key]:
                if any(re.search(l, derived.path) is not None for l in dont_steal_list):
                    continue
                for lang, file_path in derived.file.items():
                    # If the derived file is nonempty but the base file is empty, then steal it.
                    if voice.file.get(lang, "") == "" and file_path != "":
                        voice.file[lang] = file_path
                        derived.file[lang] = ""


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
        # FIXME: temporary patch to prevent birthday lines (e.g. Vox_Audrey_Birthday_001) from interfering
        #  with regular lines
        if re.search(r"(_Date|Birthday_)\d{2,3}", v.path) is not None or "_TeamGuide_" in v.path:
            continue
        digits = v.path_digits()
        if digits is None:
            continue
        if digits in triggers:
            triggers[digits].voices.append(v)

    result = list(triggers.values())
    apply_trigger_fix(result)
    return result



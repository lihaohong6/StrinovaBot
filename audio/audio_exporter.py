import os
import random
import re
import shutil
import string
import subprocess
from dataclasses import dataclass
from enum import Enum
from functools import cache
from pathlib import Path

from utils.asset_utils import global_wem_root, global_bnk_root, audio_event_root_global, audio_export_root
from utils.file_utils import temp_file_dir
from utils.json_utils import load_json
from utils.lang import Language


def extract_wem_to_wav(txtp_file: Path, wem_path: Path, output_file: Path) -> None:

    assert txtp_file.exists() and txtp_file.is_file()
    assert wem_path.exists() and wem_path.is_file()

    temp_wem_dir = txtp_file.parent / "wem"
    temp_wem_dir.mkdir(exist_ok=True)
    temp_wem_link = temp_wem_dir / wem_path.name
    if not temp_wem_link.exists():
        os.symlink(wem_path, temp_wem_link)

    vgmstream_cmd = [
        "vgmstream-cli",
        txtp_file.absolute(),
        "-o", output_file.absolute(),
    ]

    # Set working directory to temp directory so vgmstream can find the WEM file
    try:
        result = subprocess.run(
            vgmstream_cmd,
            check=True,
            cwd=txtp_file.parent,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        result.check_returncode()
    except subprocess.CalledProcessError as e:
        print(f"Failed to convert {txtp_file.name} to WAV: {e}")
        return

    if not output_file.exists():
        raise RuntimeError(f"WAV file was not created: {output_file}")


class AudioLanguage(Language):

    def get_export_path(self) -> Path:
        return audio_export_root / self.name

    def get_bnk_path(self):
        if self.code == 'sfx':
            return global_bnk_root
        else:
            return global_bnk_root / self.name

    def get_txtp_path(self):
        path = temp_file_dir / "txtp" / self.code
        return path

class AudioLanguageVariant(Enum):
    ENGLISH = AudioLanguage('en', 'English')
    CHINESE = AudioLanguage('cn', 'Chinese')
    JAPANESE = AudioLanguage('ja', 'Japanese')
    SFX = AudioLanguage('sfx', 'SFX')

def language_from_name(name: str) -> AudioLanguage:
    for variant in AudioLanguageVariant:
        if variant.value.name == name:
            return variant.value
    raise RuntimeError(f"Unknown language: {name}")

def get_audio_languages() -> list[AudioLanguage]:
    return [AudioLanguageVariant.CHINESE.value,
            AudioLanguageVariant.JAPANESE.value,
            AudioLanguageVariant.ENGLISH.value,
            AudioLanguageVariant.SFX.value]


@dataclass
class AudiokineticEvent:
    event_name: str
    bank_name: str
    wem_path: dict[AudioLanguage, list[Path]]


@cache
def parse_audiokinetic_events() -> list[AudiokineticEvent]:
    events = []
    for event_file in audio_event_root_global.iterdir():
        json_data = load_json(event_file)
        event_name = json_data["Name"]
        properties = json_data["Properties"]
        bank_name = properties["RequiredBank"]["ObjectName"].split("'")[1]
        wem_paths: dict[AudioLanguage, list[Path]] = {}
        if "EventCookedData" not in json_data:
            continue
        for language_map in json_data["EventCookedData"]["EventLanguageMap"]:
            lang = language_from_name(language_map["Key"]["LanguageName"])
            medias = language_map["Value"]['Media']
            if len(medias) == 0:
                continue
            paths = []
            for m in medias:
                path_name = m["MediaPathName"]
                debug_name = m["DebugName"]
                if "reverb" in debug_name.lower():
                    continue
                wem_path = global_wem_root / path_name
                paths.append(wem_path)
                assert wem_path.exists() and wem_path.is_file()
            wem_paths[lang] = sorted(paths, key=lambda p: int(p.stem))
        event = AudiokineticEvent(event_name, bank_name, wem_paths)
        events.append(event)
    return events

def path_name_to_priority(p: str) -> int:
    if not p.startswith('Vox'):
        return 3
    if "_original" in p:
        return 0
    if "org" in p or "red" in p:
        return 2
    return 1

def sort_audio_paths(paths: list[Path]) -> None:
    """
    Sort audio paths to prioritize original voice lines over red and org ones.
    See https://github.com/bnnm/wwiser/issues/49

    :param paths: List of bnk files.
    """
    paths.sort(key=lambda p: (path_name_to_priority(p.name), p.name))

def generate_txtp(bnk_path: Path, txtp_path: Path):
    paths = list(Path(bnk_path).glob('*.bnk'))
    sort_audio_paths(paths)
    config_file = temp_file_dir / (''.join(random.choices(string.ascii_uppercase + string.digits, k=15)) + "wwconfig.txt")
    with open(config_file, "w") as f:
        f.write("-g -go ")
        f.write(f'{txtp_path.absolute()} ')
        f.write(" ".join(f'"{str(p.absolute())}"' for p in paths))
    subprocess.run(['python', 'wwiser.pyz', config_file],
                   cwd=audio_export_root,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL,
                   check=True)
    config_file.unlink()

def wem_to_wav(wem_path: Path, wav_path: Path):
    subprocess.run(['vgmstream-cli', wem_path.absolute(), "-o", wav_path.absolute()],
                   cwd=audio_export_root,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL,
                   check=True)


def export_audiokinetic_events(events: list[AudiokineticEvent]):
    prep_export()

    lang_and_wem_id_to_txtp = map_wem_id_to_txtp()

    events.sort(key=lambda e: path_name_to_priority(e.event_name))
    visited_wem_ids: dict[str, set[str]] = {}
    for lang in get_audio_languages():
        visited_wem_ids[lang.code] = set()

    for event in events:
        for lang, wem_path_list in event.wem_path.items():
            audio_parent_dir = lang.get_export_path()
            wav_file_path = audio_parent_dir / f"{event.event_name}.wav"
            wem_path_list = [w for w in wem_path_list if w.stem not in visited_wem_ids[lang.code]]
            if len(wem_path_list) == 0:
                print(f"All wems exhausted for {event.event_name} ({lang.code})")
                continue
            for wem_path in wem_path_list:
                wem_id = wem_path.stem
                txtp_file = lang_and_wem_id_to_txtp[lang.code].get(wem_id, None)
                if txtp_file is None:
                    continue
                visited_wem_ids[lang.code].add(wem_id)
                extract_wem_to_wav(txtp_file, wem_path, wav_file_path)
                break
            else:
                assert not wav_file_path.exists()
                wem_path = wem_path_list[0]
                visited_wem_ids[lang.code].add(wem_path.stem)
                print(f"No txtp file found. Converting {wem_path.name} straight to {wav_file_path.name}.")
                wem_to_wav(wem_path, wav_file_path)

            # apply Kanami fix: copy from sfx to CN/JP directory
            if lang.code == AudioLanguageVariant.SFX.value.code and "Communicate_Kanami" in event.event_name:
                new_lang = AudioLanguageVariant.JAPANESE.value if "JP" in event.event_name else AudioLanguageVariant.CHINESE.value
                new_wav_path = new_lang.get_export_path() / f"{event.event_name.replace('_JP', '')}.wav"
                shutil.copy(wav_file_path, new_wav_path)



def prep_export():
    # export txtp
    for lang in get_audio_languages():
        txtp_path = lang.get_txtp_path()
        shutil.rmtree(txtp_path, ignore_errors=True)
        txtp_path.mkdir(parents=True, exist_ok=True)
        generate_txtp(lang.get_bnk_path(), txtp_path)

    for lang in get_audio_languages():
        p = lang.get_export_path()
        shutil.rmtree(p, ignore_errors=True)
        p.mkdir(parents=True, exist_ok=True)


def map_wem_id_to_txtp():
    lang_and_wem_id_to_txtp: dict[str, dict[str, Path]] = {}
    for lang in get_audio_languages():
        txtp_path = lang.get_txtp_path()
        files = list(txtp_path.glob("*.txtp"))
        files.sort(key=lambda p: p.name)
        wem_id_to_txtp: dict[str, Path] = {}
        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            matches = re.findall(r"(\d+)\.wem", content)
            if len(matches) != 1:
                continue
            wem_id = matches[0]
            if wem_id not in wem_id_to_txtp:
                wem_id_to_txtp[wem_id] = file
        lang_and_wem_id_to_txtp[lang.code] = wem_id_to_txtp
    return lang_and_wem_id_to_txtp


def main():
    events = parse_audiokinetic_events()
    export_audiokinetic_events(events)


if __name__ == "__main__":
    main()
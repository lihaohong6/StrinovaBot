import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from functools import cache
from pathlib import Path

from utils.asset_utils import global_wem_root, global_bnk_root, audio_event_root_global, audio_root
from utils.file_utils import temp_file_dir
from utils.json_utils import load_json
from utils.lang import Language


def extract_wem_to_wav(bnk_path: Path, wem_path: Path, output_file: Path) -> None:

    assert bnk_path.exists() and bnk_path.is_file()
    assert wem_path.exists() and wem_path.is_file()
    if output_file.exists():
        return
    # Get WEM file ID from filename (assuming format like "123456.wem")
    wem_id = wem_path.stem
    # Step 1: Convert BNK to TXTP using wwiser
    print(f"Converting BNK file to TXTP: {bnk_path.name}")
    txtp_dir = temp_file_dir / "txtp"
    shutil.rmtree(txtp_dir, ignore_errors=True)
    txtp_dir.mkdir(exist_ok=True)

    # Run wwiser to extract TXTP files
    wwiser_cmd = [
        "python",
        "wwiser.pyz",
        str(bnk_path),
        "-go", str(txtp_dir),
        "--txtp"
    ]

    result = subprocess.run(wwiser_cmd, check=True, cwd=audio_root,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result.check_returncode()

    # Step 2: Find the relevant TXTP file that references our WEM
    matching_txtp = None
    for txtp_file in txtp_dir.glob("*.txtp"):
        with open(txtp_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for the WEM ID in the TXTP content
            if wem_id in content or wem_path.name in content:
                matching_txtp = txtp_file
                break

    if matching_txtp is None:
        # Fallback: try to convert WEM directly if no TXTP match found
        print(f"No matching TXTP found for WEM {wem_id}, trying direct conversion")
        raise RuntimeError(f"No matching TXTP found for WEM {wem_id}")
        # _convert_wem_directly(wem_path, output_file)

    temp_wem_dir = txtp_dir / "wem"
    temp_wem_dir.mkdir(exist_ok=True)
    temp_wem_link = temp_wem_dir / wem_path.name
    os.symlink(wem_path, temp_wem_link)

    print(f"Converting to WAV: {matching_txtp.name}")
    vgmstream_cmd = [
        "vgmstream-cli",
        matching_txtp.absolute(),
        "-o", output_file.absolute(),
    ]

    # Set working directory to temp directory so vgmstream can find the WEM file
    try:
        result = subprocess.run(
            vgmstream_cmd,
            check=True,
            cwd=txtp_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        result.check_returncode()
    except subprocess.CalledProcessError as e:
        print(f"Failed to convert {matching_txtp.name} to WAV: {e}")
        return

    if not output_file.exists():
        raise RuntimeError(f"WAV file was not created: {output_file}")

    print(f"Successfully converted to: {output_file}")


class AudioLanguage(Enum):
    ENGLISH = "English"
    CHINESE = "Chinese"
    JAPANESE = "Japanese"
    SFX = "SFX"

    @property
    def code(self):
        if self == AudioLanguage.ENGLISH:
            return 'en'
        if self == AudioLanguage.CHINESE:
            return 'zh'
        if self == AudioLanguage.JAPANESE:
            return 'ja'
        if self == AudioLanguage.SFX:
            return 'sfx'
        raise RuntimeError(f"Unknown language: {self}")

    def get_export_path(self) -> Path:
        return audio_root / self.value

    def get_bnk_path(self, bnk_name):
        if self == AudioLanguage.SFX:
            root = global_bnk_root
        else:
            root = global_bnk_root / self.value
        return root / (bnk_name + ".bnk")

def create_audio_language(lang: Language) -> AudioLanguage:
    mapper = {
        'en': AudioLanguage.ENGLISH,
        'zh': AudioLanguage.CHINESE,
        'ja': AudioLanguage.JAPANESE
    }
    return mapper[lang.code]


def init_language_export_directories():
    for lang in AudioLanguage:
        p = lang.get_export_path()
        p.mkdir(parents=True, exist_ok=True)


@dataclass
class AudiokineticEvent:
    event_name: str
    bank_name: str
    wem_path: dict[AudioLanguage, Path]


@cache
def parse_audiokinetic_events() -> list[AudiokineticEvent]:
    events = []
    for event_file in audio_event_root_global.iterdir():
        json_data = load_json(event_file)
        event_name = json_data["Name"]
        properties = json_data["Properties"]
        bank_name = properties["RequiredBank"]["ObjectName"].split("'")[1]
        wem_paths: dict[AudioLanguage, Path] = {}
        if "EventCookedData" not in json_data:
            continue
        for language_map in json_data["EventCookedData"]["EventLanguageMap"]:
            lang = AudioLanguage(language_map["Key"]["LanguageName"])
            medias = language_map["Value"]['Media']
            if len(medias) == 0:
                continue
            path_name = medias[0]["MediaPathName"]
            wem_path = global_wem_root / path_name
            assert wem_path.exists() and wem_path.is_file()
            wem_paths[lang] = wem_path
        event = AudiokineticEvent(event_name, bank_name, wem_paths)
        events.append(event)
    return events


def export_audiokinetic_events(events: list[AudiokineticEvent]):
    for event in events:
        for lang, wem_path in event.wem_path.items():
            bnk_file = lang.get_bnk_path(event.bank_name)
            assert bnk_file.exists() and bnk_file.is_file()
            audio_parent_dir = lang.get_export_path()
            extract_wem_to_wav(bnk_file, wem_path, audio_parent_dir / f"{event.event_name}.wav")


def main():
    events = parse_audiokinetic_events()
    export_audiokinetic_events(events)


if __name__ == "__main__":
    init_language_export_directories()
    main()
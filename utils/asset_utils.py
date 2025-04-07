import platform
from pathlib import Path

def ensure_exists(path: Path):
    assert path.exists(), (f"Please ensure that {path} exists. If you are running this program on a different machine,"
                           f"consider changing hard-coded paths to ones that fit your own machine.")

strinova_root = Path(r"D:\Strinova")

if platform.system() != "Windows":
    strinova_root = Path("/mnt/ssd1/Strinova")

ensure_exists(strinova_root)

# cn export
cn_export_root = strinova_root / "AutoUnpack/CNExport"
json_root = strinova_root / "Strinova-data/CN"
csv_root = json_root / "CSV"
wem_root = cn_export_root / 'WwiseAudio' / 'Windows'
string_table_root = json_root / "CyTable" / "StringTable"
resource_root = cn_export_root / "DynamicResource"
# at the very least, json files should be accessible
ensure_exists(csv_root)

# global export
global_export_root = strinova_root / "AutoUnpack/GLExport"
global_json_root = strinova_root / "Strinova-data/Global"
global_csv_root = global_json_root / "CSV"
global_wem_root = global_export_root / 'WwiseAudio' / 'Windows'
localization_root = global_json_root / "Localization/Game"
global_resources_root = global_export_root / "DynamicResource"
# at the very least, localizations should be accessible
ensure_exists(localization_root)

# audio
audio_root = Path("audio/audio_export")
audio_event_root_cn = json_root / r"WwiseAssets\AkEvent"
audio_event_root_global = global_json_root / r"WwiseAssets\AkEvent"
wav_root_cn = audio_root / "Chinese"
wav_root_jp = audio_root / "Japanese"
wav_root_en = audio_root / "English"
wav_root_sfx = audio_root / "sfx"

def main():
    pass


if __name__ == '__main__':
    main()


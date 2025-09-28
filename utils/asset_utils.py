import platform
from pathlib import Path

def ensure_exists(path: Path):
    assert path.exists(), (f"Please ensure that {path} exists. If you are running this program on a different machine,"
                           f"consider changing hard-coded paths to ones that fit your own machine.")

is_bulb_machine = False

if platform.system() != "Windows":
    strinova_root = Path("/mnt/ssd1/Strinova")
else:
    strinova_root = Path(r"D:\Strinova")
    if not strinova_root.exists():
        # On Bulb's machine
        is_bulb_machine = True
        strinova_root = Path(r"C:\StrinovaUnpack")

ensure_exists(strinova_root)

# cn export
cn_export_root = strinova_root / "AutoUnpack/CNExport"
json_root = strinova_root / "Strinova-data/CN"
csv_root = json_root / "CSV"
wem_root = cn_export_root / 'WwiseAudio'
string_table_root = json_root / "CyTable" / "StringTable"
resource_root = cn_export_root / "DynamicResource"
# at the very least, json files should be accessible
ensure_exists(csv_root)

# global export
global_export_root = strinova_root / "AutoUnpack/GLExport"
global_json_root = strinova_root / "Strinova-data/GL"
global_csv_root = global_json_root / "CSV"
global_wem_root = global_export_root / 'WwiseAudio'
global_bnk_root = global_wem_root
localization_root = global_json_root / "Localization/Game"
global_resources_root = global_export_root / "DynamicResource"
# at the very least, localizations should be accessible
ensure_exists(localization_root)

# audio
audio_export_root = Path("audio/audio_export")
audio_event_root_cn = json_root / "WwiseAssets" / "AkEvent"
audio_event_root_global = global_json_root / "WwiseAssets" / "AkEvent"
wav_root_cn = audio_export_root / "Chinese"
wav_root_jp = audio_export_root / "Japanese"
wav_root_en = audio_export_root / "English"
wav_root_sfx = audio_export_root / "sfx"

def main():
    ensure_exists(csv_root)
    ensure_exists(global_csv_root)
    ensure_exists(resource_root)
    ensure_exists(global_resources_root)


if __name__ == '__main__':
    main()


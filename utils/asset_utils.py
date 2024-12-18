import platform
from pathlib import Path

strinova_root = Path(r"D:\Strinova")

if platform.system() != "Windows":
    strinova_root = Path("/mnt/ssd1/Strinova")

# cn export
cn_export_root = strinova_root / "AutoUnpack/CNExport"
json_root = strinova_root / "Strinova-data/CN"
csv_root = json_root / "CSV"
string_table_root = csv_root / ".." / "CyTable" / "StringTable"
resource_root = cn_export_root / "DynamicResource"

# global export
global_export_root = strinova_root / "AutoUnpack/GLExport"
global_json_root = strinova_root / "Strinova-data/Global"
global_csv_root = global_json_root / "CSV"
localization_root = global_json_root / "Localization/Game"

# audio
audio_root = cn_export_root / "../audio"
audio_event_root_cn = json_root / r"WwiseAssets\AkEvent"
audio_event_root_global = global_json_root / r"WwiseAssets\AkEvent"
wav_root_cn = audio_root / "Chinese"
wav_root_jp = audio_root / "Japanese"
wav_root_en = audio_root / "English"


def main():
    pass


if __name__ == '__main__':
    main()


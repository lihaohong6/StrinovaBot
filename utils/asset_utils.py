from pathlib import Path

# cn export
cn_export_root = Path(r"D:\Strinova\AutoUnpack\CNExport")
csv_root = Path(r"D:\Strinova\Strinova-data\CN\CSV")
resource_root = cn_export_root / "DynamicResource"
audio_root = cn_export_root / "../audio"
audio_event_root = cn_export_root / r"WwiseAssets\AkEvent"
wav_root_cn = audio_root / "Chinese"
wav_root_jp = audio_root / "Japanese"
wav_root_en = audio_root / "English"

# global export
en_export_root = Path(r"D:\Strinova\AutoUnpack\GLExport")
en_csv_root = Path(r"D:\Strinova\Strinova-data\Global\CSV")
localization_root = Path("D:/Strinova/Strinova-data/Global/Localization/Game")

# non-exported assets
skin_back_root = Path(r"D:\Strinova\Skins Back\result")
portrait_root = Path(r"D:\Strinova\Portrait\result")
local_asset_root = Path(r"D:\Strinova\LocalAssets")


def main():
    pass


if __name__ == '__main__':
    main()


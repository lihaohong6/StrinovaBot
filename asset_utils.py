import os
import subprocess
from pathlib import Path

from pywikibot import FilePage, Site
from pywikibot.site._upload import Uploader

s = Site()
resource_root = Path(r"D:\ProgramFiles\FModel\output\Exports\PM\Content\PaperMan\UI\Atlas\DynamicResource")
portrait_root = Path(r"D:\Strinova\Portrait\result")
audio_root = Path(r"D:\Strinova\CNExport\Exports\PM\Content\WwiseAudio\Windows")
skin_back_root = Path(r"D:\Strinova\Skins Back\result")


def upload_weapon(char_name: str, weapon_id: int):
    weapons_root = resource_root / r"Weapon\InGameGrowth"
    weapon_path = weapons_root / f"T_Dynamic_InGameGrowth_{weapon_id}.png"
    p = FilePage(s, f"File:{char_name} GrowthWeapon.png")
    if p.exists():
        return
    if not weapon_path.exists():
        print(f"File for weapon {weapon_id} of {char_name} does not exist")
    Uploader(s, p, source_filename=str(weapon_path),
             text="[[Category:Weapon growth images]]", comment="upload from game assets").upload()


def upload_item(item_id: int | str, cat: str):
    path = resource_root / f"Item/ItemIcon/T_Dynamic_Item_{item_id}.png"
    assert path.exists()
    p = FilePage(s, f"File:Item Icon {item_id}.png")
    if p.exists():
        return
    Uploader(s, p,
             source_filename=str(path),
             text=f"[[Category:{cat}]]",
             comment="upload from game assets").upload()


def audio_convert():
    output_root = Path("files")
    output_root.mkdir(exist_ok=True)
    for file in audio_root.rglob("*.bnk"):
        file_name = file.name
        out_path = output_root.joinpath(file.relative_to(audio_root))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path = out_path.parent.joinpath(file_name.replace(".bnk", ".wav"))
        subprocess.call(["vgmstream-cli.exe", file, "-o", out_path], stdout=open(os.devnull, 'wb'))


def main():
    audio_convert()


if __name__ == '__main__':
    main()

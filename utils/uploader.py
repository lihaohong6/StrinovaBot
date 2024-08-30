import re
from dataclasses import dataclass
from pathlib import Path

from pywikibot import Site, FilePage
from pywikibot.pagegenerators import PreloadingGenerator
from pywikibot.site._apisite import APISite
from pywikibot.site._upload import Uploader

from utils.asset_utils import resource_root

s: APISite = Site()


def upload_skill_demo():
    url = "https://klbq-web-cdn.strinova.com/www/video/CharactersSkillVideos/{}/{}/{}{}.mp4"
    factions = {
        "TheScissors": ["Lawine", "Reiichi", "Meredith", "Ming", "Kanami"],
        "Urbino": ["Fuchsia", "Astierred", "Audrey", "BaiMo", "Maddelena"],
        "PaintingUtopiaSecurity": ['Michele', "Nobunaga", "Kokona", "Yvette"]
    }
    name_map = {
        "Astierred": "Celestia",
        "BaiMo": "Bai Mo"
    }
    temp_path = Path("temp.mp4")
    for faction, names in factions.items():
        for name in names:
            for number in range(1, 4):
                target_name = name_map.get(name, name)
                target_file = FilePage(s, f"File:{target_name} Skill{number}.mp4")
                if target_file.exists():
                    continue

                source = url.format(faction, name, name, number)
                if name == "Michele":
                    number_mapper = {1: "-Q", 2: "-2", 3: "-X"}
                    source = url.format(faction, name, name, number_mapper[number])
                # download_file(source, temp_path)
                # converted_file = Path("o.webm")
                # subprocess.run([shutil.which("ffmpeg"), "-i", temp_path, converted_file, "-y"], shell=True, check=True)
                Uploader(s, target_file, source_url=str(source),
                         comment="batch upload skill videos",
                         text="Video from official site\n\n[[Category:Skill demos]]",
                         ignore_warnings=True).upload()


def upload_item_icons(items: list[int | str], text: str = "[[Category:Item icons]]",
                      summary: str = "batch upload item icons", ):
    lst: list[UploadRequest] = []
    for item in items:
        lst.append(UploadRequest(resource_root / f"Item/ItemIcon/T_Dynamic_Item_{item}.png",
                                 FilePage(s, f"File:Item Icon {item}.png"),
                                 text,
                                 summary))
    process_uploads(lst)


def upload_local():
    p = Path("../files")
    for f in p.rglob("*.ogg"):
        target_file = FilePage(s, "File:" + f.name)
        if target_file.exists():
            continue
        Uploader(s, target_file, source_filename=str(f), comment="batch upload music",
                 text="[[Category:Character BGM]]").upload()


def upload_file(text: str, target: FilePage, summary: str = "batch upload file",
                file: str | Path = None, url: str = None):
    force = False
    while True:
        try:
            if url is not None:
                Uploader(s, target, source_url=url, text=text, comment=summary, ignore_warnings=force).upload()
            if file is not None:
                Uploader(s, target, source_filename=str(file), text=text, comment=summary,
                         ignore_warnings=force).upload()
            return
        except Exception as e:
            search = re.search(r"duplicate of \['([^']+)'", str(e))
            if 'already exists' in str(e):
                return
            if "http-timed-out" in str(e):
                continue
            if "was-deleted" in str(e):
                force = True
                continue
            assert search is not None, str(e)
            target.set_redirect_target(FilePage(s, f"File:{search.group(1)}"), create=True)
            return


def main():
    pass


if __name__ == '__main__':
    main()


def upload_weapon(char_name: str, weapon_id: int) -> bool:
    weapons_root = resource_root / r"Weapon\InGameGrowth"
    weapon_path = weapons_root / f"T_Dynamic_InGameGrowth_{weapon_id}.png"
    p = FilePage(s, f"File:{char_name} GrowthWeapon.png")
    if p.exists():
        return True
    if not weapon_path.exists():
        print(f"File for weapon {weapon_id} of {char_name} does not exist")
        return False
    Uploader(s, p, source_filename=str(weapon_path),
             text="[[Category:Weapon growth images]]", comment="upload from game assets").upload()
    return True


@dataclass
class UploadRequest:
    source: Path | str
    target: FilePage
    text: str
    comment: str = "batch upload file"


def process_uploads(requests: list[UploadRequest]) -> None:
    existing = set(p.title() for p in PreloadingGenerator((r.target for r in requests)) if p.exists())
    for r in requests:
        if r.target.title() in existing:
            continue
        if isinstance(r.source, str):
            upload_file(r.text, r.target, r.comment, url=r.source)
        else:
            assert r.source.exists()
            upload_file(r.text, r.target, r.comment, file=r.source)

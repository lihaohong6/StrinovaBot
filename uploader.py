import re
from pathlib import Path

from pywikibot import Site, FilePage
from pywikibot.pagegenerators import PreloadingGenerator
from pywikibot.site._apisite import APISite
from pywikibot.site._upload import Uploader

from asset_utils import resource_root

s: APISite = Site()


def upload_emotes():
    path = resource_root / "Emote"
    for f in path.glob("*.png"):
        if f.name.startswith("T_Dynamic_Emote_"):
            file_num = re.search(r"\d+", f.name).group(0)
            target = FilePage(s, f"File:Emote_{file_num}.png")
            s.upload(target,
                     source_filename=str(f.absolute()),
                     text='[[Category:Emotes]]', comment='Batch upload emotes')


def upload_achievement_icons():
    path = resource_root / "Achievement"
    for f in path.glob("*.png"):
        if f.name.startswith("T_Dynamic_Achievement_"):
            file_num = re.search(r"\d+", f.name).group(0)
            target = FilePage(s, f"File:Achievement_{file_num}.png")
            Uploader(s, target,
                     source_filename=str(f.absolute()),
                     text='[[Category:Achievement icons]]', comment="Batch upload achievement icons").upload()


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


def upload_item_icons(items: list[int | str], cat: str):
    targets = []
    paths = []
    for item in items:
        path = resource_root / f"Item/ItemIcon/T_Dynamic_Item_{item}.png"
        assert path.exists()
        paths.append(path)
        targets.append(FilePage(s, f"File:Item Icon {item}.png"))
    existing = set(p.title() for p in PreloadingGenerator(targets) if p.exists())
    for index, item in enumerate(items):
        target = targets[index]
        if target.title() in existing:
            continue
        Uploader(s, target, source_filename=str(paths[index]),
                 comment="batch upload items",
                 text=f"[[Category:{cat}]]",
                 ignore_warnings=False).upload()


def upload_local():
    p = Path("files")
    for f in p.glob("*.*"):
        target_file = FilePage(s, "File:" + f.name)
        Uploader(s, target_file, source_filename=str(f), comment="batch upload",
                 text="[[Category:Currency images]]").upload()


def upload_file(text: str, target: FilePage, summary: str = "batch upload file",
                file: str | Path = None, url: str = None):
    while True:
        if target.exists():
            return
        try:
            if url is not None:
                Uploader(s, target, source_url=url, text=text, comment=summary).upload()
            if file is not None:
                Uploader(s, target, source_filename=str(file), text=text, comment=summary).upload()
        except Exception as e:
            search = re.search(r"duplicate of \['([^']+)'", str(e))
            if 'already exists' in str(e):
                return
            if "http-timed-out" in str(e):
                continue
            assert search is not None
            target.set_redirect_target(FilePage(s, f"File:{search.group(1)}"), create=True)


def main():
    upload_achievement_icons()


if __name__ == '__main__':
    main()


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

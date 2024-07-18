import re
import shutil
import subprocess
from pathlib import Path

from pywikibot import Site, FilePage
from pywikibot.site._apisite import APISite
from pywikibot.site._upload import Uploader

from asset_utils import resource_root
from utils import download_file

s: APISite = Site()


def upload_emotes():
    path = resource_root / "Emote"
    for f in path.glob("*.png"):
        if f.name.startswith("T_Dynamic_Emote_"):
            file_num = re.search(r"\d+", f.name).group(0)
            target = FilePage(s, f"File:Emote_{file_num}.png")
            s.upload(target, source_filename=str(f.absolute()), text='[[Category:Emotes]]', comment='Batch upload emotes')


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


def main():
    upload_skill_demo()


if __name__ == '__main__':
    main()

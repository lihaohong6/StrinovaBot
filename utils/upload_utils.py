import re
from dataclasses import dataclass
from pathlib import Path

from pywikibot import FilePage
from pywikibot.pagegenerators import PreloadingGenerator
from pywikibot.site._upload import Uploader

from utils.asset_utils import resource_root, global_resources_root
from utils.wiki_utils import s


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
                      summary: str = "batch upload item icons"):
    lst: list[UploadRequest] = []
    fails: set[int | str] = set()
    for item in items:
        # try upload the big version if it exists, otherwise use small version
        for big in [True, False]:
            folder = "ItemIcon" if not big else "BigIcon"
            file_name = "Item" if not big else "BigItem"
            local_path = f"Item/{folder}/T_Dynamic_{file_name}_{item}.png"
            source = resource_root / local_path
            if not source.exists():
                source = global_resources_root / local_path
            if source.exists():
                break
        if not source.exists():
            print(f"{source} does not exist")
            fails.add(item)
            continue
        lst.append(UploadRequest(source,
                                 FilePage(s, f"File:Item Icon {item}.png"),
                                 text,
                                 summary))
    process_uploads(lst)
    return fails


def upload_file(text: str, target: FilePage, summary: str = "batch upload file",
                file: str | Path = None, url: str = None, force: bool = False,
                ignore_dup: bool = False, redirect_dup: bool = False, move_dup: bool = False):
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
                # print(f"Warning: {target.title(with_ns=True)} was deleted. Reuploading...")
                # force = True
                # continue
                print(f"INFO: {target.title(with_ns=True)} was deleted. Will not reupload.")
                return
            assert search is not None, str(e)
            existing_page = f"File:{search.group(1)}"
            if ignore_dup:
                return
            if redirect_dup:
                target.set_redirect_target(existing_page, create=True, summary="redirect to existing file")
                return
            if move_dup:
                FilePage(s, existing_page).move(
                    target.title(with_ns=True, underscore=True),
                    reason="rename file")
                return
            raise RuntimeError(f"{existing_page} already exists and so {target.title()} is a dup") from e



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
    source: Path | str | FilePage
    target: FilePage | str
    text: str
    comment: str = "batch upload file"


def process_uploads(requests: list[UploadRequest], force: bool = False, **kwargs) -> None:
    for r in requests:
        if isinstance(r.target, str):
            if "File" not in r.target:
                r.target = "File:" + r.target
            r.target = FilePage(s, r.target)
    existing = set(p.title() for p in PreloadingGenerator((r.target for r in requests)) if p.exists())
    for r in requests:
        if r.target.title() in existing:
            continue
        upload_args = [r.text, r.target, r.comment]
        if isinstance(r.source, str):
            upload_file(*upload_args, url=r.source, force=force, **kwargs)
        elif isinstance(r.source, FilePage):
            upload_file(*upload_args, url=r.source.get_file_url(), force=force, **kwargs)
        elif isinstance(r.source, Path):
            assert r.source.exists(), f"File {r.source} does not exist"
            upload_file(*upload_args, file=r.source, force=force, **kwargs)

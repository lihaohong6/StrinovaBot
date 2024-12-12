from pathlib import Path

from pywikibot import Site, FilePage
from pywikibot.pagegenerators import GeneratorFactory
from pywikibot.site._upload import Uploader

from utils.general_utils import download_file, cn_name_to_en

bwiki = Site(code="bwiki")
s = Site()


def default():
    gen = GeneratorFactory(bwiki)
    gen.handle_args(["-cat:角色"])
    gen = gen.getCombinedGenerator(preload=False)
    for page in gen:
        title = page.title()
        file_page = FilePage(bwiki, f'File:{title}-初始立绘.png')
        if not file_page.exists():
            print(f"{file_page.title()} does not exist")
            continue
        url = file_page.get_file_url()
        title = cn_name_to_en(title)
        target_page = FilePage(s, f'File:{title} Default.png')
        Uploader(s, target_page, source_url=url, comment="upload from bwiki", ignore_warnings=True).upload()


def profile():
    gen = GeneratorFactory(bwiki)
    gen.handle_args(["-cat:角色"])
    gen = gen.getCombinedGenerator(preload=False)
    for page in gen:
        title = page.title()
        file_page = FilePage(bwiki, f'File:{title}头像.png')
        if not file_page.exists():
            print(f"{file_page.title()} does not exist")
            continue
        url = file_page.get_file_url()
        title = cn_name_to_en(title)
        target_page = FilePage(s, f'File:{title} Profile.png')
        if not target_page.exists():
            s.upload(target_page, source_url=url, comment="upload from bwiki")


file_dir = Path("files")
file_dir.mkdir(exist_ok=True)


def download_wallpapers():
    wallpaper_dir = file_dir / "wallpapers"
    existing = set(f.name for f in (wallpaper_dir / 'existing').glob("*"))
    gen = GeneratorFactory(bwiki)
    gen.handle_args(["-imagesused:壁纸", "-ns:File"])
    gen = gen.getCombinedGenerator(preload=False)
    for page in gen:
        file_name = page.title(underscore=True, with_ns=False)
        if file_name in existing:
            continue
        target_file = wallpaper_dir / file_name
        # title = page.title(with_ns=True, underscore=True)
        # file_page = FilePage(bwiki, title)
        file_page: FilePage = page
        url = file_page.get_file_url()
        download_file(url, target_file)
        print(f"{file_name} downloaded")


def bwiki_downloader_main(*args):
    download_wallpapers()


if __name__ == "__main__":
    bwiki_downloader_main()

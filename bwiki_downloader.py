from pywikibot import Site, FilePage
from pywikibot.pagegenerators import GeneratorFactory
from pywikibot.site._upload import Uploader

from utils import zh_name_to_en

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
        title = zh_name_to_en(title)
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
        title = zh_name_to_en(title)
        target_page = FilePage(s, f'File:{title} Profile.png')
        if not target_page.exists():
            s.upload(target_page, source_url=url, comment="upload from bwiki")


def skills():
    gen = GeneratorFactory(bwiki)
    gen.handle_args(["-cat:角色"])
    gen = gen.getCombinedGenerator(preload=False)
    for page in gen:
        title = page.title()
        for sequence in range(1, 4):
            file_page = FilePage(bwiki, f'File:{title}技能{sequence}.png')
            if not file_page.exists():
                print(f"{file_page.title()} does not exist")
                continue
            url = file_page.get_file_url()
            en_title = zh_name_to_en(title)
            target_page = FilePage(s, f'File:{en_title} Skill {sequence}.png')
            if not target_page.exists():
                s.upload(target_page, source_url=url, comment="upload from bwiki; own work as User:16635128")


if __name__ == "__main__":
    default()

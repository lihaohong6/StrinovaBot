import filecmp

from pywikibot import Site, FilePage
from pywikibot.pagegenerators import PreloadingGenerator

from char_info.gallery import parse_skin_tables
from utils.file_utils import temp_file_dir
from utils.general_utils import download_file
from utils.wiki_utils import bwiki


def main():
    skins = parse_skin_tables()
    bwiki_pages: dict[int, FilePage] = {}
    pages: dict[int, FilePage] = {}
    for char, skin_list in skins.items():
        for skin in skin_list:
            skin_id = skin.id
            bwiki_title = skin.get_bwiki_portrait_title(char)
            title = skin.get_mh_portrait_title(char)
            bwiki_page = FilePage(bwiki(), bwiki_title)
            page = FilePage(Site(), title)
            bwiki_pages[skin_id] = bwiki_page
            pages[skin_id] = page
    gen = PreloadingGenerator(bwiki_pages.values())
    for page in gen:
        pass
    gen = PreloadingGenerator(pages.values())
    for page in gen:
        pass
    f1 = temp_file_dir / "gallery_file_1.png"
    f2 = temp_file_dir / "gallery_file_2.png"
    for skin_id in pages.keys():
        p1 = bwiki_pages[skin_id]
        p2 = pages[skin_id]
        download_file(p1.get_file_url(), f1)
        download_file(p2.get_file_url(), f2)
        identical = filecmp.cmp(f1, f2, shallow=False)
        filecmp.clear_cache()
        if not identical:
            print(f"Double check {p2.full_url()}")


if __name__ == "__main__":
    main()

from pathlib import Path

import requests
from pywikibot import Site, Page, FilePage
from pywikibot.pagegenerators import GeneratorFactory

bwiki = Site(code="bwiki")
s = Site()

char_mapper: dict[str, str] = {
    "米雪儿·李": "Michele",
    "米雪儿": "Michele",
    "信": "Nobunaga",
    "心夏": "Kokona",
    "伊薇特": "Yvette",
    "芙拉薇娅": "Flavia",
    "明": "Ming",
    "拉薇": "Lawine",
    "梅瑞狄斯": "Meredith",
    "令": "Reiichi",
    "香奈美": "Kanami",
    "艾卡": "Aika",
    "加拉蒂亚": "Galatea",
    "奥黛丽": "Audrey",
    "玛德蕾娜": "Maddelena",
    "绯莎": "Fuchsia",
    "星绘": "Celestia",
    "白墨": "Bai Mo"
}


def download_file(url, local_filename: Path):
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename


def main():
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
        print(url)
        title = char_mapper[title]
        target_page = FilePage(s, f'File:{title} Profile.png')
        if not target_page.exists():
            s.upload(target_page, source_url=url, comment="upload from bwiki")


if __name__ == "__main__":
    main()

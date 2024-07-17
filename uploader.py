import re

from pywikibot import Site, FilePage
from pywikibot.site._apisite import APISite

from asset_utils import resource_root

s: APISite = Site()


def upload_emotes():
    path = resource_root / "Emote"
    for f in path.glob("*.png"):
        if f.name.startswith("T_Dynamic_Emote_"):
            file_num = re.search(r"\d+", f.name).group(0)
            target = FilePage(s, f"File:Emote_{file_num}.png")
            s.upload(target, source_filename=str(f.absolute()), text='[[Category:Emotes]]', comment='Batch upload emotes')


def main():
    upload_emotes()


if __name__ == '__main__':
    main()

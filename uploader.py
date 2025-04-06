from pathlib import Path

from pywikibot import FilePage, Page

from global_config import get_characters
from utils.file_utils import local_file_dir
from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s


def upload_emotes():
    def e1():
        p = Path("files/emotes_outgame/renamed/卡丘丘")
        requests = []
        for d in p.iterdir():
            if d.is_file():
                continue
            char_name = d.name
            for index, f in enumerate(d.iterdir(), 1):
                assert f.name.endswith(".png")
                target_file = FilePage(s, f"File:Emotes extra {char_name} {f.name}")
                requests.append(UploadRequest(f, target_file, f"[[Category:Extra emotes]][[Category:{char_name} emotes]]",
                                              "batch upload emotes"))
        process_uploads(requests)

    def e2():
        p = Path("files/emotes_outgame/renamed/卡丘丘")
        requests = []
        for index, f in enumerate(p.iterdir(), 1):
            if not f.is_file():
                continue
            assert f.name.endswith(".png")
            target_file = FilePage(s, f"File:Emotes extra {f.name}")
            requests.append(UploadRequest(f, target_file, f"[[Category:Extra emotes]]",
                                          "batch upload emotes"))
        process_uploads(requests)

    def e3():
        p = Path("files/emotes_outgame/renamed/b站")
        requests = []
        for index, f in enumerate(p.iterdir(), 1):
            assert f.name.endswith(".png")
            target_file = FilePage(s, f"File:{f.name}")
            requests.append(UploadRequest(f, target_file, f"[[Category:Extra emotes]][[Category:Kanami emotes]]",
                                          "batch upload emotes"))
        process_uploads(requests)

    def e4():
        for c in get_characters():
            cat_page = Page(s, f"Category:{c.name} emotes")
            cat_page.text = "[[Category:Extra emotes]]"
            cat_page.save(summary="batch create cat")


    def e5():
        p = Path("files/emotes_outgame/renamed/玩法介绍")
        requests = []
        for index, f in enumerate(p.iterdir(), 1):
            assert f.name.endswith(".png")
            target_file = FilePage(s, f"File:Emotes extra tutorial {index}.png")
            requests.append(UploadRequest(f, target_file, f"[[Category:Extra emotes]]",
                                          "batch upload emotes"))
        process_uploads(requests)

    e5()


def upload_local():
    p = local_file_dir / "upload"
    requests = []
    files = list(p.glob("*.jpg")) + list(p.glob("*.png"))
    for f in files:
        target_file = FilePage(s, "File:" + f.name)
        # char_name = f.name.split(" ")[0]
        requests.append(UploadRequest(f, target_file, f"[[Category:Event images]]",
                                      "batch upload images"))
    process_uploads(requests)


def main():
    upload_emotes()


if __name__ == '__main__':
    main()
from pathlib import Path

from pywikibot import FilePage

from utils.upload_utils import UploadRequest, process_uploads
from utils.wiki_utils import s


def upload_local():
    p = Path("files/upload")
    requests = []
    files = list(p.glob("*.jpg")) + list(p.glob("*.png"))
    for f in files:
        target_file = FilePage(s, "File:" + f.name)
        # char_name = f.name.split(" ")[0]
        requests.append(UploadRequest(f, target_file, f"[[Category:Event images]]",
                                      "batch upload images"))
    process_uploads(requests)


def main():
    upload_local()


if __name__ == '__main__':
    main()
import os
from pathlib import Path

from pywikibot import FilePage

from audio.audio_parser import parse_role_voice
from audio.audio_utils import compute_audio_distance, load_json_voices
from utils.asset_utils import audio_root
from utils.general_utils import download_file
from utils.lang import languages_with_audio
from utils.wiki_utils import s


def test_audio_similarity():
    targets = [
        "CN_Vox_Michele_BPCHAR_065", # same
        "EN_Vox_Michele_BPCHAR_018", # same
        "EN_Vox_Michele_BPCHAR_019", # diff
        "EN_Vox_Michele_BPCHAR_020", # diff
        "EN_Vox_Ming_BPCHAT_143.", # diff
    ]
    voices = load_json_voices('Michele') + load_json_voices('Ming')
    download_dir = Path("files/cache")
    download_dir.mkdir(parents=True, exist_ok=True)
    for v in voices:
        for lang in languages_with_audio():
            file_page_title = v.get_file_page(lang)
            if file_page_title == "":
                continue
            file_page = FilePage(s, "File:" + file_page_title)
            local_path = audio_root / lang.audio_dir_name / v.file[lang.code]
            if any(string in file_page_title for string in targets):
                temp_file = download_dir / file_page_title
                if not temp_file.exists():
                    download_file(file_page.get_file_url(), temp_file)
                result = compute_audio_distance(local_path, temp_file)
                print(f"Comparing {file_page_title}: {result}")

if __name__ == "__main__":
    test_audio_similarity()
else:
    raise ImportError("Do not import this module. Run it directly instead.")
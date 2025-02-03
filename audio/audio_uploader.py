import subprocess
from pathlib import Path

from pywikibot import FilePage
from pywikibot.pagegenerators import GeneratorFactory

from audio.audio_utils import audio_is_same, wav_to_ogg
from audio.voice import Voice
from utils.asset_utils import audio_root
from utils.general_utils import download_file
from utils.lang import languages_with_audio, CHINESE

from utils.upload_utils import upload_file
from utils.wiki_utils import s


def upload_audio(source: Path, target: FilePage, text: str, force: bool = False):
    assert source.exists()
    temp_file = Path("temp.ogg")
    wav_to_ogg(source, temp_file)
    upload_file(text=text, target=target, file=temp_file, force=force)
    temp_file.unlink()


def upload_audio_file(voices: list[Voice],
                      char_name: str,
                      dry_run: bool = False,
                      force_replace: bool = False):
    gen = GeneratorFactory()
    gen.handle_args([f"-cat:{char_name} voice lines", "-ns:File"])
    gen = gen.getCombinedGenerator()
    existing: set[str] = set(p.title(underscore=True, with_ns=False) for p in gen)
    text = f"[[Category:{char_name} voice lines]]"
    temp_download_dir = Path("files/cache/audio")
    temp_download_dir.mkdir(parents=True, exist_ok=True)
    for v in voices:
        for lang in languages_with_audio():
            file_page_title = v.file_page.get(lang.code, "")
            if file_page_title == "":
                continue
            file_page = FilePage(s, "File:" + file_page_title)
            local_path = audio_root / lang.audio_dir_name / v.file[lang.code]
            if file_page_title in existing:
                # FIXME: extend this comparison to non-English lines as well?
                if not file_page_title.startswith("EN"):
                    continue
                temp_wiki_file = temp_download_dir / file_page_title
                if not temp_wiki_file.exists():
                    download_file(file_page.get_file_url(), temp_wiki_file)
                is_same = audio_is_same(local_path, temp_wiki_file)
                if not is_same:
                    if dry_run:
                        print(f"{file_page_title} is {is_same}")
                    elif force_replace:
                        # Only replace the old copy if this is not a dry run AND force replace is explicitly enabled
                        # Need to invalidate the local cache
                        temp_wiki_file.unlink()
                        upload_audio(local_path, file_page, text, True)
            else:
                assert local_path.exists()
                if dry_run:
                    print(f"Will upload {local_path.name} to {file_page_title}")
                else:
                    upload_audio(local_path, file_page, text, force=force_replace)


def ensure_audio_files_exist(voices: list[Voice]):
    for v in voices:
        has_file = False
        for lang in languages_with_audio():
            file_name = v.file.get(lang.code, '')
            audio_path = audio_root / lang.audio_dir_name / f"{file_name}"
            if file_name != '':
                if not v.non_local:
                    assert audio_path.exists(), f"{audio_path} does not exist"
                has_file = True
                v.set_file_page(lang)
        assert has_file

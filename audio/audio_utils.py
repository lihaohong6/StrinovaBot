import subprocess
from pathlib import Path
from typing import Any

from pywikibot import FilePage
from pywikibot.pagegenerators import GeneratorFactory

from audio.audio_parser import Voice
from utils.asset_utils import audio_root
from utils.json_utils import load_json
from utils.lang import CHINESE, languages_with_audio

from utils.upload_utils import upload_file
from utils.wiki_utils import s


def upload_audio(source: Path, target: FilePage, text: str):
    assert source.exists()
    temp_file = Path("temp.ogg")
    subprocess.run(["ffmpeg", "-i", source, "-c:a", "libopus", "-y", temp_file],
                   check=True,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL
                   )
    upload_file(text=text, target=target, file=temp_file)
    temp_file.unlink()


def upload_audio_file(voices: list[Voice], char_name: str):
    for v in voices:
        for lang in languages_with_audio():
            file_name = v.file.get(lang.code, '')
            audio_path = audio_root / lang.audio_dir_name / f"{file_name}"
            if file_name != '' and audio_path.exists():
                v.set_file_page(lang)
            else:
                # Chinese file must always be present
                assert lang != CHINESE or (audio_path.exists() and audio_path.is_file()), f"{audio_path} does not exist"
    gen = GeneratorFactory()
    gen.handle_args([f"-cat:{char_name} voice lines", "-ns:File"])
    gen = gen.getCombinedGenerator()
    existing: set[str] = set(p.title(underscore=True, with_ns=False) for p in gen)
    text = f"[[Category:{char_name} voice lines]]"
    for v in voices:
        assert v.file_page[CHINESE.code] != ""
        for lang in languages_with_audio():
            file_page = v.file_page.get(lang.code, "")
            if file_page not in existing and file_page != "":
                path = audio_root / lang.audio_dir_name / v.file[lang.code]
                assert path.exists()
                upload_audio(path, FilePage(s, "File:" + file_page), text)


VoiceJson = dict[int, dict[str, Any]]


def load_json_voices(char_name: str) -> list[Voice]:
    voices_json = load_json(get_json_path(char_name))
    voices = []
    for voice_id, voice_data in voices_json.items():
        voice = Voice([int(voice_id)])
        for k, v in voice_data.items():
            setattr(voice, k, v)
        voice.id = [voice.id]
        voices.append(voice)
    return voices


def get_json_path(char_name: str) -> Path:
    return Path("audio/data/" + char_name + ".json")

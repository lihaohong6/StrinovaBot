import subprocess
from pathlib import Path
from typing import Any

from pywikibot import FilePage
from pywikibot.pagegenerators import GeneratorFactory

from audio.audio_parser import Voice
from utils.asset_utils import audio_root
from utils.general_utils import load_json

from utils.uploader import upload_file
from utils.wiki_utils import s


def pick_two(a: str, b: str) -> str:
    """
    Pick a string. Prefer the first one but use the second one if the first is empty.
    :param a:
    :param b:
    :return:
    """
    if "NoTextFound" in a:
        a = ""
    if "NoTextFound" in b:
        b = ""
    if a.strip() in {"", "?", "彩蛋"}:
        return b
    return a


def pick_string(strings: list[str]) -> str:
    i = len(strings) - 2
    while i >= 0:
        strings[i] = pick_two(strings[i], strings[i + 1])
        i -= 1
    return strings[0]


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
        path_cn = audio_root.joinpath("Chinese").joinpath(f"{v.file_cn}")
        assert path_cn.exists(), f"{path_cn} does not exist"
        v.file_page_cn = f"CN_{v.path}.ogg"
        path_jp = audio_root.joinpath("Japanese").joinpath(f"{v.file_jp}")
        if v.file_jp != "" and path_jp.exists():
            v.file_page_jp = f"JP_{v.path}.ogg"
    gen = GeneratorFactory()
    gen.handle_args([f"-cat:{char_name} voice lines", "-ns:File"])
    gen = gen.getCombinedGenerator()
    existing: set[str] = set(p.title(underscore=True, with_ns=False) for p in gen)
    text = f"[[Category:{char_name} voice lines]]"
    for v in voices:
        assert v.file_page_cn != ""
        if v.file_page_cn not in existing:
            path = audio_root.joinpath("Chinese").joinpath(f"{v.file_cn}")
            upload_audio(path, FilePage(s, "File:" + v.file_page_cn), text)
        # FIXME: Vox_SelectCharacter-0208-event.wav is for Michele in CN but for Yvette in JP;
        #  do not upload Japanese files for now
        if v.file_page_jp not in existing and v.file_page_jp != "":
            path = audio_root.joinpath("Japanese").joinpath(f"{v.file_jp}")
            upload_audio(path, FilePage(s, "File:" + v.file_page_jp), text)


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

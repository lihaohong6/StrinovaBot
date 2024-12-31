import os
import subprocess
from pathlib import Path
from typing import Any

from pywikibot import FilePage
from pywikibot.pagegenerators import GeneratorFactory

from audio.voice import Voice
from utils.asset_utils import audio_root
from utils.general_utils import download_file
from utils.json_utils import load_json
from utils.lang import CHINESE, languages_with_audio

from utils.upload_utils import upload_file
from utils.wiki_utils import s


def upload_audio(source: Path, target: FilePage, text: str, force: bool = False):
    assert source.exists()
    temp_file = Path("temp.ogg")
    subprocess.run(["ffmpeg", "-i", source, "-c:a", "libopus", "-y", temp_file],
                   check=True,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL
                   )
    upload_file(text=text, target=target, file=temp_file, force=force)
    temp_file.unlink()


def upload_audio_file(voices: list[Voice], char_name: str, dry_run: bool = False):
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
    temp_download_dir = Path("files/cache")
    temp_download_dir.mkdir(parents=True, exist_ok=True)
    for v in voices:
        assert v.file_page[CHINESE.code] != ""
        for lang in languages_with_audio():
            file_page_title = v.file_page.get(lang.code, "")
            if file_page_title == "":
                continue
            file_page = FilePage(s, "File:" + file_page_title)
            local_path = audio_root / lang.audio_dir_name / v.file[lang.code]
            if file_page_title in existing:
                if not file_page_title.startswith("EN"):
                    continue
                temp_wiki_file = temp_download_dir / file_page_title
                if not temp_wiki_file.exists():
                    download_file(file_page.get_file_url(), temp_wiki_file)

                is_same = audio_is_same(local_path, temp_wiki_file)
                if dry_run:
                    print(f"{file_page_title} is {is_same}")
                if not is_same and not dry_run:
                    upload_audio(local_path, file_page, text, True)
            else:
                assert local_path.exists()
                if dry_run:
                    print(f"Will upload {local_path.name} to {file_page_title}")
                else:
                    upload_audio(local_path, file_page, text)


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


def compute_audio_distance(audio_path1, audio_path2, sr=22050, n_mfcc=13) -> float:
    """
    Computes similarity score between two audio clips using MFCC features.

    Parameters:
        audio_path1 (str): Path to the first audio file.
        audio_path2 (str): Path to the second audio file.
        sr (int): Sampling rate for audio loading.
        n_mfcc (int): Number of MFCC coefficients to extract.

    Returns:
        float: Similarity score (range: -1 to 1, where 1 is most similar).
    """
    import librosa.feature
    import numpy as np
    from scipy.spatial.distance import euclidean
    from fastdtw import fastdtw

    def extract_audio_info(audio_path, sr=22050, n_mfcc=13) -> tuple[int, np.ndarray]:
        """
        Extracts the mean MFCC features from an audio file.

        Parameters:
            audio_path (str): Path to the audio file.
            sr (int): Sampling rate for audio loading.
            n_mfcc (int): Number of MFCC coefficients to extract.

        Returns:
            np.ndarray: Mean MFCC features.
        """
        y, _ = librosa.load(audio_path, sr=sr)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
        return y.shape[0], mfcc

    try:
        # Extract mean MFCC features
        length1, mfcc1 = extract_audio_info(audio_path1, sr, n_mfcc)
        length2, mfcc2 = extract_audio_info(audio_path2, sr, n_mfcc)

        if abs(length1 - length2) > 1:
            return 1
        distance, _ = fastdtw(mfcc1, mfcc2, dist=euclidean)

        return distance / length1
    except ValueError as e:
        print(f"Error computing similarity score between {audio_path1} and {audio_path2}: {e}")
        return 0


def audio_is_same(audio1, audio2):
    return compute_audio_distance(audio1, audio2) < 0.05


def audio_is_silent(source: Path):
    import librosa.feature
    import numpy as np
    y, sr = librosa.load(source, sr=None)

    rms = librosa.feature.rms(y=y)
    avg_rms = np.mean(rms)

    # If the average RMS is below the threshold, the audio is considered silent
    if avg_rms < 0.001:
        return True

    return False

import subprocess
from pathlib import Path
from typing import Any

import librosa.feature
from pywikibot import FilePage
from pywikibot.pagegenerators import GeneratorFactory

from audio.voice import Voice
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


def audio_is_same(audio1, audio2):
    import librosa.feature
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity

    def extract_mean_mfcc(audio_path, sr=22050, n_mfcc=13):
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
        return np.mean(mfcc, axis=1)

    def compute_similarity(audio_path1, audio_path2, sr=22050, n_mfcc=13) -> float:
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
        # Extract mean MFCC features
        mfcc1_mean = extract_mean_mfcc(audio_path1, sr, n_mfcc)
        mfcc2_mean = extract_mean_mfcc(audio_path2, sr, n_mfcc)

        # Compute cosine similarity
        similarity = cosine_similarity([mfcc1_mean], [mfcc2_mean])[0][0]
        return similarity

    return compute_similarity(audio1, audio2) > 0.9999


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

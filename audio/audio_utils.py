import subprocess
from pathlib import Path
from typing import Any

from audio.voice import Voice
from utils.json_utils import load_json

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


def compute_audio_distance(audio_path1: Path, audio_path2: Path, sr=22050, n_mfcc=13) -> float:
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

    def extract_audio_info(audio_path: Path, sr=22050, n_mfcc=13) -> tuple[int, np.ndarray]:
        """
        Extracts the mean MFCC features from an audio file.

        Parameters:
            audio_path (str): Path to the audio file.
            sr (int): Sampling rate for audio loading.
            n_mfcc (int): Number of MFCC coefficients to extract.

        Returns:
            np.ndarray: Mean MFCC features.
        """
        y, _ = librosa.load(audio_path, sr=sr, duration=10)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
        return y.shape[0], mfcc

    try:
        # Extract mean MFCC features
        length1, mfcc1 = extract_audio_info(audio_path1, sr, n_mfcc)
        length2, mfcc2 = extract_audio_info(audio_path2, sr, n_mfcc)

        if abs(length1 - length2) > 1:
            return 1

        if mfcc1.shape != mfcc2.shape:
            mfcc1 = mfcc1.T
            mfcc2 = mfcc2.T

        distance, _ = fastdtw(mfcc1, mfcc2, dist=euclidean)

        return distance / length1
    except ValueError as e:
        print(f"Error computing similarity score between {audio_path1} and {audio_path2}: {e}")
        return 0


def audio_is_same(audio1: Path, audio2: Path):
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


def wav_to_ogg(wav_path: Path, ogg_path: Path):
    subprocess.run(["ffmpeg", "-i", wav_path, "-c:a", "libopus", "-y", ogg_path],
                   check=True,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL
                   )


def wem_to_wav(wem_path: Path, wav_path: Path):
    subprocess.run(["vgmstream-cli", wem_path, "-o", wav_path],
                   check=True,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)

import re
import subprocess
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from audio.data.conversion_table import VoiceType, voice_conversion_table, table_languages
from audio.voice import Voice, get_voice_path_digits
from utils.json_utils import load_json
from utils.lang import CHINESE, ENGLISH

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

        # Sometimes audio files change by increasing/decreasing the length of silence.
        # This would mistakenly treat them as different files
        # if abs(length1 - length2) > 1:
        #     return 1

        if mfcc1.shape != mfcc2.shape:
            mfcc1 = mfcc1.T
            mfcc2 = mfcc2.T

        distance, _ = fastdtw(mfcc1, mfcc2, dist=euclidean)

        return distance / length1
    except ValueError as e:
        print(f"Error computing similarity score between {audio_path1} and {audio_path2}: {e}")
        return 0


def audio_is_same(audio1: Path, audio2: Path):
    return compute_audio_distance(audio1, audio2) < 0.08


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


def get_trigger_id(voice_type: VoiceType, digits: str) -> str:
    if voice_type == VoiceType.SYSTEM:
        return f"Kanami_Communicate_{digits}"
    return digits


@dataclass
class VoicePath:
    type: VoiceType
    trigger_id: str
    title: dict[str, str]


def parse_path(path: str) -> VoicePath | None:
    # FIXME: temporary patch to prevent birthday lines (e.g. Vox_Audrey_Birthday_001) from interfering
    #  with regular lines
    if re.search(r"(_Date|Birthday_)\d{2,3}", path) is not None or "_TeamGuide_" in path:
        return None

    digits = get_voice_path_digits(path)
    if digits is None:
        return None

    def name_tuple_to_dict(names: tuple[str, str]) -> dict[str, str]:
        cn, en = names
        return {
            CHINESE.code: cn,
            ENGLISH.code: en,
        }

    if "Vox_Communicate_Kanami" in path:
        voice_type = VoiceType.SYSTEM
        title_tuple = voice_conversion_table[VoiceType.SYSTEM][digits]
    else:
        for voice_type, voice_dict in voice_conversion_table.items():
            if voice_type == VoiceType.SYSTEM:
                continue
            if digits in voice_dict:
                title_tuple = voice_dict[digits]
                break
        else:
            return None
    trigger_id = get_trigger_id(voice_type, digits)
    return VoicePath(voice_type, trigger_id, name_tuple_to_dict(title_tuple))


def make_custom_triggers():
    triggers: dict[str, Trigger] = {}

    def make_trigger(key: str, names: dict[str, str], voice_type: VoiceType):
        trigger_id = key
        triggers[key] = Trigger(
            id=trigger_id,
            name=names,
            description=names,
            role_id=0,
            type=voice_type,
        )

    for voice_type, table in voice_conversion_table.items():
        for digits, names in table.items():
            names_dict = dict(zip(table_languages, names))
            make_trigger(get_trigger_id(voice_type, digits), names_dict, voice_type)
    return triggers


@dataclass
class Trigger:
    id: str
    type: VoiceType
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    voice_id: list[int] = field(default_factory=list)
    # 0: applicable for all
    # otherwise: applicable to a single character
    role_id: int = 0
    voices: list[Voice] = field(default_factory=list)
    children: list["UpgradeTrigger"] = field(default_factory=list)

    def merge(self, o: "Trigger"):
        assert self.id == o.id and self.type == o.type
        for f in fields(self):
            if f.type == str:
                a1 = getattr(self, f.name)
                a2 = getattr(o, f.name)
                if a1 == a2:
                    continue
                if a1 == "":
                    setattr(self, f.name, a2)
                raise RuntimeError(str(self) + "\n" + str(o))
            elif f.type == dict:
                raise RuntimeError("TODO: dict merge unimplemented")
        if self.role_id != o.role_id:
            if self.role_id == 999:
                self.role_id = o.role_id


@dataclass
class UpgradeTrigger:
    trigger: int
    voice_id: list[int]
    skins: list[int]

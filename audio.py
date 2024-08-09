import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from asset_utils import audio_root
from utils import get_table, get_game_json


def audio_convert():
    output_root = Path("files/audio")
    output_root.mkdir(exist_ok=True, parents=True)
    for file in audio_root.rglob("*.txtp"):
        file_name = file.name
        out_path = output_root.joinpath(file.relative_to(audio_root))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path = out_path.parent.joinpath(file_name.replace(".txtp", ".wav"))
        subprocess.call(["vgmstream-cli.exe", file, "-o", out_path], stdout=open(os.devnull, 'wb'))


@dataclass
class Voice:
    id: int
    role_id: int
    quality: int
    name: str = ""
    text: str = ""


def file_audio_file(file_name: str):
    pass


def role_voice():
    i18n = get_game_json()['RoleVoice']
    voice_table = get_table("RoleVoice")
    for k, v in voice_table.items():
        name_obj = v['VoiceName']
        key = name_obj.get("Key", None)
        name = ""
        if "Key" is not None:
            name = name_obj["SourceString"]
            name = i18n.get(key, name)

        content_obj = v['Content']
        key = content_obj.get("Key", None)
        content = ""
        if "Key" is not None:
            content = content_obj["SourceString"]
            content = i18n.get(key, content)

        file_audio_file(v["AkEvent"]["AssetPathName"].split(".")[-1])

        Voice(id=k,
              role_id=v['RoleId'],
              quality=v['Quality'],
              name=name,
              text=content)

import re
from dataclasses import dataclass, field, fields
from enum import Enum

from utils.dict_utils import merge_dict2
from utils.lang import Language


class VoiceUpgrade(Enum):
    REGULAR = ""
    ORG = "org"
    RED = "red"


@dataclass
class Voice:
    id: list[int]
    role_id: int = -1
    quality: int = -1
    # title: displayed on the wiki
    title: dict[str, str] = field(default_factory=dict)
    # name: given by the game itself
    name: dict[str, str] = field(default_factory=dict)
    transcription: dict[str, str] = field(default_factory=dict)
    translation: dict[str, dict[str, str]] = field(default_factory=dict)
    path: str = ""
    file: dict[str, str] = field(default_factory=dict)
    file_page: dict[str, str] = field(default_factory=dict)
    upgrade: VoiceUpgrade = VoiceUpgrade.REGULAR
    # non_local = True indicates that the file no longer exists in the game, but might have been uploaded to the wiki
    # already
    non_local: bool = False

    def merge(self, o: "Voice"):
        assert self.path == o.path
        assert len(o.id) == 1
        self.id.append(o.id[0])
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

    def lang_merge(self, o: "Voice"):
        # assert len(o.id) == 1, f"Other voice has more than one id: {o.id}\nPath: {o.path}\n{o}"
        self.id.extend(o.id)
        self.file = merge_dict2(self.file, o.file)

    def get_file_page(self, lang: Language):
        return f"{lang.audio_code.upper()}_{self.path}.ogg"

    def set_file_page(self, lang: Language):
        self.file_page[lang.code] = self.get_file_page(lang)

    def path_digits(self) -> str | None:
        return get_voice_path_digits(self.path)

    @property
    def icon(self):
        assert self.role_id != 0
        return f"File:Item Icon 22{self.role_id}001.png"


def get_voice_path_digits(path: str) -> str | None:
    r = re.search(r"(\d{3})(_|$)", path)
    if r is None:
        return None
    return r.group(1)

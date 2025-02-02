from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from audio.audio_parser import parse_banks_xml, map_bank_name_to_files, find_audio_file
from story.story_preprocessor import RawEvent
from utils.asset_utils import cn_export_root, audio_root, audio_event_root_global, global_export_root
from utils.lang import ENGLISH, CHINESE
from utils.upload_utils import UploadRequest


class StoryRowType(Enum):
    PLAYER = 0,
    PLAYER_REPLY = 99,
    CHARACTER = 1,
    BGM = 2,
    BACKGROUND = 3,
    SOUND_EFFECT = 4,
    INFO = 5


@dataclass
class StoryRow(ABC):
    id: int

    @property
    def type(self):
        raise NotImplementedError()

    @property
    def data(self) -> dict[str, str | int]:
        raise NotImplementedError()


@dataclass
class PlayerLine(StoryRow):
    text: dict[str, str]

    @property
    def type(self):
        return StoryRowType.PLAYER

    @property
    def data(self):
        return {
            '': 'sensei',
            'text': self.text.get(ENGLISH.code, self.text.get(CHINESE.code))
        }


@dataclass
class PlayerReply(StoryRow):
    options: list[dict[str, str]]
    group: int

    @property
    def type(self):
        return StoryRowType.PLAYER_REPLY

    @property
    def data(self):
        result = {'': "reply",
                'group': self.group}
        options = dict(('option{}_' + str(index), option) for index, option in enumerate(self.options, 1))
        return result | options


@dataclass
class CharacterLine(StoryRow):
    name: str
    text: dict[str, str]
    profile: str = ""
    group: int = -1
    option: int = -1

    @property
    def type(self):
        return StoryRowType.CHARACTER

    @property
    def data(self):
        result = {
            "": "student-text",
            "name": self.name,
            "text": self.text[ENGLISH.code],
            "portrait": self.profile
        }
        if self.group >= 0:
            result["group"] = self.group
            result["option"] = self.option
        return result


@dataclass
class BGMChange(StoryRow):
    filename: str
    name: str

    @property
    def type(self):
        return StoryRowType.BGM

    @property
    def data(self):
        return {'': 'bgm', 'bgm': self.filename, 'name': self.name}


@dataclass
class BackgroundChange(StoryRow):
    background: str

    @property
    def type(self):
        return StoryRowType.BACKGROUND

    @property
    def data(self):
        return {'': "background", 'background': self.background}


@dataclass
class SoundEffectChange(StoryRow):
    filename: str
    name: str

    @property
    def type(self):
        return StoryRowType.SOUND_EFFECT

    @property
    def data(self):
        return {
            '': "sound",
            'sound': self.filename,
            'name': self.name
        }


@dataclass
class InfoRow(StoryRow):
    text: dict[str, str]

    @property
    def type(self):
        return StoryRowType.INFO

    @property
    def data(self):
        return {'': 'info', 'text': self.text.get(ENGLISH.code, self.text.get(CHINESE.code))}


@dataclass
class Story:
    rows: list[StoryRow] = field(default_factory=list)
    bgm: list[UploadRequest] = field(default_factory=list)
    background_images: list[UploadRequest] = field(default_factory=list)


def parse_raw_events(raw_events: list[RawEvent]) -> Story:
    story = Story()
    for event in raw_events:
        parse_background(event, story)
        parse_bgm(event, story)
        parse_conversation(event, story)
    return story


def parse_conversation(event: RawEvent, story):
    # SubOptionEvent: player choice, need to merge with adjacent event
    talker = event.talker_name
    if talker is not None:
        talker = talker.get('cn', None)
    if len(event.extend_performance_list) > 0:
        for ext in event.extend_performance_list:
            story.rows.append(InfoRow(event.id, text=ext))
    if event.role_id == 0 and talker is None and event.text is not None:
        story.rows.append(PlayerLine(event.id, text=event.text))
    if event.role_id != 0 and talker is not None:
        name = event.talker_name[ENGLISH.code]
        story.rows.append(CharacterLine(
            id=event.id,
            name=name,
            text=event.text,
            profile=f"{name}_Profile.png"
        ))


def get_story_audio_local_path(name: str) -> Path | None:
    sfx_dir = audio_root / "sfx"
    json_file = audio_event_root_global / f"{name}.json"
    if not json_file.exists():
        return None
    banks = parse_banks_xml("sfx")
    mapping = map_bank_name_to_files(sfx_dir)
    local_file = find_audio_file(json_file, banks, mapping)
    if local_file is None:
        return None
    return sfx_dir / local_file


def parse_bgm(event: RawEvent, story: Story):
    if event.bgm:
        bgm = event.bgm.split(".")[-1]
        wiki_file = f"BGM {bgm}.ogg"
        local_path = get_story_audio_local_path(bgm)
        if local_path is None:
            print(f"Could not find {bgm}")
        else:
            print(f"Found {bgm}")
            story.bgm.append(UploadRequest(local_path, wiki_file, "[[Category:Story BGMs]]"))
            story.rows.append(BGMChange(event.id, wiki_file, name=bgm))
    if event.sound_effect:
        se = event.sound_effect.split(".")[-1]
        wiki_file = f"SE {se}.ogg"
        local_path = get_story_audio_local_path(se)
        if local_path is None:
            print(f"Could not find {se}")
        else:
            print(f"Found {se}")
            story.bgm.append(UploadRequest(local_path, wiki_file, "[[Category:Sound effects]]"))
            story.rows.append(SoundEffectChange(event.id, wiki_file, name=se))


def parse_background(event: RawEvent, story: Story):
    if event.background is None:
        return
    background = event.background
    if "Maps/Apartment" in background:
        fs_path, wiki_file = background.split(".")
        local_file = global_export_root / (fs_path.split("Maps/")[1] + ".png")
        wiki_file = f"BG {wiki_file}.png"
        story.background_images.append(UploadRequest(local_file, wiki_file, "[[Category:Background images]]"))
    elif "PC/Frontend" in background:
        # No need to upload since these are event files and are already present on the wiki
        fs_path, wiki_file = background.split(".")
        # local_file = cn_export_root / fs_path.split("PC/")[1]
        wiki_file = f"PC {wiki_file}.png"
        # story.background_images.append(UploadRequest(local_file, wiki_file, "[[Category:Background images]]"))
    elif "T_DefaultBlack_Gamma" in background:
        wiki_file = "BG Black.png"
    else:
        raise RuntimeError(f"Unknown background type: {background}")
    bg_change = BackgroundChange(event.id, wiki_file)
    story.rows.append(bg_change)

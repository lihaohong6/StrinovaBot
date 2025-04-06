import re
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from audio.audio_parser import parse_banks_xml, map_bank_name_to_files, find_audio_file, get_bgm_file_by_event_id
from global_config import is_valid_char_name
from story.story_preprocessor import RawEvent, EventType
from utils.asset_utils import audio_root, audio_event_root_global, global_export_root, global_resources_root
from utils.general_utils import en_name_to_cn
from utils.json_utils import load_json
from utils.lang_utils import get_english_version
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
            'text': get_english_version(self.text),
        }


@dataclass
class PlayerReply(StoryRow):
    options: list[dict[str, str]]
    group: int = -1

    @property
    def type(self):
        return StoryRowType.PLAYER_REPLY

    @property
    def data(self):
        result = {'': "reply",
                'group': self.group}
        options = dict(('option{}_' + str(index), get_english_version(option)) for index, option in enumerate(self.options, 1))
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
            "text": get_english_version(self.text),
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
    loop: bool = True

    @property
    def type(self):
        return StoryRowType.BGM

    @property
    def data(self):
        return {'': 'bgm', 'bgm': self.filename, 'name': self.name, 'loop': 'true' if self.loop else 'false'}


@dataclass
class BGMStop(StoryRow):
    @property
    def type(self):
        return StoryRowType.BGM

    @property
    def data(self):
        return {'': 'bgm-stop'}


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
        return {'': 'info', 'text': get_english_version(self.text)}


@dataclass
class Story:
    rows: list[StoryRow] = field(default_factory=list)
    title: dict[str, str] | None = None
    bgm: list[UploadRequest] = field(default_factory=list)
    background_images: list[UploadRequest] = field(default_factory=list)


def merge_options(story: Story):
    prev_replies: list[PlayerReply] = []
    result = []
    group = 0
    for row in story.rows:
        if isinstance(row, PlayerReply):
            prev_replies.append(row)
            continue
        # not a player reply
        if len(prev_replies) > 0:
            if len(prev_replies) > 1:
                # process prev replies
                group += 1
                options = [r.options[0] for r in prev_replies]
                result.append(PlayerReply(prev_replies[0].id, options=options, group=group))
            else:
                prev = prev_replies[0]
                result.append(PlayerLine(prev.id, prev.options[0]))
            prev_replies = []
        result.append(row)
    story.rows = result


def parse_raw_events(raw_events: list[RawEvent]) -> Story:
    story = Story()
    for event in raw_events:
        if event.prologue_title is not None:
            story.title = event.prologue_title
        parse_background(event, story)
        parse_bgm(event, story)
        parse_conversation(event, story)
    merge_options(story)
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
    elif event.event_type == EventType.SUB_OPTION_EVENT:
        story.rows.append(PlayerReply(event.id, options=[event.text]))
    elif talker is not None:
        name = get_english_version(event.talker_name)
        if name != "" and is_valid_char_name(name):
            profile = f"{name}_Profile.png"
        else:
            profile = ""
        story.rows.append(CharacterLine(
            id=event.id,
            name=name,
            text=event.text,
            profile=profile
        ))


def get_story_audio_local_path(name: str) -> Path | None:
    sfx_dir = audio_root / "sfx"
    json_file = audio_event_root_global / f"{name}.json"
    if not json_file.exists():
        return None
    banks = parse_banks_xml("sfx")
    mapping = map_bank_name_to_files(sfx_dir)
    local_file = find_audio_file(json_file, banks, mapping)
    if local_file is not None:
        return sfx_dir / local_file
    # Special treatment for BGMs
    event_id = load_json(json_file)["Properties"]["ShortID"]
    path = get_bgm_file_by_event_id(event_id)
    return path


def parse_bgm(event: RawEvent, story: Story):
    if event.bgm:
        bgm = event.bgm.split(".")[-1]
        if bgm.lower() == "bgm_date_play":
            return
        if bgm.lower() == "bgm_date_stop" or bgm.lower().endswith("_stop"):
            story.rows.append(BGMStop(event.id))
            return
        bgm_name = re.sub(r"^Bgm[_ ]", "", bgm)
        bgm_name = bgm_name.replace("_", " ")
        wiki_file = f"BGM {bgm_name}.ogg"
        local_path = get_story_audio_local_path(bgm)
        if local_path is None:
            print(f"Could not find bgm {bgm}")
        else:
            story.bgm.append(UploadRequest(local_path, wiki_file, "[[Category:Story BGMs]]"))
            is_bgm = bgm_name.startswith("Date")
            if is_bgm:
                story.rows.append(BGMChange(event.id, wiki_file, name=bgm_name))
            else:
                story.rows.append(SoundEffectChange(event.id, wiki_file, name=bgm_name))
    # Sound effects cannot be found. Skip for now.
    # if event.sound_effect:
    #     se = event.sound_effect.split(".")[-1]
    #     wiki_file = f"SE {se}.ogg"
    #     local_path = get_story_audio_local_path(se)
    #     if local_path is None:
    #         print(f"Could not find se {se}")
    #     else:
    #         print(f"Found se {se}: {local_path}")
    #         story.bgm.append(UploadRequest(local_path, wiki_file, "[[Category:Sound effects]]"))
    #         story.rows.append(SoundEffectChange(event.id, wiki_file, name=se))


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
    elif "T_DefaultWhite_Gamma" in background:
        wiki_file = "BG White.png"
    elif "T_Dynamic_Talent" in background:
        file_name = background.split(".")[-1]
        local_file = global_resources_root / "Talent" / (file_name + ".png")
        wiki_file = f"BG {file_name}.png"
        story.background_images.append(UploadRequest(local_file, wiki_file, "[[Category:Background images]]"))
    elif "None" in background:
        return
    else:
        raise RuntimeError(f"Unknown background type: {background}")
    bg_change = BackgroundChange(event.id, wiki_file)
    story.rows.append(bg_change)

import dataclasses
from dataclasses import dataclass
from enum import Enum

from utils.json_utils import get_all_game_json
from utils.lang_utils import get_text


class EventType(Enum):
    SUB_OPTION_EVENT = "SubOptionEvent"
    SINGLE_CLICK_EVENT = "SingleClickEvent"
    MULTIPLE_OPTION_EVENT = "MultipleOptionEvent"
    NORMAL_EVENT = "NormalEvent"


@dataclass
class RawEvent:
    event_type: EventType
    id: int
    next: list[int]
    prev: list[int]
    background: str | None
    bgm: str | None
    sound_effect: str | None
    role_id: int
    text: dict[str, str]
    prologue_title: dict[str, str] | None = None
    talker_name: dict[str, str] | None = None
    extend_performance_list: list[dict[str, str]] = dataclasses.field(default_factory=list)


def get_asset_path_name(v: dict, key: str) -> str | None:
    r = v.get(key, {}).get("AssetPathName", "None")
    if r == "None":
        return None
    return r


def get_raw_events(events: dict[int, dict], pred: dict[int, list[int]], i18n_name: str) -> list[RawEvent]:
    result: list[RawEvent] = []
    i18n = get_all_game_json(i18n_name)

    for event_id, v in events.items():
        type_candidates = [event_type for event_type in EventType if event_type.value in v["EventType"]]
        assert len(type_candidates) == 1, v["EventType"] + f" has wrong number of event type candidates: {type_candidates}"
        event_type = type_candidates[0]
        next_events = v["NextEventIds"]
        assert len(next_events) == 1 or event_type == EventType.MULTIPLE_OPTION_EVENT
        prev_events = pred.get(event_id, [])
        background = get_asset_path_name(v, "SceneBg")
        bgm = get_asset_path_name(v, "BgAkEvent")
        sound_effect = get_asset_path_name(v, "AkEvent")
        role_id = v["RoleId"]
        talker_name = get_text(i18n, v["TalkerName"])
        text_context = get_text(i18n, v["TextContext"])
        prologue_title = get_text(i18n, v["PrologueTitle"])
        extend_performance_list = []
        for p in v["ExtendPerformanceList"]:
            r = get_text(i18n, p['TextParam'])
            if r is not None:
                extend_performance_list.append(r)
        result.append(
            RawEvent(event_type=event_type, id=event_id,
                     next=next_events, prev=prev_events,
                     background=background,
                     bgm=bgm,
                     sound_effect=sound_effect,
                     role_id=role_id,
                     text=text_context,
                     prologue_title=prologue_title,
                     talker_name=talker_name,
                     extend_performance_list=extend_performance_list))

    return result

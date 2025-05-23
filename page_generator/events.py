from dataclasses import dataclass, field

import wikitextparser as wtp
from pywikibot.pagegenerators import GeneratorFactory

from page_generator.items import Item
from utils.dict_utils import merge_dict2
from utils.json_utils import get_all_game_json, get_table_global
from utils.lang_utils import StringConverters, get_text, get_english_version
from utils.wiki_utils import s, save_json_page
from utils.wtp_utils import get_templates_by_name


@dataclass
class EventTask:
    description: dict[str, str]
    reward: int
    reward_id: int
    daily: bool
    weekly: bool

    def __str__(self):
        if self.daily:
            freq = "Daily"
        elif self.weekly:
            freq = "Weekly"
        else:
            freq = "One-time"
        return ("|-\n"
                f"| {get_english_version(self.description)} || {freq} || {self.reward}")


@dataclass
class EventReward:
    item: Item
    quantity: int


@dataclass
class Event:
    id: int
    name: dict[str, str]
    tasks: list[EventTask]
    rewards: list[EventReward] = field(default_factory=list)


def manual_event_rewards(events: dict[int, Event]):
    rewards = []


def parse_events():
    i18n = merge_dict2(get_all_game_json("Activity"), get_all_game_json("ActivityTask"))
    activity_table = get_table_global("Activity")
    task_table = get_table_global("ActivityTask")
    result: dict[int, Event] = {}
    for event_id, v in activity_table.items():
        name = get_text(i18n, v['Name'], converter=StringConverters.all_caps_remove)
        result[event_id] = Event(id=event_id, name=name, tasks=[])
    for task_id, v in task_table.items():
        activity_id = v["ActivityId"]
        desc = get_text(i18n, v['Desc'])
        rewards = v["Prize"]
        if len(rewards) == 0:
            reward = -1
            reward_id = -1
        else:
            reward = rewards[0]['ItemAmount']
            reward_id = rewards[0]['ItemId']
        daily = v["DayFlush"]
        weekly = v["WeekFlush"]
        if activity_id not in result:
            continue
        result[activity_id].tasks.append(EventTask(description=desc, reward=reward, reward_id=reward_id, daily=daily, weekly=weekly))
    manual_event_rewards(result)
    return result


@dataclass
class WikiEvent:
    title: str
    image: str
    start: str
    end: str
    intro: str


def parse_wiki_events() -> list[WikiEvent]:
    gen = GeneratorFactory(s)
    gen.handle_args(['-cat:Events', '-titleregexnot:Patch|/'])
    result = []
    for page in gen.getCombinedGenerator(preload=True):
        parsed = wtp.parse(page.text)
        matches = get_templates_by_name(parsed, "Event top")
        assert len(matches) == 1, f"Template event top not found on {page.title()}"
        t = matches[0]
        args = {
            'title': page.title()
        }
        for attr in ['image', 'start', 'end', 'intro']:
            args[attr] = t.get_arg(attr).value.strip()
        result.append(WikiEvent(**args))
    result.sort(key=lambda e: e.start)
    return result


def save_wiki_events():
    events = parse_wiki_events()
    save_json_page("Module:Event/data.json", events)


def main():
    save_wiki_events()


if __name__ == '__main__':
    main()

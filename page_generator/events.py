from dataclasses import dataclass, field

from page_generator.items import Item
from utils.general_utils import get_table_global
from utils.json_utils import get_all_game_json
from utils.lang import ENGLISH
from utils.lang_utils import get_multilanguage_dict, StringConverters

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
                f"| {self.description[ENGLISH.code]} || {freq} || {self.reward}")


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
    i18n = get_all_game_json("Activity")
    i18n_task = get_all_game_json("ActivityTask")
    activity_table = get_table_global("Activity")
    task_table = get_table_global("ActivityTask")
    result: dict[int, Event] = {}
    for event_id, v in activity_table.items():
        name = get_multilanguage_dict(i18n, v['Name']['Key'], converter=StringConverters.all_caps_remove)
        result[event_id] = Event(id=event_id, name=name, tasks=[])
    for task_id, v in task_table.items():
        activity_id = v["ActivityId"]
        desc = get_multilanguage_dict(i18n_task, v['Desc']['Key'])
        rewards = v["Prize"]
        if len(rewards) == 0:
            reward = -1
            reward_id = -1
        else:
            reward = rewards[0]['ItemAmount']
            reward_id = rewards[0]['ItemId']
        daily = v["DayFlush"]
        weekly = v["WeekFlush"]
        result[activity_id].tasks.append(EventTask(description=desc, reward=reward, reward_id=reward_id, daily=daily, weekly=weekly))
    manual_event_rewards(result)
    return result


def print_event(event: Event):
    rid_to_task: dict[int, list[EventTask]] = {}
    for task in event.tasks:
        if task.reward_id not in rid_to_task:
            rid_to_task[task.reward_id] = []
        rid_to_task[task.reward_id].append(task)
    for _, tasks in rid_to_task.items():
        print("{| class=\"wikitable\"")
        print("|-\n"
              "! Task !! Frequency !! Points")
        for task in tasks:
            print(str(task))
        print("|}")


def main():
    events = parse_events()
    event = events[10028]
    print_event(event)


if __name__ == '__main__':
    main()

from dataclasses import dataclass

from page_generator.events import Event, EventTask, parse_events
from utils.json_utils import get_game_json, get_table_global


@dataclass
class EventMessage:
    id: int
    group: int
    title: str
    title_display: str
    content: str


def print_phantom_night_event_story():
    table = get_table_global("ActivityStrangeThiefStory")
    i18n = get_game_json()['ActivityStrangeThiefStory']

    def translate(obj: dict) -> str:
        return i18n.get(obj.get('Key', None), "")

    messages = []

    for _, event in table.items():
        event_id = event['Id']
        group = event['BelongToId']
        title = translate(event['BelongToName'])
        title_display = translate(event['TitleDisplay'])
        content = []
        content.append(translate(event['ContentAside']))
        for aside in event['Aside']:
            content.append(translate(aside))
        content.append(translate(event['ContentMono']))
        content = ["<br/>".join(line.strip() for line in c.split("\n") if line.strip() != "")
                   for c in content
                   if c != ""]
        messages.append(EventMessage(event_id, group, title, title_display, "<br/>".join(c.strip() for c in content)))

    for message in messages:
        print(f";Day {message.id}&#58; {message.title_display}")
        print(message.content)

    message_by_group: dict[int, list[EventMessage]] = {}
    for message in messages:
        group = message.group
        if group not in message_by_group:
            message_by_group[group] = []
        message_by_group[group].append(message)

    tab_titles = []
    tab_contents = []
    for group, messages in message_by_group.items():
        tab_titles.append(messages[0].title)
        content = []
        for message in messages:
            message: EventMessage
            content.append(f";Day {message.id}&#58; {message.title_display}")
            content.append(message.content)
        tab_contents.append("\n".join(content))
    print("{{Tab/tabs | group=story_by_type | " + " | ".join(tab_titles) + " }}")
    print("{{Tab/content | group=story_by_type | " + " | ".join(tab_contents) + " }}")


def print_spring_blessings_event_story():
    table = get_table_global("ActivityCNYFireStory")
    i18n = get_game_json()['ActivityCNYFireStory']

    tab_titles = []
    tab_contents = []
    for _, v in table.items():
        name_key = v['StoryName']['Key']
        content_key = v['StoryContext']['Key']
        tab_titles.append(i18n[name_key])
        tab_contents.append(i18n[content_key])
    print("{{Tab/tabs | group=stories | " + " | ".join(tab_titles) + " }}")
    print("{{Tab/content | group=stories | " + " | ".join(tab_contents) + " }}")


def print_outbreak_event_story():
    i18n = get_game_json()['ActivityBiochemicalModeTV']
    for i in range(1, 13):
        print(i18n[f'{i}_Content'], end="\n\n")


def print_event_tasks(event: Event):
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


def print_event_tasks_main():
    events = parse_events()
    event = events[10094]
    print_event_tasks(event)


if __name__ == '__main__':
    print_event_tasks_main()

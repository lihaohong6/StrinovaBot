from dataclasses import dataclass

from utils.general_utils import get_table_global
from utils.json_utils import get_game_json


@dataclass
class EventMessage:
    id: int
    group: int
    title: str
    title_display: str
    content: str


def main():
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

    message_by_group = {}
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
            content.append(f";Day {message.id}&#58; {message.title_display}")
            content.append(message.content)
        tab_contents.append("\n".join(content))
    print("{{Tab/tabs | group=story_by_type | " + " | ".join(tab_titles) + " }}")
    print("{{Tab/content | group=story_by_type | " + " | ".join(tab_contents) + " }}")


if __name__ == '__main__':
    main()

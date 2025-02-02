from story.story_parser import parse_raw_events, Story
from story.story_preprocessor import get_raw_events
from utils.general_utils import get_table_global
from utils.upload_utils import process_uploads


def story_to_template(story) -> str:
    result = ["{{Story"]
    for i, event in enumerate(story.rows, 1):
        data: dict[str, str | int] = event.data
        args = []
        for k, v in data.items():
            key = f'{k}{i}' if "{}" not in k else k.format(str(i))
            args.append(f"|{key}={v}")
        result.append("\n".join(args))
    result.append("}}")
    return "\n\n".join(result)


def perform_story_uploads(story: Story) -> None:
    image_uploads = []
    existing: set[str] = set()
    for req in story.background_images:
        if req.target in existing:
            continue
        existing.add(req.target)
        image_uploads.append(req)
    process_uploads(image_uploads)


def parse_event_stories():
    table = get_table_global("Cinematic/AVGEvent/AVGEvent_Activity")
    event_starts, predecessors, successors = get_event_start_ids(table)
    event_lists = event_bfs(event_starts, successors, table)
    for event_list in event_lists:
        if str(list(event_list)[0]).startswith("1042"):
            raw_events = get_raw_events(event_list, predecessors)
            story = parse_raw_events(raw_events)
            template_string = story_to_template(story)
            perform_story_uploads(story)
            print(template_string)



def get_event_start_ids(table):
    predecessors: dict[int, list[int]] = {}
    successors: dict[int, list[int]] = {}
    for event_id, v in table.items():
        lst = v["NextEventIds"]
        assert len(lst) >= 1, lst
        for next_id in lst:
            if next_id not in predecessors:
                predecessors[next_id] = []
            predecessors[next_id].append(event_id)
        successors[event_id] = v["NextEventIds"]
    event_starts = []
    for event_id in table:
        if event_id not in predecessors:
            event_starts.append(event_id)
    return event_starts, predecessors, successors


def event_bfs(event_starts, successors, table):
    event_lists: list[dict[int, dict]] = []
    for start_id in event_starts:
        event_ids = []
        bfs: list[int] = []
        visited: set[int] = set()
        bfs.append(start_id)
        visited.add(start_id)
        while len(bfs) > 0:
            event_id = bfs.pop(0)
            event_ids.append(event_id)
            if event_id not in successors:
                continue
            for successor in successors[event_id]:
                if successor not in visited:
                    bfs.append(successor)
                    visited.add(successor)
        event_lists.append(dict((event_id, table[event_id]) for event_id in event_ids if event_id != 99999))
    return event_lists


if __name__ == '__main__':
    parse_event_stories()

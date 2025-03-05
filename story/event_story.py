from pathlib import Path
from typing import Callable

from audio.audio_utils import wem_to_wav, wav_to_ogg
from story.story_parser import parse_raw_events, Story
from story.story_preprocessor import get_raw_events
from utils.general_utils import get_table_global, save_page
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


def upload_story_images(stories: list[Story]) -> None:
    image_uploads = []
    existing: set[str] = set()
    for story in stories:
        for req in story.background_images:
            if req.target in existing:
                continue
            existing.add(req.target)
            image_uploads.append(req)
    process_uploads(image_uploads, redirect_dup=True)


def upload_story_audio(stories: list[Story]) -> None:
    upload_cache_dir = Path("files/temp")
    upload_cache_dir.mkdir(parents=True, exist_ok=True)
    requests = []
    # deduplicate requests
    existing: set[str] = set()
    for story in stories:
        for req in story.bgm:
            if req.target in existing:
                continue
            existing.add(req.target)
            requests.append(req)
    # convert wem to ogg
    temp_wav_file = upload_cache_dir / "temp.wav"
    for r in requests:
        original_name = r.source.name
        if original_name.endswith("ogg"):
            continue
        if original_name.endswith("wem"):
            wem_to_wav(r.source, temp_wav_file)
            wav_file = temp_wav_file
        elif original_name.endswith("wav"):
            wav_file = r.source
        else:
            raise ValueError(f"unknown file type: {original_name}")
        ogg_file = upload_cache_dir / f"{original_name}.ogg"
        wav_to_ogg(wav_file, ogg_file)
        r.source = ogg_file
    process_uploads(requests)


def perform_story_uploads(stories: list[Story]) -> None:
    upload_story_images(stories)
    upload_story_audio(stories)


def parse_event_stories():
    table = get_table_global("Cinematic/AVGEvent/AVGEvent_Activity")
    event_starts, predecessors, successors = get_event_start_ids(table)
    event_lists = event_bfs(event_starts, successors, table)
    stories: list[Story] = []
    out_dir = Path("files/out")
    out_dir.mkdir(parents=True, exist_ok=True)
    for event_list in event_lists:
        first_event_id = list(event_list)[0]
        if str(first_event_id).startswith("1042"):
            raw_events = get_raw_events(event_list, predecessors)
            story = parse_raw_events(raw_events)
            template_string = story_to_template(story)
            stories.append(story)
            with open(out_dir / f"{first_event_id}.txt", "w", encoding="utf-8") as f:
                f.write(template_string)
    perform_story_uploads(stories)


def parse_stories(table_name: str, i18n_name: str,
                  filter_function: Callable[[int], bool] = lambda x: True,
                  upload: bool = True,
                  output: Callable[[int], str] = None) -> None:
    table = get_table_global(table_name)
    event_starts, predecessors, successors = get_event_start_ids(table)
    event_lists = event_bfs(event_starts, successors, table)
    stories: list[Story] = []
    out_dir = Path("files/out")
    out_dir.mkdir(parents=True, exist_ok=True)
    for index, event_list in enumerate(event_lists, 1):
        first_event_id = list(event_list)[0]
        if not filter_function(first_event_id):
            continue
        raw_events = get_raw_events(event_list, predecessors, i18n_name)
        story = parse_raw_events(raw_events)
        template_string = story_to_template(story)
        stories.append(story)
        if output:
            # output to wiki page
            has_next = "true" if index < len(event_lists) else "false"
            page_name = output(index)
            page_text = f"{{{{StoryTop | has_next = {has_next} }}}}\n" \
                        f"{template_string}" \
                        f"{{{{StoryBottom | has_next = {has_next} }}}}\n"
            save_page(page_name, page_text)
        else:
            # output to file
            with open(out_dir / f"{first_event_id}.txt", "w", encoding="utf-8") as f:
                f.write(template_string)
    if upload:
        perform_story_uploads(stories)


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


def parse_seasonal_story(season: int) -> None:
    parse_stories(f"Cinematic/AVGEvent/AVGEvent_Season{season}",
                  f"AVGEvent_Season{season}",
                  upload=True,
                  output=lambda i: f"Story/Season_{season}/{i}")


def parse_main_stories():
    parse_seasonal_story(3)


if __name__ == '__main__':
    parse_main_stories()

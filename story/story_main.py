from typing import Callable

from audio.audio_utils import wem_to_wav, wav_to_ogg
from story.story_parser import parse_raw_events, Story
from story.story_preprocessor import get_raw_events
from utils.file_utils import local_file_dir, temp_file_dir
from utils.general_utils import get_id_by_char
from utils.json_utils import get_table_global
from utils.lang import ENGLISH
from utils.lang_utils import StringConverters
from utils.upload_utils import process_uploads
from utils.wiki_utils import save_page


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
    temp_wav_file = temp_file_dir / "temp.wav"
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
        ogg_file = temp_file_dir / f"{original_name}.ogg"
        wav_to_ogg(wav_file, ogg_file)
        r.source = ogg_file
    process_uploads(requests)


def perform_story_uploads(stories: list[Story]) -> None:
    upload_story_images(stories)
    upload_story_audio(stories)


def parse_event_stories():
    parse_stories("Cinematic/AVGEvent/AVGEvent_Activity",
                  "AVGEvent_Activity",
                  upload=False)


def parse_stories(table_name: str, i18n_name: str,
                  filter_function: Callable[[int], bool] = lambda x: True,
                  upload: bool = True,
                  output: Callable[[int, int], str] = None,
                  sorter: Callable = lambda x: x) -> list[Story]:
    table = get_table_global(table_name)
    event_starts, predecessors, successors = get_event_start_ids(table)
    event_lists = event_bfs(event_starts, successors, table)
    stories: list[Story] = []
    out_dir = local_file_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    event_lists = [event_list for event_list in event_lists if filter_function(list(event_list)[0])]
    event_lists.sort(key=(lambda el: sorter(list(el)[0])))
    for index, event_list in enumerate(event_lists, 1):
        first_event_id = list(event_list)[0]
        raw_events = get_raw_events(event_list, predecessors, i18n_name)
        story = parse_raw_events(raw_events)
        template_string = story_to_template(story)
        stories.append(story)
        if output:
            # output to wiki page
            has_next = "true" if index < len(event_lists) else "false"
            page_name = output(index, first_event_id)
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
    return stories


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
        d: dict[int, dict] = {}
        for event_id in event_ids:
            if event_id == 99999:
                continue
            if event_id not in table:
                continue
                raise RuntimeError(f"Event {event_id} not found")
            d[event_id] = table[event_id]
        event_lists.append(d)
    return event_lists


def parse_seasonal_story(season: int) -> None:
    parse_stories(f"Cinematic/AVGEvent/AVGEvent_Season{season}",
                  f"AVGEvent_Season{season}",
                  upload=True,
                  output=lambda i, story_id: f"Story/Season_{season}/{i}")


def parse_main_stories():
    for s in [2, 3]:
        parse_seasonal_story(s)


def make_character_stories():
    internal_names: dict[str, str] = {
        "Michele": "Michel",
        "Celestia": "XingHui",
        "Audrey": "Audrey",
        "Maddelena": "Maddelena",
        "Lawine": "Lawine",
        "Kokona": "KokonaShiki",
    }
    intro_stories: set[int] = set()
    final_stories: set[int] = {146101000}
    for char_name in internal_names.keys():
        char = internal_names[char_name]
        char_id = get_id_by_char(char_name)

        def key_function(story_id):
            if story_id in intro_stories:
                return 0, story_id
            if story_id in final_stories:
                return 2, story_id
            if str(story_id).startswith(f"{char_id}101"):
                return 0, story_id
            if str(story_id).startswith(f"{char_id}102"):
                return 2, story_id
            assert str(story_id).startswith(f"{char_id}20"), f"{story_id}'s priority cannot be determined"
            return 1, story_id

        stories = parse_stories(f"Cinematic/AVGEvent/AVGEvent_{char}",
                                f"AVGEvent_{char}",
                                filter_function=lambda i: str(i).startswith(f"{char_id}"),
                                upload=True,
                                output=lambda i, story_index: f"{char_name}/Story/{i}",
                                sorter=key_function)

        story_navigation: list[str] = [f"{char_name}'s personal stories:", ""]
        for index, story in enumerate(stories, 1):
            root_page = "{{ROOTPAGENAME}}"
            story_name = story.title[ENGLISH.code] if story.title else f"Episode {index}"
            story_name = StringConverters.all_caps_remove(story_name)
            story_navigation.append(f"#[[{root_page}/Story/{index}|{story_name}]]")
        story_text = "\n".join(story_navigation)
        save_page(f"{char_name}/Story", story_text)


if __name__ == '__main__':
    parse_event_stories()

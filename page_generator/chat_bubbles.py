from dataclasses import dataclass, field
from functools import cache

from utils.asset_utils import global_resources_root
from utils.json_utils import get_table, get_all_game_json
from utils.lang_utils import get_text
from utils.upload_utils import UploadRequest, process_uploads


@dataclass
class ChatBubble:
    id: int
    name: dict[str, str] = field(default_factory=dict)
    description: dict[str, str] = field(default_factory=dict)
    quality: int = 0

    @property
    def file(self):
        return f"File:Chat bubble {self.id}.png"

    @property
    def icon(self):
        return self.file


@cache
def parse_chat_bubbles() -> list[ChatBubble]:
    chat_bubble_json = get_table("ChatBubbles")
    i18n = get_all_game_json("ChatBubbles")
    result = []
    for bubble_id, v in chat_bubble_json.items():
        bubble = ChatBubble(bubble_id)
        bubble.name = get_text(i18n, v["Name"])
        bubble.description = get_text(i18n, v["Desc"])
        result.append(bubble)
    return result


def upload_chat_bubbles():
    bubbles = parse_chat_bubbles()
    uploads = []
    for bubble in bubbles:
        local_file = global_resources_root / "ChatBubbles" / "ChatBubblesIcon" / f"T_Dynamic_ChatBubblesIcon_{bubble.id}.png"
        if not local_file.exists():
            continue
        uploads.append(UploadRequest(local_file, bubble.file, '[[Category:Chat bubbles]]'))
    process_uploads(uploads)


def main():
    upload_chat_bubbles()


if __name__ == '__main__':
    main()

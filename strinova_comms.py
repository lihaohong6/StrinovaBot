import dataclasses

from pywikibot import Page

import json
from pathlib import Path
import re

from utils import csv_root, get_table, char_id_mapper, get_game_json, s

group_counter = 1
num = -1


@dataclasses.dataclass
class Node:
    node_id: str
    value: dict
    in_degree: int = 0


def parse_simple_content(value):
    # check to see if this is an emoji
    if 'SourceString' not in value['TextContent']:
        image_size = 160
        text_image = value["TextureContent"]['AssetPathName']
        emote = re.search(r"Emote_([0-9]+)", text_image)
        if emote:
            text_image = "表情 " + emote.group(1) + ".png"
        id_card = re.search(r"IdCard_([0-9]+)", text_image)
        if id_card:
            text_image = "基板 " + id_card.group(1) + ".png"
        chat_share = re.search(r"ChatShare_([0-9]+)", text_image)
        if chat_share:
            text_image = "聊天图 " + chat_share.group(1) + ".png"
            image_size = 300
        return f"[[File:{text_image}|{image_size}px]]"
    else:
        is_player = value['bIsPlayer']
        text_class = "mc-text" if is_player else "char-text"
        return '<span class{{=}}"' + text_class + '">' + value['TextContent']['SourceString'] + "</span>"


def get_i18n():
    return get_game_json()[""]


def process_file(p: Path) -> str:
    global group_counter
    i18n = get_i18n()
    obj = json.load(open(p, "r", encoding="utf-8"))[0]['Rows']
    choice_flag = False
    choice_counter = 1

    result = ["{{StrinovaComms"]

    nodes: dict[str, Node] = {}
    prev: Node | None = None
    for key in obj:
        value = obj[key]
        options_count = len(value['TextContentList']) // 2 + 1
        nodes[key] = Node(key,
                          value)
        if prev is not None:
            prev.next_id = key
        prev = nodes[key]

    for key, value in obj.items():
        jump_row = value["NormalJumpRowName"]
        jump_row_array = value["OptionalJumpRowNameArray"]
        if jump_row != "":
            if jump_row in nodes:
                nodes[jump_row].in_degree += 1
            else:
                print(f"Invalid jump target of {jump_row} in {p.name}")
        elif len(jump_row_array) >= 2:
            for target in jump_row_array:
                nodes[target].in_degree += 1
        elif len(jump_row_array) == 1:
            target = jump_row_array[0]
            if target in nodes:
                nodes[target].in_degree += 2
            else:
                print(f"Invalid jump target of {target} in {p.name}")
        elif key == "End":
            # sometimes there are mysterious rows after End
            break
        elif key != "Start":
            raise RuntimeError(f"{p}: {key}, {value}")

    line_counter = 1
    for key, node in nodes.items():
        value = node.value
        is_player = value['bIsPlayer']

        # skip dummy conversations
        if 'ECyCommunicationContentType::None' in value['ContentType'] and not is_player:
            continue

        text = value['TextContentList']
        from_id = value["FromId"]
        char_name = char_id_mapper.get(from_id)
        profile_str = f'\n|profile{line_counter}={char_name} Profile\n|name{line_counter}={char_name}' if not is_player and char_name else ""
        choice_string = ""
        if choice_flag:
            choice_string = f"\n|group{line_counter}={group_counter}\n" \
                            f"|option{line_counter}={choice_counter}"
        if len(text) == 0:
            text = [value['TextContent']]
        new_text = []
        for t in text:
            new_text.append(i18n.get(t.get('Key', ""), t.get('SourceString', "")))
        text = new_text

        if len(text) > 1:
            group_counter += 1
            line = f"|{line_counter}=reply\n" \
                   f"|group{line_counter}={group_counter}\n" + \
                   "\n".join(f"|option{line_counter}_{index + 1}={t}" for index, t in enumerate(text))
            result.append(line)
            choice_flag = True
            choice_counter = 1
            line_counter += 1
        # no text in content list, either emoji or single line response
        elif "Voice" in value['ContentType']:
            # FIXME: support me in template
            line = (f"|{line_counter}=voice\n"
                    f"|file{line_counter}={value['AkOnEvent']['AssetPathName'].split('.')[-1]}"
                    f"{profile_str}{choice_string}")
            result.append(line)
            line_counter += 1
        elif "Texture" in value['ContentType']:
            line = (f"|{line_counter}=emote\n"
                    f"|file{line_counter}={value['TextureContent']['AssetPathName'].split('_')[-1]}"
                    f"{profile_str}{choice_string}")
            result.append(line)
            line_counter += 1
        elif "GreetingCard" in value['ContentType']:
            # FIXME: finish this
            pass
        else:
            assert len(text) == 1
            text = text[0]
            if is_player:
                line = f"|{line_counter}=navigator\n|text{line_counter}={text}"
            else:
                # text response from char
                line = f"|{line_counter}=char-text\n" \
                       f"|text{line_counter}={text}{choice_string}{profile_str}"
            line_counter += 1
            result.append(line)

        if len(value['OptionalJumpRowNameArray']) > 0:
            next_node = value['OptionalJumpRowNameArray'][0]
        else:
            next_node = value["NormalJumpRowName"]
        if node.next_id != next_node:
            # skipping ahead: transitioning from option 1 to option 2
            choice_counter += 1
        elif node.in_degree >= 2 or nodes[next_node].in_degree >= 2:
            # about to merge into the same conversation
            choice_flag = False
    result.append("}}")
    return "\n\n".join(result)


def main():
    # TODO: KaChatOption.json has character favorability boosts
    ka_phone_root = csv_root.joinpath("KaPhone")
    name_mapper = {
        'HuiXing': 'Celestia'
    }
    skip = {
        "Fuchsia"
    }

    for parent in ka_phone_root.iterdir():
        if parent.is_file():
            continue
        conversation_name = parent.name.capitalize()
        conversation_name = name_mapper.get(conversation_name, conversation_name)
        if conversation_name not in char_id_mapper.values() or conversation_name in skip:
            continue
        tabs = []
        contents = []
        for file in parent.glob("*.json"):
            name = file.name.capitalize()
            tab = "?"
            last_segment = name.split("_")[-1].split(".")[0]
            if name.startswith(conversation_name):
                tab = "Friendship Lv. " + last_segment
            elif name.lower().startswith("playerbirthday"):
                tab = "Player birthday " + last_segment
            elif name.lower().startswith("birthday"):
                tab = f"{conversation_name} birthday " + last_segment
            tabs.append(tab)
            contents.append(process_file(file))
        group_string = f" group=strinova_comms_{conversation_name} | "
        result = "{{Tab/tabs| " + group_string + " | ".join(tabs) + " }}\n" + \
                 "{{Tab/content| " + group_string + "\n\n" + "\n\n|\n\n".join(contents) + "\n\n}}"

        p = Page(s, conversation_name + "/Strinova Comms")
        p.text = result
        p.save(summary="generate strinova comms")
        global group_counter
        group_counter = 1


main()
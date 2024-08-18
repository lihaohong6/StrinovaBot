import dataclasses
from itertools import takewhile

from pywikibot import Page

import json
from pathlib import Path
import re

from utils.general_utils import get_game_json, make_tab_group
from utils.asset_utils import csv_root
from utils.wiki_utils import s
from global_config import char_id_mapper

group_counter = 1
num = -1


# FIXME: implement topological sort or something similar to deal with out-of-order options
@dataclasses.dataclass
class Node:
    node_id: str
    value: dict
    next: list[str] = dataclasses.field(default_factory=list)
    group: int | None = None
    options: list[tuple[int, int]] = dataclasses.field(default_factory=list)


def find_convergence_point(conversations: dict[str, Node], start: Node) -> str | None:
    """
    When dialogue branches based on navigator's choice, find out at which point the conversation
    converges to the same lines and then modify Node::groups to match it.

    Args:
        conversations (list[dict]): all lines in this conversation
        start (dict): the node at which the conversation diverges
    """
    global group_counter
    current_group = group_counter
    group_counter += 1
    start.group = current_group
    paths: list[list[str]] = []
    for option_index, option in enumerate(start.next):
        paths.append([])
        paths[-1].append(option)
        while option in conversations and option != "End":
            next_key = conversations[option].next[0]
            if next_key not in conversations:
                return option
            next_node = conversations[next_key]
            paths[-1].append(next_node.node_id)
            option = next_node.node_id
    path_sets: list[set[str]] = [set(p for p in path) for path in paths]
    convergence = -1
    for cid in paths[0]:
        for path_set in path_sets:
            if cid not in path_set:
                break
        else:
            convergence = cid
            break
    assert convergence != -1, str(start)

    paths = [list(takewhile(lambda x: x != convergence, path)) for path in paths]
    for index, path in enumerate(paths):
        for key in path:
            node = conversations[key]
            if len(node.next) > 1:
                assert find_convergence_point(conversations, node) is None
            node.options.append((current_group, index + 1))

    return None


def get_i18n():
    return get_game_json()[""]


def process_file(p: Path) -> str:
    i18n = get_i18n()
    obj = json.load(open(p, "r", encoding="utf-8"))['Rows']

    result = ["{{StrinovaComms"]

    nodes: dict[str, Node] = {}
    for key in obj:
        value = obj[key]
        next_nodes = [t for t in value['OptionalJumpRowNameArray'] if t != ""]
        normal_jump_row_name = value['NormalJumpRowName']
        if len(value['TextContentList']) > 1 and len(next_nodes) == 1:
            next_nodes = [next_nodes[0], next_nodes[0]]

        if len(next_nodes) == 1 and normal_jump_row_name != "":
            print(f"Ambiguous jump in {key} of {p.name}. Guessing between {next_nodes[0]} and {normal_jump_row_name}")
            if normal_jump_row_name == "End" or int(normal_jump_row_name) > int(next_nodes[0]):
                next_nodes = [normal_jump_row_name]
        elif len(next_nodes) == 0:
            next_nodes = [normal_jump_row_name]
        assert len(next_nodes) > 0
        nodes[key] = Node(key,
                          value,
                          next=next_nodes)

    for key, value in nodes.items():
        if len(value.next) > 1:
            ret = find_convergence_point(nodes, value)
            if ret is not None:
                print(f"Convergence point not found in {p.name}. Reason is: {ret}.")
                return ""

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
        if len(node.options) > 0:
            assert len(node.options) == 1
            group, option = node.options[0]
            choice_string = f"\n|group{line_counter}={group}\n" \
                            f"|option{line_counter}={option}"
        if len(text) == 0:
            text = [value['TextContent']]
        new_text = []
        for t in text:
            new_text.append(i18n.get(t.get('Key', ""), t.get('SourceString', "")))
        text = new_text

        if len(text) > 1:
            assert is_player
            # note that node.next may have length 1 because both options lead to the same result
            line = (f"|{line_counter}=reply\n" +
                    f"|group_start{line_counter}={node.group}\n" +
                    "\n".join(f"|option{line_counter}_{index + 1}={t}" for index, t in enumerate(text)) +
                    choice_string)
            result.append(line)
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

    result.append("}}")
    return "\n\n".join(result)


def main():
    # TODO: KaChatOption.json has character favorability boosts
    ka_phone_root = csv_root.joinpath("KaPhone")
    name_mapper = {
        'Huixing': 'Celestia'
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
        # tab name, tab content, and sort weight; smaller is more important
        x: list[tuple[str, str, int]] = []
        for file in parent.glob("*.json"):
            name = file.name.capitalize()
            tab = "?"
            last_segment = re.search(r"\d+$", name.split("_")[-1].split(".")[0]).group(0)
            if name.startswith(conversation_name) or name.startswith(parent.name.capitalize()):
                tab = ("Friendship Lv. " + last_segment, 0 + int(last_segment))
            elif name.lower().startswith("playerbirthday"):
                tab = ("Player birthday " + last_segment, 20 + int(last_segment))
            elif name.lower().startswith("birthday"):
                tab = (f"{conversation_name} birthday " + last_segment, 10 + int(last_segment))
            processed = process_file(file)
            if processed != "":
                x.append((tab[0], processed, tab[1]))
        group_string = f" group=strinova_comms_{make_tab_group(conversation_name)} | "
        tabs, contents = zip(*[(t[0], t[1]) for t in sorted(x, key=lambda t: t[2])])
        result = "<noinclude>{{StrinovaCommsTop}}</noinclude>" + \
                 "{{Tab/tabs| " + group_string + " | ".join(tabs) + " }}\n" + \
                 "{{Tab/content| " + group_string + "\n\n" + "\n\n|\n\n".join(contents) + "\n\n}}" + \
                 "<noinclude>[[Category:Strinova Comms]]</noinclude>"

        p = Page(s, conversation_name + "/Strinova Comms")
        if p.text.strip() != result:
            p.text = result
            p.save(summary="generate strinova comms")
        global group_counter
        group_counter = 1


if __name__ == "__main__":
    main()

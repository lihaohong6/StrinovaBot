import dataclasses
import enum
import json
import re
from typing import Any

from pywikibot import Site, Page

from utils.dict_utils import MergeFunction, merge_dict2


def bwiki():
    return Site(code="bwiki")


s = Site()


def save_page(page: Page | str, text, summary: str = "update page"):
    if isinstance(page, str):
        page = Page(s, page)
    if page.text.strip() != text.strip():
        page.text = text
        page.save(summary=summary)


def dump_json(o):
    return json.dumps(o, indent=4, cls=EnhancedJSONEncoder)


def dump_minimal_json(o):
    return json.dumps(o, indent=None, separators=(',', ':'), cls=EnhancedJSONEncoder)


def obj_to_lua_string(obj):
    def lua_kv(key: Any, value: Any):
        if isinstance(key, int) or re.match(r"^\d+$", key):
            return f'[{key}]={dump_lua(value)}'
        if isinstance(key, str):
            return f'["{key}"]={dump_lua(value)}'

    def dump_lua(data):
        if type(data) is str:
            return f'"{data}"'
        if type(data) in (int, float):
            return f'{data}'
        if type(data) is bool:
            return data and "true" or "false"
        if type(data) is list:
            l = "{"
            l += ",\n".join([dump_lua(item) for item in data])
            l += "}"
            return l
        if type(data) is dict:
            t = "{"
            t += ",\n".join([lua_kv(k, v) for k, v in data.items()])
            t += "}"
            return t
        raise TypeError("Unsupported data type")
    return dump_lua(json.loads(dump_json(obj)))


def save_lua_table(page: Page | str, obj, summary: str = "update lua table"):
    lua_string = "return " + obj_to_lua_string(obj)
    if isinstance(page, str):
        page = Page(s, page)
    if page.text.strip() == lua_string.strip():
        return
    page.text = lua_string
    page.save(summary=summary)


def save_json_page(page: Page | str, obj, summary: str = "update json page", merge: bool | None | MergeFunction = False):

    if isinstance(page, str):
        page = Page(s, page)

    if page.text != "":
        original_json = json.loads(page.text)
        original = dump_json(original_json)
    else:
        original_json = {}
        original = ""
    if merge is not None and merge:
        def merge_function(s1: str | None, s2: str | None) -> str:
            if s1 is None:
                return s2
            if s2 is None:
                return s1
            def check_no_bot(string: str) -> bool:
                return re.search(r"nobot", string, re.IGNORECASE) is not None
            if check_no_bot(s1):
                return s1
            if check_no_bot(s2):
                return s2
            return s1
        obj = merge_dict2(json.loads(dump_json(obj)), original_json, merge=merge_function if merge is True else merge)
    modified = dump_json(obj)
    if original != modified:
        page.text = modified
        page.save(summary=summary)


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, enum.Enum):
            return o.value
        return super().default(o)

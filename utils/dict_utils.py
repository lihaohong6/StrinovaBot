from copy import deepcopy
from typing import Callable

from utils.string_utils import pick_string_length

MergeFunction = Callable[[str | int | None, str | int | None], str | int]


def merge_dict[K, V](a: dict[K, V], b: dict[K, V], check: bool = False, merge: Callable[[list[str]], str] = None) -> dict[K, V]:
    """
    Use b as the base dict and override with a whenever there's a conflict
    """
    result = deepcopy(b)
    for k, v in a.items():
        if isinstance(v, dict):
            if result.get(k) is None:
                result[k] = v
            else:
                result[k] = merge_dict(v, result[k])
        elif isinstance(v, str):
            if merge is not None:
                result[k] = merge([result.get(k, None), v])
            if not check or (v != "" and "NoTextFound" not in v):
                result[k] = v
        else:
            raise RuntimeError("Unexpected type")
    return result


def merge_dict2(a: dict, b: dict, merge: MergeFunction = pick_string_length) -> dict:
    """
    Use b as the base dict and override with a whenever there's a conflict (i.e. prioritize a)

    @:param merge: A function that prefers the first parameter
    """
    result = deepcopy(b)
    for k, v in a.items():
        if result.get(k) is None:
            result[k] = v
            continue
        if isinstance(v, dict):
            result[k] = merge_dict2(v, result[k], merge)
        elif isinstance(v, str) or isinstance(v, int):
            result[k] = merge(result[k], v)
        elif isinstance(v, list):
            # Can't handle lists
            continue
        elif v is not None:
            raise RuntimeError(f"Unexpected type: {type(v)}")
    return result

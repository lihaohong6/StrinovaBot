def pick_two(a: str, b: str) -> str:
    """
    Pick a string. Prefer the first one but use the second one if the first is empty.
    :param a:
    :param b:
    :return:
    """
    if a is None:
        return b
    if b is None:
        return a
    if "NoTextFound" in a:
        a = ""
    if "NoTextFound" in b:
        b = ""
    if a.strip() in {"", "?", "彩蛋"}:
        return b
    return a


def pick_string(strings: list[str]) -> str:
    i = len(strings) - 2
    while i >= 0:
        strings[i] = pick_two(strings[i], strings[i + 1])
        i -= 1
    return strings[0]


def pick_string_length(a: str, b: str) -> str:
    if a is None:
        return b
    if b is None:
        return a
    if "NoTextFound" in a:
        return b
    if "NoTextFound" in b:
        return a
    if "nobot" in a.lower():
        return a
    if "nobot" in b.lower():
        return b
    if len(a) > len(b):
        return a
    return b

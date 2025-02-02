import re
from dataclasses import dataclass
from typing import Callable

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from utils.lang import Language, LanguageVariants, ENGLISH, get_language, CHINESE
from utils.wiki_utils import s

print(f"Current language: {get_language().code}")

char_name_table: dict[str, dict[int, str]] = {
    LanguageVariants.JAPANESE.value.code: {
        120: 'フラグランス',
        110: '白墨',
        137: '香奈美',
        205: 'ガラテア',
        132: '明',
        124: 'ココナ'
    }
}


def from_lang_code(lang_code: str) -> Language | None:
    for lang in LanguageVariants:
        if lang.value.code == lang_code:
            return lang.value
    return None


def title_to_lang(title: str) -> Language:
    if "/" in title:
        res = from_lang_code(title.split("/")[-1])
        if res is None:
            return ENGLISH
        return res
    return ENGLISH


@dataclass
class RedirectRequest:
    lang: Language
    source: str
    target: str


def redirect_pages(requests: list[RedirectRequest]):
    existing_sources = dict((p.title(), p) for p in PreloadingGenerator(Page(s, r.source) for r in requests))
    for request in requests:
        p = existing_sources[request.source]
        if p.exists():
            continue
        p.set_redirect_target(Page(s, f"{request.target}{request.lang.page_suffix}"), create=True, force=True)


StringConverter = Callable[[str], str]


def compose(f1: StringConverter, f2: StringConverter) -> StringConverter:
    return lambda x: f2(f1(x))


def all_caps_remove(original: str) -> str:
    lower = original.lower()

    diff = 0
    for i in range(0, len(original)):
        diff += 1 if original[i] != lower[i] else 0
    if diff < len(original) / 2:
        return original

    def upper(match: re.Match) -> str:
        return str(match.group(0).upper())

    return re.subn(r"(^| ).", lambda y: upper(y), lower)[0]


class StringConverters:
    no_text_found: StringConverter = lambda x: x if "NoTextFound" not in x else ""
    remove_extra_line_space: StringConverter = lambda string: "\n".join(x.strip() for x in string.split("\n"))
    basic_converter: StringConverter = compose(no_text_found, remove_extra_line_space)
    newline_to_br: StringConverter = lambda x: x.replace("\n", "<br>")
    double_newline: StringConverter = lambda x: x.replace("\n", "\n\n")
    all_caps_remove: StringConverter = all_caps_remove


def get_multilanguage_dict(i18n: dict[str, dict], key: str | list[str] | None, default: str = None,
                           converter: StringConverter = StringConverters.basic_converter,
                           extra: str | None = None) -> dict[str, str]:
    """

    :param i18n:
    :param key: For multi-level keys
    :param default: Default string value when no localization is found
    :param converter: Postprocessor for the resulting string
    :param extra: Chinese text extracted directly from game files
    :return:
    """
    result: dict[str, str] = {}
    if extra is not None:
        result[CHINESE.code] = converter(extra)
    if key is None:
        return result
    if isinstance(key, str):
        key = [key]
    for lang, v in i18n.items():
        cur = v
        for k in key:
            if cur is None:
                break
            cur = cur.get(k, None)
        if cur is not None and "NoTextFound" not in cur:
            assert isinstance(cur, str)
            result[lang] = converter(cur.strip())
        elif default is not None:
            result[lang] = converter(default)
    return result


def get_text(i18n, d: dict) -> dict[str, str] | None:
    if d is None or "Key" not in d:
        return None
    key = d["Key"]
    return get_multilanguage_dict(i18n, key, extra=d["SourceString"])

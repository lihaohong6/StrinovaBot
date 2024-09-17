from dataclasses import dataclass

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from utils.json_utils import get_game_json
from utils.lang import Language, LanguageVariants, ENGLISH, get_language
from utils.wiki_utils import s

print(f"Current language: {get_language().code}")

char_name_table = {
    LanguageVariants.JAPANESE.value.code: {
        120: 'フラグランス',
        205: 'ガラテア'
    }
}


def get_localized_char_name(char_id: int, lang: Language = get_language()) -> str | None:
    char_id = int(char_id)
    if lang.code in char_name_table:
        t = char_name_table[lang.code]
        if char_id in t:
            return t[char_id]
    return get_game_json(language=lang)['RoleProfile'].get(f'{char_id}_NameEn', None)


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

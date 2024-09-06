from dataclasses import dataclass
from enum import Enum

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from utils.wiki_utils import s


@dataclass
class Language:
    code: str

    @property
    def page_suffix(self):
        if self.code != 'en':
            return f"/{self.code}"
        return ""

    @property
    def json_suffix(self):
        if self.code != 'en':
            return f"_{self.code}"
        return ""

    @property
    def game_json_dir(self):
        return self.code


class LanguageVariants(Enum):
    ENGLISH = Language('en')
    JAPANESE = Language('ja')
    KOREAN = Language('ko')
    SIMPLIFIED_CHINESE = Language('zh-Hans')


ENGLISH: Language = LanguageVariants.ENGLISH.value

def get_language() -> Language:
    return LanguageVariants.JAPANESE.value


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

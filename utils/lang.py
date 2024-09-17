from dataclasses import dataclass
from enum import Enum


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

current_language: Language = LanguageVariants.JAPANESE.value


def get_language() -> Language:
    return current_language


def set_language(code: str):
    global current_language
    for lang in LanguageVariants:
        if lang.value.code == code:
            current_language = lang.value
            break
    else:
        raise RuntimeError(f"Fail to set language to {code}")

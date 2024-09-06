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


def get_language() -> Language:
    return LanguageVariants.JAPANESE.value

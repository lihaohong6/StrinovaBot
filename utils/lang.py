from dataclasses import dataclass
from enum import Enum


@dataclass
class Language:
    code: str
    name: str

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
        special = {
            'es': 'es-419',
            'zh-hans': 'zh-Hans',
            'pt-br': 'pt-BR',
        }
        return special.get(self.code, self.code)

    @property
    def audio_code(self):
        if self.code == JAPANESE.code:
            return 'jp'
        return self.code


    @property
    def audio_dir_name(self):
        return self.name

    @property
    def mw_code(self):
        return self.code

    @property
    def iso_code(self):
        if self.code == 'cn':
            return 'zh'
        return self.code


class LanguageVariants(Enum):
    ENGLISH = Language('en', 'English')
    JAPANESE = Language('ja', 'Japanese')
    KOREAN = Language('ko', 'Korean')
    SPANISH = Language('es', 'Spanish')
    FRENCH = Language('fr', 'French')
    GERMAN = Language('de', 'German')
    RUSSIAN = Language('ru', 'Russian')
    PORTUGUESE = Language('pt-br', 'Portuguese')
    SIMPLIFIED_CHINESE = Language('zh-hans', 'Simplified Chinese')


CHINESE: Language = Language('cn', 'Chinese')
ENGLISH: Language = LanguageVariants.ENGLISH.value
JAPANESE: Language = LanguageVariants.JAPANESE.value
KOREAN: Language = LanguageVariants.KOREAN.value

available_languages = [l.value for l in LanguageVariants]

current_language: Language = LanguageVariants.ENGLISH.value


def get_language() -> Language:
    return current_language


def set_language(code: str | Language) -> None:
    global current_language
    if isinstance(code, Language):
        current_language = code
        return
    for lang in LanguageVariants:
        if lang.value.code == code:
            current_language = lang.value
            break
    else:
        raise RuntimeError(f"Fail to set language to {code}")


def languages_with_audio() -> list[Language]:
    return [CHINESE, JAPANESE, ENGLISH]

from pywikibot import Page

from audio_utils import load_json_voices
from audio.audio_uploader import upload_audio_file
from utils.general_utils import pick_string
from audio_parser import Trigger, match_custom_triggers
from data.conversion_table import VoiceType
from global_config import char_id_mapper
from utils.lang import JAPANESE, ENGLISH, CHINESE, Language, get_language, languages_with_audio
from utils.wiki_utils import s


def make_table(triggers: list[Trigger], lang: Language):
    result = ['{{Voice/start}}']
    for t in triggers:
        for voice in t.voices:
            title = t.name.copy()
            for k, v in voice.title.items():
                title[k] = pick_string([v, title.get(k, "")])
            title_text = title.get(lang.code, title.get(ENGLISH.code, ""))
            args = [
                ("Title", title_text)
            ]

            if 'org' in voice.path:
                args.append(('Type', 'org'))
            if 'red' in voice.path:
                args.append(('Type', 'red'))

            transcription_languages = languages_with_audio()
            for transcription_language in transcription_languages:
                lang_code = transcription_language.code
                lang_name = lang_code.upper()
                file_page = voice.file_page.get(lang_code, "")
                if file_page != "":
                    args.append((f"File{lang_name}", file_page))
                    args.append((f"Text{lang_name}", voice.transcription.get(lang_code, "")))
                    args.append((f"Trans{lang_name}", voice.translation.get(lang_code, {}).get(lang.code, "")))

            result.append("{{Voice/row | " + " | ".join(f"{k}={v}" for k, v in args) + " }}")
    result.append('{{Voice/end}}')
    return "\n".join(result)


def make_character_audio_page(char_id: int, lang: Language, dry_run: bool = False):
    result = ["{{CharacterAudioTop}}"]
    char_name = char_id_mapper[char_id]
    voices = load_json_voices(char_name)
    upload_audio_file(voices, char_name, dry_run=dry_run)
    triggers = match_custom_triggers(voices)
    for voice_type in VoiceType:
        t_list = [t for t in triggers if t.type.value == voice_type.value]
        result.append(f"=={voice_type.value}==")
        table = make_table(t_list, lang)
        result.append(table)
        result.append("")
    p = Page(s, f"{char_name}/audio")
    result = "\n".join(result)
    if p.text.strip() != result.strip():
        if dry_run:
            print(f"{p.title()} changed. No edit due to dry run.")
        else:
            p.text = result
            p.save("Generate audio page")
    else:
        print(f"Skipping {p.title()}: no change")


def make_character_audio_pages():
    lang = get_language()
    for char_id, char_name in char_id_mapper.items():
        # FIXME: only do Michele for now to test
        if char_name == "Celestia":
            make_character_audio_page(char_id, lang, dry_run=True)


def main():
    make_character_audio_pages()


if __name__ == '__main__':
    main()

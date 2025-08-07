from pywikibot import Page

from audio.audio_uploader import upload_audio_file, ensure_audio_files_exist
from audio.audio_utils import Trigger
from audio_parser import match_custom_triggers
from audio_utils import load_json_voices
from data.conversion_table import VoiceType
from global_config import char_id_mapper
from utils.lang import ENGLISH, Language, get_language, languages_with_audio
from utils.string_utils import pick_string
from utils.wiki_utils import s


def make_table(triggers: list[Trigger], page_lang: Language):
    result = ['{{Voice/start}}']
    for t in triggers:
        for voice in t.voices:
            title = t.name.copy()
            for k, v in voice.title.items():
                title[k] = pick_string([v, title.get(k, "")])
            title_text = title.get(page_lang.code, title.get(ENGLISH.code, ""))
            args = [
                ("Title", title_text)
            ]

            if '_org' in voice.path:
                args.append(('Type', 'org'))
            if '_red' in voice.path:
                args.append(('Type', 'red'))

            transcription_languages = languages_with_audio()
            for transcription_language in transcription_languages:
                lang_code = transcription_language.code
                lang_name = lang_code.upper()
                file_page = voice.file_page.get(lang_code, "")
                if file_page != "":
                    args.append((f"File{lang_name}", file_page))
                    args.append((f"Text{lang_name}", voice.transcription.get(lang_code, "")))
                    args.append((f"Trans{lang_name}", voice.translation.get(lang_code, {}).get(page_lang.code, "")))

            result.append("{{Voice/row | " + " | ".join(f"{k}={v}" for k, v in args) + " }}")
    result.append('{{Voice/end}}')
    return "\n".join(result)


def make_character_audio_page(char_id: int,
                              lang: Language,
                              dry_run: bool = False,
                              upload_audio_files: bool = False,
                              force_replace: bool = False):
    result = ["{{CharacterAudioTop}}"]
    char_name = char_id_mapper[char_id]
    voices = load_json_voices(char_name)
    ensure_audio_files_exist(voices)
    if upload_audio_files:
        upload_audio_file(voices, char_name, dry_run=dry_run, force_replace=force_replace)
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
        # Be very careful with audio: do one character at a time and watch for problems in the upload.
        # Try to do a dry run to make sure everything looks alright.
        if char_name == "Audrey":
            make_character_audio_page(char_id, lang,
                                      dry_run=False,
                                      upload_audio_files=True,
                                      force_replace=False)


def main():
    make_character_audio_pages()


if __name__ == '__main__':
    main()

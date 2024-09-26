from pywikibot import Page

from audio_utils import pick_string, upload_audio_file, load_json_voices
from audio_parser import Trigger, match_custom_triggers
from data.conversion_table import VoiceType
from global_config import char_id_mapper
from utils.wiki_utils import s


def make_table(triggers: list[Trigger]):
    result = ['{{Voice/start}}']
    for t in triggers:
        for voice in t.voices:
            title = pick_string([voice.title_en, t.name_en, t.name_cn])

            title_extra = ""
            if "red" in voice.path:
                title_extra = " (legendary skin)"
            if "org" in voice.path:
                title_extra = " (dorm skin)"

            args = [
                ("Title", f"{title}{title_extra}"),
                ("FileCN", f"CN_{voice.path}.ogg"),
                ("TextCN", voice.text_cn),
                ("TextEN", voice.text_en),
            ]

            if voice.file_page_jp != "":
                args.append(("FileJP", f"JP_{voice.path}.ogg"))
                args.append(("TextJP", voice.text_jp))

            result.append("{{Voice/row | " + " | ".join(f"{k}={v}" for k, v in args) + " }}")
    result.append('{{Voice/end}}')
    return "\n".join(result)


def make_character_audio_page(char_id: int):
    result = ["{{CharacterAudioTop}}"]
    char_name = char_id_mapper[char_id]
    voices = load_json_voices(char_name)
    upload_audio_file(voices, char_name)
    triggers = match_custom_triggers(voices)
    for voice_type in VoiceType:
        t_list = [t for t in triggers if t.type.value == voice_type.value]
        result.append(f"=={voice_type.value}==")
        table = make_table(t_list)
        result.append(table)
        result.append("")
    p = Page(s, f"{char_name}/audio")
    result = "\n".join(result)
    if p.text.strip() != result.strip():
        p.text = result
        p.save("Generate audio page")
    else:
        print(f"Skipping {p.title()}: no change")

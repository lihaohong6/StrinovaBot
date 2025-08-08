import json
import re
from time import sleep

from audio_utils import get_json_path
from global_config import name_to_en, char_id_mapper, get_characters
from page_generator.translations import get_translations
from page_generator.weapons import get_weapons_by_type, WeaponType
from utils.asset_utils import wav_root_cn, audio_export_root
from utils.general_utils import camp_name_cn
from utils.json_utils import load_json
from utils.lang import ENGLISH, CHINESE, Language, LanguageVariants

def get_char_prompts(char_name: str) -> list[dict[str, str]]:
    char_prompts: dict[str, list[tuple[str, str, str]]] = {
        'Michele': [('喵喵卫士', 'Pawtector'), ('火力大喵', 'Mighty Meowblast')],
        'Celestia': [('星庇所', 'Astral Sanctuary', '星のクリニック')],
        'Audrey': [('格罗夫', 'Grove', "グローブ")],
        'Yvette': [('菲', 'Fay', 'フェイ')]
    }
    langs = ['zh-hans', 'en', 'ja']
    prompts = char_prompts.get(char_name, [])
    result = []
    for prompt_tuple in prompts:
        d = {}
        for index, string in enumerate(prompt_tuple):
            lang = langs[index]
            d[lang] = string
        result.append(d)
    return result

def get_prompt(char: str, lang: Language) -> str:
    i18n = get_translations()
    characters = get_characters()
    result = []
    code = lang.code
    # Use SC instead since cn does not exist in i18n files
    if code == CHINESE.code:
        code = LanguageVariants.SIMPLIFIED_CHINESE.value.code
    # character names
    strings = [c.name for c in characters]
    # custom strings
    strings.extend(["Navigator", "Strinova"])
    # grenades
    strings.extend(w.name_en for w in get_weapons_by_type(WeaponType.GRENADE))
    for string in strings:
        t = i18n.get(string, {}).get(code, None)
        if t is not None:
            result.append(t)
    result.extend(d[code] for d in get_char_prompts(char) if code in d)
    return ",".join(result)


def postprocess_chinese(t: str) -> str:
    if len(t) == 0:
        return t
    t = (t.replace(",", "，")
         .replace("?", "？")
         .replace(" ", "，")
         .replace("!", "！"))
    # 。！？~…—
    if t[-1] not in {'。', '？', '！', '~', '…', '—'}:
        t += "。"
    return t


def load_whisper_model():
    import whisper
    model = whisper.load_model(name="large-v3", device="cuda", download_root="models")
    return model


def transcribe_char(char_name: str, model = None, lang: Language = ENGLISH):
    json_path = get_json_path(char_name)
    assert json_path.exists()
    voices = load_json(json_path)
    prompt = get_prompt(char_name, lang)
    print(f"Prompt: {prompt}")
    if model is None:
        model = load_whisper_model()
    for voice_id, voice in voices.items():
        existing = voice['transcription'].get(lang.code, None)
        if existing is not None and existing != '':
            continue
        file = audio_export_root / lang.audio_dir_name / voice['file'].get(lang.code, "DOES_NOT_EXIST")
        if not file.exists() or file.is_dir():
            continue
        result = model.transcribe(str(file), language=lang.iso_code, patience=2, beam_size=7, prompt=prompt)
        text = result['text'].strip()
        if lang == CHINESE:
            text = postprocess_chinese(text)
        voice['transcription'][lang.code] = text
        print(text)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(voices, f, ensure_ascii=False, indent=4)


def transcribe():
    model = load_whisper_model()
    for c in char_id_mapper.values():
        transcribe_char(c, model)


def translate():
    import cohere
    co = cohere.Client(open("models/cohere.txt", "r").read())
    char_name = input("Char name?").strip()
    json_path = get_json_path(char_name)
    assert json_path.exists()
    voices = load_json(json_path)
    preamble = ("Translate from Chinese to English. " +
                " ".join(f"{k} is {v}." for k, v in (general_prompts | weapon_prompts | char_prompts[char_name]).items()))
    print("Preamble:", preamble)
    index = 0
    for v in voices.values():
        if v['text_en'].strip() != '':
            continue
        original = v['text_cn'].strip()
        if original == '':
            continue
        response: str = co.chat(
            model='command-r-plus',
            preamble=preamble,
            message=original,
            temperature=0.3,
            chat_history=[],
            prompt_truncation='AUTO',
            connectors=[{"id": "web-search"}]
        ).text
        response, _ = re.subn(r"Senior \w+", r"\1 Senpai", response)
        v['text_en'] = response
        print(response)
        sleep(1)
        index += 1
        if index % 5 == 0:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(voices, f, ensure_ascii=False, indent=4)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(voices, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    transcribe()
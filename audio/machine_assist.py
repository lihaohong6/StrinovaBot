import json
import re
from time import sleep

from whisper import Whisper

from audio_utils import get_json_path
from global_config import name_to_en
from page_generator.weapons import get_weapons_by_type
from utils.asset_utils import wav_root_cn, audio_root
from utils.general_utils import camp_name_cn
from utils.json_utils import load_json
from utils.lang import ENGLISH, CHINESE

general_prompts = dict([(k.split("·")[0], v) for k, v in name_to_en.items()] +
                       list(camp_name_cn.items()) +
                       [('引航者', 'Navigator'), ('卡拉彼丘', 'Strinova')])

char_prompts: dict[str, dict[str, str]] = {
    'Michele': {'喵喵卫士': 'Pawtector', '火力大喵': 'Mighty Meowblast', '搜查官': 'Inspector'},
    'Celestia': {'星庇所': 'Astral Sanctuary'},
    'Audrey': {'格罗夫': 'Grove'},
    'Yvette': {'菲': 'Fay'}
}


weapon_prompts: dict[str, str] = dict((w.name_cn, w.name_en) for w in get_weapons_by_type("Grenade"))


def postprocess_chinese(t: str) -> str:
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


def transcribe_char(char_name: str, model: Whisper | None = None):
    json_path = get_json_path(char_name)
    assert json_path.exists()
    voices = load_json(json_path)
    prompt = ",".join(list(general_prompts.values()) + list(char_prompts.get(char_name, {}).values()))
    lang = ENGLISH
    print(f"Prompt: {prompt}")
    if model is None:
        model = load_whisper_model()
    for voice_id, voice in voices.items():
        existing = voice['transcription'].get(lang.code, None)
        if existing is not None and existing != '':
            continue
        file = audio_root / lang.audio_dir_name / voice['file'].get(lang.code, "DOES_NOT_EXIST")
        if not file.exists() or file.is_dir():
            continue
        result = model.transcribe(str(file), language=lang.code, patience=2, beam_size=5, prompt=prompt)
        text = result['text'].strip()
        if lang == CHINESE:
            text = postprocess_chinese(text)
        voice['transcription'][lang.code] = text
        print(text)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(voices, f, ensure_ascii=False, indent=4)


def transcribe():
    model = load_whisper_model()
    for c in ['Audrey', 'Flavia', 'Bai Mo', 'Fuchsia', 'Kanami', 'Kokona', 'Lawine', 'Maddelena', 'Meredith', 'Ming', 'Nobunaga', 'Reiichi', 'Yvette']:
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
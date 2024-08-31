import json
import re
from pathlib import Path
from time import sleep

import cohere

from audio.audio_utils import get_json_path
from global_config import char_id_mapper, name_to_en
from utils.asset_utils import wav_root_cn
from utils.general_utils import load_json, camp_name_cn

general_prompts = dict([(k.split("·")[0], v) for k, v in name_to_en.items()] +
                       list(camp_name_cn.items()) +
                       [('引航者', 'Navigator'), ('卡拉彼丘', 'Strinova')])

char_prompts: dict[str, dict[str, str]] = {
    'Michele': {'喵喵卫士': 'Pawtector', '火力大喵': 'Mighty Meowblast', '搜查官': 'Inspector'}
}


def postprocess_chinese(t: str) -> str:
    t = (t.replace(",", "，")
         .replace("?", "？")
         .replace(" ", "，")
         .replace("!", "！"))
    # 。！？~…—
    if t[-1] not in {'。', '？', '！', '~', '…', '—'}:
        t += "。"
    return t


def transcribe():
    import whisper
    model = whisper.load_model(name="large-v3", device="cuda", download_root="models")
    char_name = input("Char name?").strip()
    json_path = get_json_path(char_name)
    assert json_path.exists()
    voices = load_json(json_path)
    prompt = ",".join(list(general_prompts.keys()) + list(char_prompts[char_name].keys()))
    print(f"Prompt: {prompt}")
    for voice_id, voice in voices.items():
        if voice['text_cn'] != '':
            continue
        cn_file = wav_root_cn / voice['file_cn']
        result = model.transcribe(str(cn_file), language="zh", patience=2, beam_size=5, prompt=prompt)
        text = result['text']
        text = postprocess_chinese(text)
        voice['text_cn'] = text
        print(text)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(voices, f, ensure_ascii=False, indent=4)


def translate():
    co = cohere.Client(open("models/cohere.txt", "r").read())
    char_name = input("Char name?").strip()
    json_path = get_json_path(char_name)
    assert json_path.exists()
    voices = load_json(json_path)
    preamble = ("Translate from Chinese to English. " +
                " ".join(f"{k} is {v}." for k, v in (general_prompts | char_prompts[char_name]).items()))
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

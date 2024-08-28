import json
from pathlib import Path

from audio.audio_utils import get_json_path
from global_config import char_id_mapper, name_to_en
from utils.asset_utils import wav_root_cn
from utils.general_utils import load_json, camp_name_cn

general_prompts = (list(name.split("·")[0] for name in name_to_en.keys()) +
                   list(camp_name_cn.keys()) +
                   ['引航者', '卡拉彼丘'])

char_prompts: dict[str, list[str]] = {
    'Michele': ['喵喵卫士', '火力大喵', '搜查官']
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
    prompt = ",".join(general_prompts + char_prompts[char_name])
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

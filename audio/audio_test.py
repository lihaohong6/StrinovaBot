import os
from pathlib import Path

from pywikibot import FilePage

from audio.audio_parser import parse_role_voice, in_game_triggers, role_voice, in_game_triggers_upgrade, \
    match_custom_triggers
from audio.audio_utils import compute_audio_distance, load_json_voices
from audio.data.conversion_table import voice_conversion_table
from global_config import internal_names
from utils.asset_utils import audio_root, wav_root_cn
from utils.file_utils import cache_dir
from utils.general_utils import download_file
from utils.lang import languages_with_audio, CHINESE
from utils.wiki_utils import s


def test_audio_similarity():
    targets = [
        "CN_Vox_Michele_BPCHAR_065", # same
        "EN_Vox_Michele_BPCHAR_018", # same
        "EN_Vox_Michele_BPCHAR_019", # diff
        "EN_Vox_Michele_BPCHAR_020", # diff
        "EN_Vox_Ming_BPCHAT_143.", # diff
    ]
    voices = load_json_voices('Michele') + load_json_voices('Ming')
    download_dir = cache_dir
    for v in voices:
        for lang in languages_with_audio():
            file_page_title = v.get_file_page(lang)
            if file_page_title == "":
                continue
            file_page = FilePage(s, "File:" + file_page_title)
            local_path = audio_root / lang.audio_dir_name / v.file[lang.code]
            if any(string in file_page_title for string in targets):
                temp_file = download_dir / file_page_title
                if not temp_file.exists():
                    download_file(file_page.get_file_url(), temp_file)
                result = compute_audio_distance(local_path, temp_file)
                print(f"Comparing {file_page_title}: {result}")


def test_audio_number_sequence():
    voices = role_voice()
    triggers = in_game_triggers()
    upgrades = in_game_triggers_upgrade()
    custom_triggers = match_custom_triggers(list(voices.values()))
    can_be_triggered: set[int] = set()
    missing_1 = 0
    for t in triggers + upgrades + custom_triggers:
        for vid in t.voice_id:
            can_be_triggered.add(vid)
            if vid not in voices:
                # print(f"{vid} can be triggered by {t} but is not in a voice file")
                missing_1 += 1
        # if hasattr(t, "voices"):
        #     for v in t.voices:
        #         if v.id[0] in can_be_triggered:
        #             print(t.id, t.description_cn, "is a duplicate trigger")
        #         can_be_triggered.add(v.id[0])

    nums = [num for table in voice_conversion_table.values() for num in table.keys()]

    missing_2 = 0
    orphans = []
    for k, v in voices.items():
        # if k in can_be_triggered:
        #     continue
        # if v.name_cn != "":
        #     continue
        if v.path.startswith("Vox_") and v.path.split("_")[1] in internal_names:
            for c in nums:
                if c in v.path:
                    break
            else:
                # print(f"Orphan voice: {v}")
                missing_2 += 1
                orphans.append(v)
        else:
            missing_2 += 1
            orphans.append(v)
    print(f"Missing voice files: {missing_1}. Missing trigger {missing_2}")
    voices_non_orphan = [v for k, v in voices.items() if k in can_be_triggered]
    print(f"Non-orphan voice-lines: {len(voices_non_orphan)}")
    print("\n".join(str(o) for o in orphans))

    # TODO:
    #  Role.json: UnlockVoiceId, AppearanceVoiceId, EquipSecondWeaponVoiceId, EquipGrenadeVoiceId
    exists = set()
    while True:
        cond = input("Cond: ")
        for v in voices.values():
            conditions = ["Birthday_" + cond.strip()]
            if any(c in v.path for c in conditions):
                if v.path in exists:
                    continue
                exists.add(v.path)
                print(v.path + "    " + v.file[CHINESE.code])
                os.startfile(wav_root_cn / v.file[CHINESE.code])


if __name__ == "__main__":
    test_audio_number_sequence()
else:
    raise ImportError("Do not import this module. Run it directly instead.")
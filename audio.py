import re

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from asset_utils import audio_root, audio_event_root, wav_root
from utils import get_table, get_game_json


def audio_convert():
    output_root = Path("files/audio")
    output_root.mkdir(exist_ok=True, parents=True)
    for file in audio_root.rglob("*.txtp"):
        file_name = file.name
        out_path = output_root.joinpath(file.relative_to(audio_root))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path = out_path.parent.joinpath(file_name.replace(".txtp", ".wav"))
        subprocess.call(["vgmstream-cli.exe", file, "-o", out_path], stdout=open(os.devnull, 'wb'))


@dataclass
class Voice:
    id: int
    role_id: int
    quality: int
    name_cn: str = ""
    name_en: str = ""
    text_cn: str = ""
    text_en: str = ""
    path: str = ""
    file: str = ""


@dataclass
class Trigger:
    id: int
    description_cn: str
    description_en: str
    voice_id: list[int]
    role_id: int


@dataclass
class UpgradeTrigger:
    trigger: int
    voice_id: list[int]
    skins: list[int]


sid_to_ix: dict[str, str] = {}
bank_name_to_files: dict[str, list[Path]] = {}


def find_audio_file(file_name: str) -> str | None:
    assert len(sid_to_ix) > 0
    event_file = audio_event_root / f"{file_name}.json"
    if not event_file.exists():
        # print(event_file.name + " does not exist")
        return None
    data = json.load(open(event_file, "r", encoding="utf-8"))["Properties"]
    bank_name = data["RequiredBank"]["ObjectName"].split("'")[1]
    short_id = str(data["ShortID"])
    if short_id not in sid_to_ix:
        # print(f"Short ID {short_id} is not in conversion table")
        return None
    ix = int(sid_to_ix[short_id])
    candidates = []
    if bank_name not in bank_name_to_files:
        # print(f"No file corresponding to bank name " + bank_name)
        return None
    for f in bank_name_to_files[bank_name]:
        if f"-{ix:04d}-" in f.name:
            candidates.append(f)
    if len(candidates) == 0:
        # print(f"No audio file found for {file_name} and bank {bank_name}")
        return None
    return candidates[0].name


def parse_banks_xml():
    cn_bank_file = audio_root / "banks/cn_banks.xml"
    assert cn_bank_file.exists()
    lines = open(cn_bank_file, "r", encoding="utf-8").readlines()
    ix = None
    sid = None
    for line in lines:
        if "ix=" in line:
            ix = re.search(r'ix="(\d+)"', line).group(1)
        if 'ty="sid"' in line:
            sid = re.search(r'va="(\d+)"', line).group(1)
            if ix is not None:
                sid_to_ix[sid] = ix


def map_bank_name_to_files(p: Path):
    for f in p.iterdir():
        bank_name = f.name.split("-")[0]
        if bank_name not in bank_name_to_files:
            bank_name_to_files[bank_name] = []
        bank_name_to_files[bank_name].append(f)


def get_text(i18n, v):
    name_obj = v['VoiceName']
    key = name_obj.get("Key", None)
    if key is not None:
        name_cn = name_obj["SourceString"]
    else:
        name_cn = ""
    name_en = i18n.get(key, "")
    content_obj = v['Content']
    key = content_obj.get("Key", None)
    if key is not None:
        content_cn = content_obj["SourceString"]
    else:
        content_cn = ""
    content_en = i18n.get(key, "")
    return content_cn, content_en, name_cn, name_en


def in_game_triggers() -> list[Trigger]:
    i18n = get_game_json()['InGameVoiceTrigger']
    table = get_table("InGameVoiceTrigger")
    result: list[Trigger] = []
    for k, v in table.items():
        description_cn = v['Desc']['SourceString']
        description_en = i18n.get(v['Desc']['Key'], "")
        role_id: int = v['RoleId']
        voice_id: list[int] = [v['VoiceId']]
        if "RandomVoiceIds" in v:
            lst = v["RandomVoiceIds"]
            if len(lst) > 0:
                assert v['IsRandom']
                voice_id = lst
        result.append(Trigger(k, description_cn, description_en, voice_id, role_id))
    return result


def in_game_triggers_upgrade() -> list[UpgradeTrigger]:
    table = get_table("InGameVoiceUpgrade")
    result: list[UpgradeTrigger] = []
    for k, v in table.items():
        trigger: int = v["TriggerInGameVoiceId"]
        voice_id: list[int] = v["RandomVoiceIdList"]
        skins: list[int] = v["RoleSkinIdList"]
        result.append(UpgradeTrigger(trigger, voice_id, skins))
    return result


def role_voice() -> dict[int, Voice]:
    parse_banks_xml()
    map_bank_name_to_files(wav_root)
    i18n = get_game_json()['RoleVoice']
    voice_table = get_table("RoleVoice")

    voices = {}
    for k, v in voice_table.items():
        content_cn, content_en, name_cn, name_en = get_text(i18n, v)

        path = v["AkEvent"]["AssetPathName"].split(".")[-1]
        file = find_audio_file(path)
        if file is None:
            continue

        voice = Voice(id=k,
                      role_id=v['RoleId'],
                      quality=v['Quality'],
                      name_cn=name_cn,
                      name_en=name_en,
                      text_cn=content_cn,
                      text_en=content_en,
                      path=path,
                      file=file)
        voices[k] = voice

    return voices


def main():
    voices = role_voice()
    triggers = in_game_triggers()
    upgrades = in_game_triggers_upgrade()
    can_be_triggered: set[int] = set()
    missing_1 = 0
    for t in triggers + upgrades:
        for vid in t.voice_id:
            can_be_triggered.add(vid)
            if vid not in voices:
                # print(f"{vid} can be triggered but is not in a voice file")
                missing_1 += 1
    missing_2 = 0
    orphans = []
    for k, v in voices.items():
        if k in can_be_triggered:
            continue
        if v.name_cn != "":
            continue
        for c in comm:
            if c in v.path:
                break
        else:
            for b in bp_char:
                if f"BPCHAR_{b}" in v.path or f"BPCHAT_{b}" in v.path:
                    break
            else:
                print(f"Orphan voice: {v}")
                missing_2 += 1
                orphans.append(v)
    print(f"Missing voice files: {missing_1}. Missing trigger {missing_2}")
    voices_non_orphan = [v for k, v in voices.items() if k in can_be_triggered]
    print(f"Non-orphan voice-lines: {len(voices_non_orphan)}")

    # TODO:
    #  Role.json: UnlockVoiceId, AppearanceVoiceId, EquipSecondWeaponVoiceId, EquipGrenadeVoiceId
    exists = set()
    for v in voices.values():
        conditions = ["_155"]
        if any(c in v.path for c in conditions):
            if v.path in exists:
                continue
            exists.add(v.path)
            print(v.path + "    " + v.file)
            os.startfile(wav_root / v.file)


no_prefix: dict[str, str] = {
    "700": "生日贺卡",
    "701": "生日蛋糕",
    "702": "生日回礼",
    "703": "生日礼物",
}

comm: dict[str, str] = {
    "COM_081": "进攻",
    "COM_082": "等待",
    "COM_083": "撤退",
    "COM_084": "谢谢",
    "COM_085": "称赞",
    "COM_086": "是",
    "COM_087": "否",
    "COM_088": "抱歉",
    "COM_089": "你好",
    "COM_090": "手榴弹",
    "COM_091": "拦截者",
    "COM_092": "烟雾弹",
    "COM_093": "闪光弹",
    "COM_094": "治疗雷",
    "COM_095": "风场雷",
    "COM_096": "减速雷",
    "COM_097": "警报器",
    "COM_103": "这里可以安装炸弹",
    "COM_105": "这里有子弹",
    "COM_106": "这里有护甲",
    "COM_107": "这里有战术道具",
    "COM_151": "警报器发现敌人"
}

bp_char: dict[str, str] = {

    "018": "获得角色",
    "021": "装备战术道具",

    "019": "当天第一次进入休息室",  # 休息室是什么？

    # dorm
    "008": "早上问候",
    "009": "晚间问候",
    "010": "深夜问候",

    "001": "点击互动",
    "002": "点击互动",
    "003": "点击互动",
    "004": "摸头",

    "005": "收到邮件",

    "011": "玩家生日",
    "012": "角色生日",

    "006": "朋友生日",
    "007": "朋友生日",

    "013": "元旦",
    "014": "春节",
    "015": "圣诞节",
    "016": "情人节",
    "017": "卡拉彼丘纪念日",
    "065": "七夕",
    "023": "打招呼",
    "024": "赠送角色礼物",
    "025": "好感度上升后触碰",
    "026": "好感度上升后触碰",
    "027": "好感度上升后触碰",
    "028": "好感度上升后触碰",
    "029": "好感度上升后触碰",
    "030": "战斗胜利",
    "031": "战斗胜利MVP",
    "032": "战斗失败",
    "033": "战斗失败SVP",
    "034": "玩家生日",
    "035": "好感提升后交谈",
    "036": "好感提升后交谈",
    "037": "好感提升后交谈",
    "038": "好感提升后交谈",
    "039": "打招呼",
    "040": "打招呼",
    "041": "打招呼",
    "042": "打招呼",
    "043": "打招呼",
    "044": "自言自语",
    "045": "自言自语",
    "046": "自言自语",
    "047": "自言自语",
    "048": "自言自语",
    "049": "打断角色状态",
    "050": "打断角色状态",
    "051": "打断角色状态",
    "052": "打断角色状态",
    "053": "打断角色状态",
    "054": "近景交谈",
    "055": "近景交谈",
    "056": "感谢礼物",
    "057": "感谢专属礼物",
    "058": "近景交谈（进入房间后互动触发）",
    "059": "互动交谈",
    "060": "互动交谈",
    "061": "互动交谈",
    "062": "互动交谈",
    "063": "互动交谈",
    "064": "好感度10语音",

    # 战斗
    "066": "选择角色",
    # "067": "确认准备",
    "068": "开场台词",
    "069": "开场台词",
    "070": "开场台词",
    "137": "失败",
    "138": "胜利",
    "139": "失败SVP",
    "140": "胜利MVP"
}

if __name__ == "__main__":
    main()

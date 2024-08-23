from enum import Enum


class VoiceType(Enum):
    DORM = "Dorm"
    BATTLE = "Battle"
    COMMUNICATIONS = "Communications",
    SYSTEM = "System",
    OTHER = "Other"


voice_conversion_table: dict[VoiceType, dict[str, str]] = {
    VoiceType.DORM: {
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

        "152": "?",
        "153": "?",
        "154": "?",
        "155": "生气",
        "156": "安慰玩家",
        "157": "?",
        "158": "?",
        "159": "?",
        "160": "?",
        "161": "?",
        "162": "?",
        "163": "?",
        "164": "?",
        # no prefix
        "700": "生日贺卡",
        "701": "生日蛋糕",
        "702": "生日回礼",
        "703": "讨论生日礼物",
        "704": "收到生日礼物",
        "705": "收到礼物"
    },
    VoiceType.BATTLE: {
        "066": "选择角色",
        "067": "确认准备",
        "068": "开场台词",
        "069": "开场台词",
        "070": "开场台词",
        "071": "Q技能冷却完毕",
        "072": "主动技能",
        "073": "主动技能",
        "074": "主动技能",
        "075": "被动生效",
        "076": "大招充能完毕",
        "077": "释放大招",
        "078": "释放大招",
        "079": "释放大招",
        "080": "大招无法使用",
        "108": "受击",
        "109": "击杀敌人",
        "110": "击杀敌人",
        "111": "击杀敌人",
        "112": "击杀敌人",
        "113": "击杀敌人",
        "114": "击杀敌人",
        "115": "双杀",
        "116": "三杀",
        "117": "四杀",
        "118": "五杀",
        "119": "超神",
        "120": "复仇",
        "121": "被击杀",
        "122": "倒地时间结束后死亡",
        "123": "被武士刀击倒",
        "124": "危险区域死亡",
        "125": "摔死",
        "126": "击倒敌人",
        "127": "被击倒",
        "128": "向队友求救",
        "129": "救助队友",
        "130": "被队友扶起",
        "131": "安装炸弹",
        "132": "捡起炸弹",
        "133": "开始拆除炸弹",
        "134": "丢弃炸弹",
        "135": "发现已被安装的炸弹",
        "136": "飞行",
        "137": "失败",
        "138": "胜利",
        "139": "失败SVP",
        "140": "胜利MVP",
        "141": "彩蛋",
        "142": "彩蛋",
        "143": "彩蛋",
        "144": "彩蛋",
        "145": "彩蛋",
        "146": "彩蛋",
        "147": "彩蛋",
        "148": "彩蛋",
        "149": "彩蛋",
        "150": "彩蛋",
        "500": "击倒敌人",
        "501": "击倒敌人",
        "502": "远处有敌人",
        "503": "远处有敌人",
        "504": "近处有敌人",
        "505": "近处有敌人",
        "506": "多名敌人",
        "507": "多名敌人",
        "508": "击中敌人",
        "509": "击中敌人",
        "510": "击中敌人",
        "511": "重创敌人",
        "512": "重创敌人",
        "513": "敌人重伤",
        "514": "受到攻击",
        "515": "受到攻击",
        "516": "左侧有敌人",
        "517": "左侧有敌人",
        "518": "右侧有敌人",
        "519": "右侧有敌人",
        "520": "身后有敌人",
        "521": "身后有敌人",
    },
    VoiceType.COMMUNICATIONS: {
        "081": "进攻",
        "082": "等待",
        "083": "撤退",
        "084": "谢谢",
        "085": "称赞",
        "086": "是",
        "087": "否",
        "088": "抱歉",
        "089": "你好",
        "090": "手榴弹",
        "091": "拦截者",
        "092": "烟雾弹",
        "093": "闪光弹",
        "094": "治疗雷",
        "095": "风场雷",
        "096": "减速雷",
        "097": "警报器",
        "098": "危险信号",
        "099": "我守这里",
        "100": "需要支援",
        "101": "进攻这里",
        "102": "注意这里",
        "103": "这里可以安装炸弹",
        "104": "这里有炸弹",
        "105": "这里有子弹",
        "106": "这里有护甲",
        "107": "这里有战术道具",
        "151": "警报器发现敌人"
    },
    VoiceType.SYSTEM: {

    },
    VoiceType.OTHER: {
        "022": "标题",
        "018": "获得角色",
        "020": "装备副武器",
        "021": "装备战术道具",
    }
}

from pathlib import Path

from cnstd import CnStd
from cnocr import CnOcr

from PIL import Image

from utils.general_utils import en_name_to_zh

std = CnStd()
cn_ocr = CnOcr()

root = Path(r'D:\Strinova\Skins Back')

for char in root.iterdir():
    if not char.is_dir():
        continue
    name_cn = en_name_to_zh[char.name]
    for original_file in char.glob("*.png"):
        original = Image.open(original_file)
        width, height = original.size   # Get dimensions
        left = width * 0.74
        top = height * 0.17
        right = width * 0.9
        bottom = height * 0.2
        cropped = original.crop((left, top, right, bottom))

        box_infos = std.detect(cropped, resized_shape=(1024, 100))

        for box_info in box_infos['detected_texts']:
            cropped_img = box_info['cropped_img']
            ocr_res = cn_ocr.ocr_for_single_line(cropped_img)
            result: str = ocr_res['text']
            break
        else:
            print("Error for " + char.name + "/" + original_file.name)
            continue

        replacements = ['私服', '完美', '卓越', '精致', '初始', '传说', '精敌', '精敏', '草越', '（']
        for replacement in replacements:
            if result.endswith(replacement):
                result = result.replace(replacement, "")

        target = char / f'{name_cn}时装背面-{result}.png'
        if target == original_file:
            continue
        if target.exists():
            number = 1
            while target.exists():
                number += 1
                target = char / f'{name_cn}时装背面-{result}{number}.png'
        original_file.rename(target)

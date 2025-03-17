import shutil
from dataclasses import dataclass
from pathlib import Path

from char_info.gallery import parse_skin_tables, SkinInfo
from utils.general_utils import cn_name_to_en, en_name_to_zh, en_name_to_cn
from utils.wiki_utils import save_json_page
from utils.lang import CHINESE
from utils.upload_utils import UploadRequest, process_uploads


@dataclass
class MMDModel:
    name: dict[str, str]
    char: str
    default: bool
    local_file: Path
    suffix: str | None
    author: str | None

    @property
    def file(self) -> str:
        suffix = ""
        if self.suffix:
            suffix = f"_{self.suffix}"
        return f"MMD_{self.char}_{self.name[CHINESE.code]}{suffix}.zip"


def save_mmd_json_object(models: dict[str, list[MMDModel]]) -> None:
    result = {}
    for char, models in models.items():
        result[char] = []
        models.sort(key=lambda m: (0 if m.default else 1, m.name[CHINESE.code]))
        for model in models:
            obj = {
                'name': model.name,
                'file': model.file
            }
            if model.author:
                obj['author'] = model.author
            result[char].append(obj)
    save_json_page("Module:MMD/data.json", result)


def main():
    models_root = Path("files/mmd")

    skin_table = parse_skin_tables()
    name_mapper: dict[str, str] = {}
    default_skins: dict[str, SkinInfo] = {}
    for char_name, skin_list in skin_table.items():
        for skin in skin_list:
            name_mapper[skin.name_cn] = skin
            if skin.quality == 0 and char_name not in default_skins and "套装" not in skin.name_cn:
                default_skins[char_name] = skin

    result: dict[str, list[MMDModel]] = {}

    rar_to_zip(models_root / "models")
    files = list((models_root / "models").iterdir()) + list((models_root / "user_models").rglob("*.zip"))

    for file in files:
        file: Path
        if file.suffix != ".zip":
            continue
        components = file.stem.split("_")
        char_name = cn_name_to_en(components[0])
        if char_name is None:
            print(f"{components[0]} is not a valid character name.")
            continue
        if len(components) == 1:
            skin = default_skins[char_name]
        else:
            skin = name_mapper.get(components[1], None)
            if skin is None:
                print(f"{components[1]} is not a valid skin name.")
                continue
        if char_name not in result:
            result[char_name] = []
        suffix = None if len(components) <= 2 else components[2]
        author = None
        if file.parent.name != "models":
            author = file.parent.name
        result[char_name].append(MMDModel(skin.name, char_name, skin.quality == 0, file, suffix, author))

    print(sum(len(lst) for lst in result.values()))
    uploads: list[UploadRequest] = []
    for char, models in result.items():
        for model in models:
            path = model.local_file
            assert path.exists()
            uploads.append(UploadRequest(
                path,
                model.file,
                text="[[Category:MMD Models]]",
                comment="Batch upload MMD model"
            ))
    # FIXME: perform uploads after script is finalized
    process_uploads(uploads, force=False)
    save_mmd_json_object(result)
    print(result)


def rar_to_zip(models_root: Path):
    import patoolib

    def find_files(path: Path) -> list[Path]:
        children: list[Path] = list(path.iterdir())
        if len(children) == 1 and children[0].is_dir():
            return find_files(children[0])
        return children

    temp_dir = models_root / "temp"
    old_files = list(models_root.iterdir())
    for file in old_files:
        file: Path
        if file.name.endswith(".zip"):
            continue
        elif file.name.endswith(".rar"):
            print(f"Processing {file}")
            new_file = models_root / file.name.replace(".rar", ".zip")
            temp_dir.mkdir(parents=True, exist_ok=True)
            patoolib.extract_archive(str(file), outdir=str(temp_dir))
            patoolib.create_archive(str(new_file), tuple(str(p) for p in find_files(temp_dir)))
            file.unlink()
            shutil.rmtree(temp_dir)
        elif file.is_dir() and file.name == "temp":
            continue
        else:
            raise IOError(f"File {file.name} not supported")


if __name__ == '__main__':
    main()
else:
    raise ImportError("Do not import this file. Run it directly.")
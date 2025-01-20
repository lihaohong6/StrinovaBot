import concurrent.futures
import random
import shutil
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from subprocess import Popen

sys.path.append("../..")

from audio.audio_utils import audio_is_silent
from utils.asset_utils import wem_root, global_wem_root


@dataclass
class AudioConfig:
    audio_path: Path
    bank_file: str
    output_dir: str


class SimpleProcessPool:
    SIZE_LIMIT = 128

    def __init__(self):
        self.pool: Queue[Popen] = Queue()
        self.size = 0

    def reap(self, target: int = 0):
        while self.size > target:
            process = self.pool.get()
            process.wait()
            self.size -= 1


    def submit(self, commands: list, *args, **kwargs):
        self.pool.put(subprocess.Popen(commands, *args, **kwargs))
        self.size += 1
        if self.size > self.SIZE_LIMIT:
            self.reap(self.SIZE_LIMIT)


wwiser_location = Path('wwiser.pyz')
assert wwiser_location.exists(), "Need wwiser to exist in order to run script."


def get_configs(root: Path, root_gl: Path):
    return [
        AudioConfig(root_gl / 'Chinese', 'cn_banks.xml', 'Chinese'),
        AudioConfig(root_gl / 'Japanese', 'ja_banks.xml', 'Japanese'),
        AudioConfig(root_gl / 'English', 'en_banks.xml', 'English'),
        AudioConfig(root_gl, 'sfx_banks.xml', 'sfx')
    ]


def path_name_to_priority(p: str) -> int:
    if "_original" in p:
        return 0
    if "org" in p or "red" in p:
        return 2
    return 1


def sort_audio_paths(paths: list[Path]) -> None:
    """
    Sort audio paths to prioritize original voice lines over red and org ones.
    See https://github.com/bnnm/wwiser/issues/49

    :param paths: List of bnk files.
    """
    paths.sort(key=lambda p: (path_name_to_priority(p.name), p.name))


def txtp_to_wav(source: Path, dest: Path):
    dest.mkdir(exist_ok=True, parents=True)
    processes = []
    for file in source.rglob("*.txtp"):
        file_name = file.name
        out_path = dest.joinpath(file_name.replace(".txtp", ".wav"))
        processes.append(Popen(
            ["vgmstream-cli", file, "-o", out_path.absolute()],
            stdout=subprocess.DEVNULL,
            cwd=source.parent
        ))
    for p in processes:
        p.wait()


def make_bank_file(banks_dir, config):
    paths = list(config.audio_path.glob('*.bnk'))
    sort_audio_paths(paths)
    out_string = " ".join(f'"{str(p)}"' for p in paths)
    if out_string == "":
        return
    out_file = Path(config.bank_file)
    out_string += f' --output={config.bank_file.replace(".xml", "")}'
    config_file = Path(f"wwconfig{config.bank_file}.txt")
    with open(config_file, "w") as f:
        f.write(out_string)
    subprocess.run(['python', wwiser_location, config_file])
    config_file.unlink()
    
    out_file.rename(banks_dir / config.bank_file)


def make_txtp_files(audio_dir, txtp):
    config_file = Path(
        ''.join(random.choices(string.ascii_uppercase + string.digits, k=15)) + "wwconfig.txt").absolute()
    paths = list(Path(audio_dir).glob('*.bnk'))
    sort_audio_paths(paths)
    with open(config_file, "w") as f:
        f.write("-g -go ")
        f.write(f'"txtp" ')
        f.write(" ".join(f'"{str(p.relative_to(audio_dir))}"' for p in paths))
    subprocess.run(['python', wwiser_location.absolute(), config_file],
                   cwd=audio_dir)
    config_file.unlink()


def generate_wav(audio_dir: Path, output_dir: Path):
    txtp = Path(audio_dir.absolute() / 'txtp')
    if txtp.exists():
        shutil.rmtree(txtp, ignore_errors=True)
    make_txtp_files(audio_dir, txtp)
    txtp_to_wav(txtp, output_dir)


def make_banks(configs):
    banks_dir = Path('banks')
    if banks_dir.exists():
        shutil.rmtree(banks_dir)
    banks_dir.mkdir(exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for config in configs:
            executor.submit(make_bank_file,
                            banks_dir, config)


def remove_silent_file(path: Path):
    if audio_is_silent(path):
        print(f"Removing {path.name} because it's silent.")
        path.unlink()


def main():

    # Set paths
    if len(sys.argv) > 1:
        audio_root = Path(sys.argv[1])
        audio_root_en = Path(sys.argv[2])
    else:
        audio_root = wem_root
        audio_root_en = global_wem_root
    print("Audio root " + str(audio_root))
    print("Audio root en " + str(audio_root_en))

    configs = get_configs(audio_root, audio_root_en)

    # Convert bnk files into xml banks
    make_banks(configs)

    # Reset output directories
    for config in configs:
        dir_name = config.output_dir
        shutil.rmtree(dir_name, ignore_errors=True)
        Path(dir_name).mkdir()

    # Generate WAV files
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for config in configs:
            executor.submit(generate_wav,
                            config.audio_path, Path(config.output_dir))

    # Remove all silent wav files
    all_wav_files = []
    for config in configs:
        out_path = Path(config.output_dir)
        all_wav_files.extend(out_path.glob('*.wav'))
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for file in all_wav_files:
            executor.submit(remove_silent_file,
                            file)


if __name__ == "__main__":
    main()
elif __name__ != "__mp_main__":
    raise ImportError("Do not import this module. Just run it.")

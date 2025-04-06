import os
import sys

from audio.audio_gen import make_json

SCRIPT_DIR = os.path.abspath(__file__)
sys.path.append(os.path.dirname(SCRIPT_DIR))

from audio.make_character_page import make_character_audio_pages
from audio.pull_from_miraheze import pull_from_miraheze

from sys import argv

from machine_assist import transcribe, translate


def parse_system_voice():
    """
    InGameSystemVoiceTrigger.json
    InGameSystemVoiceUpgrade.json (for Kanami)
    Files with prefix "Vox_Communicate"
    :return:
    """
    pass


def audio_main(args=None):
    if args is None:
        args = argv
    commands = {
        "push": make_character_audio_pages,
        "gen": make_json,
        "pull": pull_from_miraheze,
        "transcribe": transcribe,
        "translate": translate
    }
    commands[args[1]]()


if __name__ == "__main__":
    audio_main()

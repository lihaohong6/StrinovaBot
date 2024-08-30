import sys

from audio.audio import audio_main
from page_generator.achievements import generate_achievement_page


def main():
    commands = {
        "audio": audio_main,
        "achievements": generate_achievement_page
    }
    commands[sys.argv[1]](sys.argv[:1] + sys.argv[2:])


if __name__ == "__main__":
    main()
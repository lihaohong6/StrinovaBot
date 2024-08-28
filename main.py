import sys

from audio.audio import audio_main


def main():
    commands = {
        "audio": audio_main
    }
    commands[sys.argv[1]](sys.argv[:1] + sys.argv[2:])


if __name__ == "__main__":
    main()
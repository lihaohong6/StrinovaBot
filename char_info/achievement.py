import wikitextparser as wtp

from utils.general_utils import get_char_pages
from utils.lang import available_languages


def generate_achievements():
    for lang in available_languages:
        for char_id, char_name, p in get_char_pages(lang=lang):
            parsed = wtp.parse(p.text)

            for section in parsed.sections:
                if section.title is not None and any(s in section.title.strip() for s in ["Achievements", "Traces"]):
                    target_section = section
                    break
            else:
                print("Achievements section not found on " + char_name)
                continue

            target_section.string = "{{CharacterAchievements}}\n"
            if p.text.strip() != str(parsed).strip():
                p.text = str(parsed)
                p.save(summary="generate achievements")


def main():
    generate_achievements()


if __name__ == "__main__":
    main()

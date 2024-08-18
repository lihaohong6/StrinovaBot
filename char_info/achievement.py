import wikitextparser as wtp

from page_generator.achievements import get_achievements, achievements_to_tabs
from utils.general_utils import get_char_pages


def generate_achievements():
    achievements = get_achievements()
    for char_id, char_name, p in get_char_pages():
        parsed = wtp.parse(p.text)

        for section in parsed.sections:
            if section.title is not None and section.title.strip() in {"Achievements", "Traces"}:
                target_section = section
                break
        else:
            print("Achievements section not found on " + char_name)
            continue

        target_section.contents = achievements_to_tabs([a for a in achievements if a.role == char_id],
                                                       group=f"achievements{char_name}")
        if p.text.strip() != str(parsed).strip():
            p.text = str(parsed)
            p.save(summary="generate achievements")


def main():
    generate_achievements()


if __name__ == "__main__":
    main()

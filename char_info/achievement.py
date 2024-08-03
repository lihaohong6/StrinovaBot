from pywikibot import Page

from achievements import get_achievements, achievements_to_tabs
from wiki_utils import s
from global_config import char_id_mapper

import wikitextparser as wtp


def generate_achievements():
    achievements = get_achievements()
    for char_id, char_name in char_id_mapper.items():
        p = Page(s, char_name)
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

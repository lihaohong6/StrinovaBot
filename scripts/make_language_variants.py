import os
import re
import sys
from dataclasses import dataclass

from pywikibot import Page
from pywikibot.data.api import APIGenerator, Request, QueryGenerator, PropertyGenerator
from pywikibot.pagegenerators import GeneratorFactory

from utils.general_utils import get_char_pages
from utils.lang_utils import LanguageVariants, title_to_lang, Language, from_lang_code
from utils.wiki_utils import s


# sys.path.insert(1, os.path.join(sys.path[0], '..'))


def make_char_pages():
    lang = LanguageVariants.JAPANESE.value

    english_version = dict((char_id, p) for char_id, _, p in get_char_pages())

    for char_id, char_name, p in get_char_pages(lang=lang):
        if p.exists():
            name_ja = re.search(r"NameJP=(.*)", p.text).group(1)
            if name_ja is not None and name_ja.strip() != "":
                Page(s, name_ja).set_redirect_target(p, create=True)
                continue
        p_original = english_version[char_id]
        p.text = p_original.text
        p.save(f"new {lang.code} page")
        try:
            r = Request(s, parameters={"action": "setpagelanguage", "title": p.title(), "lang": lang.code,
                                       "token": getattr(s, 'tokens')['csrf']})
            r.submit()
        except Exception as e:
            print(e)


def make_interlanguage_links():
    @dataclass
    class LangPage:
        page: Page
        lang: Language
        neighbors: list["LangPage"]

    gen = GeneratorFactory(s)
    gen.handle_args(['-cat:Characters'])
    gen = gen.getCombinedGenerator()
    pages: dict[str, LangPage] = dict((p.title(), LangPage(p, title_to_lang(p.title()), [])) for p in gen)
    gen = PropertyGenerator(site=s, prop="langlinks", titles="|".join(p.page.title() for p in pages.values()))
    for p in gen:
        if "langlinks" not in p:
            continue
        for link in p['langlinks']:
            target = pages[link['*']]
            assert target.lang == from_lang_code(link['lang'])
            pages[p['title']].neighbors.append(target)

    parents: dict[str, LangPage] = dict(pages)

    def find(p: LangPage) -> LangPage:
        if parents[p.page.title()] == p:
            return p
        parents[p.page.title()] = find(parents[p.page.title()])
        return parents[p.page.title()]

    def union(p1: LangPage, p2: LangPage):
        p1 = find(p1)
        p2 = find(p2)
        if p1 != p2:
            parents[p1.page.title()] = p2

    for p in pages.values():
        for p2 in p.neighbors:
            union(p, p2)

    groups: dict[str, list[LangPage]] = {}
    for p in pages.values():
        group = find(p).page.title()
        if group not in groups:
            groups[group] = []
        groups[group].append(p)

    for group, page_list in groups.items():
        for p in page_list:
            changed = False
            for p2 in page_list:
                if p == p2:
                    continue
                if p2 not in p.neighbors:
                    p.page.text = p.page.text + f"\n[[{p2.lang.code}:{p2.page.title()}]]"
                    changed = True
            if changed:
                p.page.save("update ILL")


make_interlanguage_links()

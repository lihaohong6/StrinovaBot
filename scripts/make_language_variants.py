from dataclasses import dataclass

from pywikibot import Page
from pywikibot.data.api import Request, PropertyGenerator
from pywikibot.pagegenerators import GeneratorFactory, PreloadingGenerator

from global_config import char_id_mapper
from page_generator.translations import get_translations, translate

from utils.general_utils import get_char_pages
from utils.lang import Language, LanguageVariants, ENGLISH, JAPANESE, get_language
from utils.lang_utils import title_to_lang, from_lang_code
from utils.wiki_utils import s


# sys.path.insert(1, os.path.join(sys.path[0], '..'))

def get_localized_char_name(char_id: int, lang: Language = get_language()) -> str | None:
    char_id = int(char_id)
    translations = get_translations()
    char_name = char_id_mapper[char_id]
    translation = translations[char_name].get(lang.code, None)
    if translation is not None:
        return translation
    print(f"Translation not found for {char_name}")
    return None
    # Legacy translation generation method
    # if lang.code in char_name_table:
    #     t = char_name_table[lang.code]
    #     if char_id in t:
    #         return t[char_id]
    # return get_game_json(language=lang)['RoleProfile'].get(f'{char_id}_NameEn', None)


def copy_page(original: Page, target: Page, lang: Language, localized_title: str | None = None):
    if not target.exists():
        target.text = original.text
        target.save(f"new {lang.name} page")
        try:
            r = Request(s, parameters={"action": "setpagelanguage", "title": target.title(), "lang": lang.mw_code,
                                       "token": getattr(s, 'tokens')['csrf']})
            r.submit()
        except Exception as e:
            print(e)
        if localized_title is not None and localized_title.strip() != "":
            try:
                redirect = Page(s, localized_title)
                if not redirect.exists():
                    redirect.set_redirect_target(target, create=True, summary=f"redirect {lang.code} title")
            except Exception as e:
                print(e)


def make_char_pages():
    languages = [l.value
                 for l in LanguageVariants
                 if l.value not in [ENGLISH]]
    for lang in languages:
        print(f"Current language: {lang.code}")
        for subpage in ['', '/gallery']:
            english_version = dict((char_id, p) for char_id, _, p in get_char_pages(subpage_name=subpage))
            for char_id, char_name, p in get_char_pages(subpage_name=subpage, lang=lang):
                page_en = english_version[char_id]
                copy_page(page_en, p, lang, translate(page_en.title(), lang))


def copy_lang_pages():

    def is_english_page(title: str) -> bool:
        if "gallery" in title:
            return "gallery/" not in title
        return "/" not in title

    languages = [l.value
                 for l in LanguageVariants
                 if l.value not in [ENGLISH]]
    gen = GeneratorFactory()
    gen.handle_args(["-catr:Character galleries"])
    en_pages: dict[str, Page] = dict((p.title(), p)
                                     for p in gen.getCombinedGenerator(preload=True)
                                     if is_english_page(p.title()))
    for lang in languages:
        print(f"Current language: {lang.code}")
        pages = PreloadingGenerator(Page(s, f"{p}/{lang.code}") for p in en_pages)
        for p in pages:
            page_en = en_pages["/".join(p.title().split("/")[:-1])]
            copy_page(page_en, p, lang, translate(page_en.title(), lang))



def make_interlanguage_links():
    @dataclass
    class LangPage:
        page: Page
        lang: Language
        neighbors: list["LangPage"]

    gen = GeneratorFactory(s)
    gen.handle_args(['-cat:Main pages', '-cat:Character galleries', '-cat:Weapons'])
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


if __name__ == "__main__":
    copy_lang_pages()


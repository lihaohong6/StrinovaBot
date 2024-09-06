import os
import sys

from pywikibot.data.api import APIGenerator, Request

from utils.general_utils import get_char_pages
from utils.lang_utils import LanguageVariants
from utils.wiki_utils import s

# sys.path.insert(1, os.path.join(sys.path[0], '..'))

lang = LanguageVariants.JAPANESE.value

english_version = dict((char_id, p) for char_id, _, p in get_char_pages())

for char_id, char_name, p in get_char_pages(lang=lang):
    p_original = english_version[char_id]
    p.text = p_original.text
    p.save(f"new {lang.code} page")
    try:
        r = Request(s, parameters={"action": "setpagelanguage", "title": p.title(), "lang": lang.code, "token": getattr(s, 'tokens')['csrf']})
        r.submit()
    except Exception as e:
        print(e)

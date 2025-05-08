import re
from dataclasses import dataclass

from pywikibot.pagegenerators import GeneratorFactory
import wikitextparser as wtp

from utils.wiki_utils import save_json_page
from utils.wtp_utils import get_templates_by_name

@dataclass
class Guide:
    title: str
    link: str
    description: str
    category: str
    author: str
    rating: tuple[float, int]


def get_rating(text: str) -> tuple[float, int]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(text, 'html.parser')
    rating = soup.find('div', attrs={'class': 'voteboxrate'})
    if not rating:
        return 0, 0
    rating = float(rating.text)
    num_votes = soup.find('span', attrs={'class': 'rating-total'})
    if not num_votes:
        return rating, 0
    search_result = re.search(r"\d+", num_votes.text)
    if search_result:
        num_votes = int(search_result.group(0))
    elif "one" in num_votes.text:
        num_votes = 1
    else:
        num_votes = 0
    return rating, num_votes


def update_guides():
    gen = GeneratorFactory()
    gen.handle_args(["-cat:Guides", "-ns:0"])
    gen = gen.getCombinedGenerator(preload=True)
    guides = []
    for page in gen:
        parsed = wtp.parse(page.text)
        templates = get_templates_by_name(parsed, "GuideData")
        assert len(templates) == 1
        t = templates[0]

        def get(k: str) -> str:
            val = t.get_arg(k)
            if val is None:
                return ""
            return val.value.strip()

        title = get("Title")
        link = page.title(underscore=True)
        description = get("Description")
        if description == "":
            description = get("Summary")
        category = get("Category")
        author = get("Author")
        if author == "":
            author = "Wiki community"

        rating = get_rating(page.get_parsed_page())

        guides.append(Guide(title=title, link=link, description=description, category=category, author=author, rating=rating))

    save_json_page("Module:Guide/data.json", guides)

def main():
    update_guides()

if __name__ == '__main__':
    main()
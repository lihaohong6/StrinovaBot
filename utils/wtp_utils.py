from wikitextparser import Template, WikiText


def get_templates_by_name(wikitext: WikiText, name: str) -> list[Template]:
    result = []
    for t in wikitext.templates:
        if t.name.lower().strip() == name.lower():
            result.append(t)
    return result

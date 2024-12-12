from wikitextparser import Template, WikiText


def normalize_template_name(template_name: str) -> str:
    return template_name.lower().strip().replace(" ", "_")


def get_templates_by_name(wikitext: WikiText, name: str) -> list[Template]:
    result = []
    for t in wikitext.templates:
        if normalize_template_name(t.name) == normalize_template_name(name):
            result.append(t)
    return result

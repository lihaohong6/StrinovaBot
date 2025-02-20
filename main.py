from char_info.char_infobox import generate_infobox
from char_info.dorm import generate_bond_items, generate_gifts, generate_friendship_gifts
from char_info.gallery import generate_skins, generate_emotes
from char_info.skills import generate_string_energy_network, generate_skills
from char_info.story import generate_return_letter, generate_biography
from char_info.weapons import generate_weapons
from page_generator.achievements import generate_all_achievements
from page_generator.badges import upload_all_badges
from page_generator.battle_pass import make_battle_pass_seasons
from page_generator.decal import make_all_decals
from page_generator.events import save_wiki_events
from page_generator.id_card import make_id_cards
from page_generator.items import save_all_items
from page_generator.shop import make_gacha_drop_data, make_gacha_banners
from page_generator.strinova_comms import strinova_comms_main
from page_generator.translations import generate_translations
from page_generator.weapons import process_weapon_pages, process_weapon_skins, upload_weapon_white_icons
from utils.general_utils import get_char_pages2
from utils.lang import available_languages, set_language


def misc_uploads():
    upload_all_badges()
    make_all_decals()
    make_id_cards()
    upload_weapon_white_icons()


def character_info_part1():
    generate_biography()
    generate_bond_items()
    generate_return_letter()
    generate_all_achievements()
    generate_gifts()
    generate_emotes()
    generate_skins()
    generate_friendship_gifts()
    # need transition to lua?
    strinova_comms_main()


def make_all_character_info():
    character_info_part1()
    for lang in available_languages:
        set_language(lang)
        pages = get_char_pages2(lang=lang)
        originals = set(p.text for _, p in pages)

        generate_infobox(pages)
        generate_skills(pages)
        generate_string_energy_network(pages)
        generate_weapons(pages)

        for c, p in pages:
            if p.text not in originals:
                p.save(summary="Update character page")


def make_everything():
    make_all_character_info()
    generate_translations()
    save_all_items()
    save_wiki_events()
    process_weapon_pages()
    process_weapon_skins()
    misc_uploads()
    make_gacha_drop_data()
    make_gacha_banners()
    make_battle_pass_seasons()


if __name__ == "__main__":
    make_everything()
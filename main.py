import sys

from audio.audio_main import audio_main
from char_info.char_infobox import generate_infobox
from char_info.dorm import generate_bond_items, generate_gifts, generate_friendship_gifts
from char_info.gallery import generate_skins, generate_emotes
from char_info.skills import generate_string_energy_network, generate_skills
from char_info.story import generate_return_letter, generate_biography
from char_info.weapons import generate_weapons
from page_generator.achievements import generate_all_achievements
from page_generator.badges import upload_all_badges
from page_generator.decal import upload_all_decals
from page_generator.id_card import upload_all_id_cards
from page_generator.strinova_comms import strinova_comms_main
from page_generator.translations import generate_translations
from page_generator.weapons import process_weapon_pages, process_weapon_skins
from utils.lang import available_languages, set_language, LanguageVariants


def main():
    commands = {
        "audio": audio_main,
        "achievements": generate_all_achievements,
        "weapons": process_weapon_pages,
        "weapon_variant": process_weapon_skins
    }
    commands[sys.argv[1]](sys.argv[:1] + sys.argv[2:])


def misc_uploads():
    upload_all_badges()
    upload_all_decals()
    upload_all_id_cards()


def make_everything():
    generate_biography()
    generate_bond_items()
    generate_return_letter()
    generate_all_achievements()
    generate_gifts()
    generate_emotes()
    generate_skins()
    generate_translations()
    process_weapon_skins()
    generate_friendship_gifts()
    # need transition to lua?
    strinova_comms_main()
    for lang in available_languages:
        set_language(lang)
        generate_infobox()
        generate_skills()
        generate_string_energy_network()
        generate_weapons()
    misc_uploads()


if __name__ == "__main__":
    make_everything()
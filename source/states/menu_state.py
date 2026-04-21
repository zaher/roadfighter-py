from __future__ import annotations

import math
import random

import sdl2

from .. import constants as const
from ..auxiliar import multiline_text_surface2, sge_transform, surface_fader
from ..configuration import default_configuration
from ..sound import Sound_create_music, Sound_music_volume, Sound_play, Sound_release_music


def _upper_key_name(key: int) -> str:
    name = sdl2.SDL_GetKeyName(key)
    if isinstance(name, bytes):
        name = name.decode("utf-8", "ignore")
    return name.upper()


def menu_cycle(roadfighter) -> int:
    if roadfighter.state_timmer == 0:
        roadfighter.menu_effect = random.randrange(1, 4)
        roadfighter.menu_state = 0
        roadfighter.menu_timmer = 0
        roadfighter.menu_current_menu = 0
        roadfighter.menu_redefining_key = -1
        if roadfighter.S_menu_in:
            Sound_play(roadfighter.S_menu_in)
        Sound_create_music("sound/menu_theme", -1)
        roadfighter.menu_credits_timmer = 0

    if roadfighter.menu_state == 0:
        roadfighter.menu_timmer += 1
        Sound_music_volume((roadfighter.menu_timmer * 128) // const.EFFECT_LENGTH)
        if roadfighter.menu_timmer >= const.EFFECT_LENGTH:
            Sound_music_volume(128)
            roadfighter.menu_state = 1
            roadfighter.menu_timmer = 0
    elif roadfighter.menu_state == 1:
        roadfighter.menu_timmer += 1
        if roadfighter.menu_timmer >= const.TEXT_EFFECT_LENGTH:
            roadfighter.menu_state = 2
            roadfighter.menu_timmer = 0
            roadfighter.menu_item = 0
    elif roadfighter.menu_state == 2:
        if roadfighter.menu_redefining_key != -1:
            for key in roadfighter.keyboard.newly_pressed(roadfighter.old_keyboard):
                if key not in (sdl2.SDLK_ESCAPE, const.GLOBAL_QUIT_KEY):
                    roadfighter.assign_redefined_key(key)
                roadfighter.menu_redefining_key = -1
                break
        else:
            if roadfighter.keyboard[sdl2.SDLK_DOWN] and not roadfighter.old_keyboard[sdl2.SDLK_DOWN]:
                Sound_play(roadfighter.S_menu_move)
                roadfighter.menu_item += 1
            if roadfighter.keyboard[sdl2.SDLK_UP] and not roadfighter.old_keyboard[sdl2.SDLK_UP]:
                Sound_play(roadfighter.S_menu_move)
                roadfighter.menu_item -= 1
            roadfighter.menu_item = max(0, min(roadfighter.menu_nitems - 1, roadfighter.menu_item))

            selecting = (
                (roadfighter.keyboard[roadfighter.fire_key] and not roadfighter.old_keyboard[roadfighter.fire_key])
                or (roadfighter.keyboard[sdl2.SDLK_SPACE] and not roadfighter.old_keyboard[sdl2.SDLK_SPACE])
                or (roadfighter.keyboard[roadfighter.right_key] and not roadfighter.old_keyboard[roadfighter.right_key])
                or (roadfighter.keyboard[roadfighter.left_key] and not roadfighter.old_keyboard[roadfighter.left_key])
                or (roadfighter.keyboard[sdl2.SDLK_ESCAPE] and not roadfighter.old_keyboard[sdl2.SDLK_ESCAPE])
            )
            if selecting:
                if (roadfighter.keyboard[roadfighter.left_key] and not roadfighter.old_keyboard[roadfighter.left_key]) or (roadfighter.keyboard[sdl2.SDLK_ESCAPE] and not roadfighter.old_keyboard[sdl2.SDLK_ESCAPE]):
                    roadfighter.menu_item = roadfighter.menu_nitems - 1
                Sound_play(roadfighter.S_menu_select)
                if roadfighter.menu_current_menu == 0:
                    roadfighter.menu_state = 3
                    roadfighter.menu_timmer = const.TEXT_EFFECT_LENGTH
                elif roadfighter.menu_current_menu == 1:
                    if roadfighter.menu_item == 2:
                        roadfighter.game_remake_extras = not roadfighter.game_remake_extras
                    if roadfighter.menu_item == 3:
                        cfg = default_configuration()
                        roadfighter.left_key = cfg.left_key
                        roadfighter.right_key = cfg.right_key
                        roadfighter.fire_key = cfg.fire_key
                        roadfighter.left2_key = cfg.left2_key
                        roadfighter.right2_key = cfg.right2_key
                        roadfighter.fire2_key = cfg.fire2_key
                        roadfighter.game_remake_extras = cfg.game_remake_extras
                    if roadfighter.menu_item in (0, 1, 4):
                        roadfighter.menu_state = 3
                        roadfighter.menu_timmer = const.TEXT_EFFECT_LENGTH
                elif roadfighter.menu_current_menu == 2:
                    if roadfighter.menu_item == 0:
                        roadfighter.menu_redefining_key = 0  # RIGHT
                    elif roadfighter.menu_item == 1:
                        roadfighter.menu_redefining_key = 1  # LEFT
                    elif roadfighter.menu_item == 2:
                        roadfighter.menu_redefining_key = 3  # UP
                    elif roadfighter.menu_item == 3:
                        roadfighter.menu_redefining_key = 4  # DOWN
                    elif roadfighter.menu_item == 4:
                        roadfighter.menu_redefining_key = 2  # FIRE
                    if roadfighter.menu_item == 5:
                        roadfighter.menu_state = 3
                        roadfighter.menu_redefining_key = -1
                        roadfighter.menu_timmer = const.TEXT_EFFECT_LENGTH
                elif roadfighter.menu_current_menu == 3:
                    if roadfighter.menu_item == 0:
                        roadfighter.menu_redefining_key = 5  # RIGHT2
                    elif roadfighter.menu_item == 1:
                        roadfighter.menu_redefining_key = 6  # LEFT2
                    elif roadfighter.menu_item == 2:
                        roadfighter.menu_redefining_key = 8  # UP2
                    elif roadfighter.menu_item == 3:
                        roadfighter.menu_redefining_key = 9  # DOWN2
                    elif roadfighter.menu_item == 4:
                        roadfighter.menu_redefining_key = 7  # FIRE2
                    if roadfighter.menu_item == 5:
                        roadfighter.menu_state = 3
                        roadfighter.menu_redefining_key = -1
                        roadfighter.menu_timmer = const.TEXT_EFFECT_LENGTH
                else:
                    roadfighter.menu_state = 3
                    roadfighter.menu_timmer = const.TEXT_EFFECT_LENGTH
    elif roadfighter.menu_state == 3:
        roadfighter.menu_timmer -= 1
        if roadfighter.menu_timmer < 0:
            return roadfighter.resolve_menu_transition()
    elif roadfighter.menu_state == 4:
        roadfighter.menu_timmer -= 1
        if roadfighter.menu_timmer >= 0:
            Sound_music_volume((roadfighter.menu_timmer * 128) // const.EFFECT_LENGTH)
        if roadfighter.menu_timmer < 0:
            return roadfighter.resolve_menu_exit()

    roadfighter.refresh_menu_text(_upper_key_name)
    return const.MENU_STATE


def menu_draw(roadfighter, screen) -> None:
    y_position = 0.55
    if roadfighter.menu_state in (0, 4):
        roadfighter.draw_menu_effect(screen)
    elif roadfighter.menu_state in (1, 2, 3):
        roadfighter.clear_screen(screen)
        roadfighter.blit_fullscreen(roadfighter.tittle_sfc, screen)
        roadfighter.draw_menu_text(screen, y_position)

    roadfighter.draw_scrolling_credits(screen)

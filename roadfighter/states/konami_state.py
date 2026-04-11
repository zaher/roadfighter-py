from __future__ import annotations

import sdl2

from .. import constants as const
from ..auxiliar import surface_fader


def konami_cycle(roadfighter) -> int:
    if roadfighter.state_timmer == 0:
        roadfighter.konami_state = 0
        roadfighter.konami_timmer = 0

    if roadfighter.konami_state == 0:
        roadfighter.konami_timmer += 1
    if roadfighter.konami_state == 1:
        roadfighter.konami_timmer -= 1

    if roadfighter.konami_state == 0 and (
        roadfighter.state_timmer >= 350
        or (roadfighter.keyboard[roadfighter.fire_key] and not roadfighter.old_keyboard[roadfighter.fire_key])
        or (roadfighter.keyboard[sdl2.SDLK_ESCAPE] and not roadfighter.old_keyboard[sdl2.SDLK_ESCAPE])
    ):
        roadfighter.konami_state = 1
        if roadfighter.konami_timmer > const.KONAMI_FADE_TIME:
            roadfighter.konami_timmer = const.KONAMI_FADE_TIME

    if roadfighter.konami_state == 1 and roadfighter.konami_timmer <= 0:
        return const.MENU_STATE
    return const.KONAMI_STATE


def konami_draw(roadfighter, screen) -> None:
    roadfighter.blit_fullscreen(roadfighter.konami1_sfc, screen)
    rect = sdl2.SDL_Rect(0, 0, roadfighter.konami2_sfc.contents.w, roadfighter.state_timmer * 2)
    sdl2.SDL_BlitSurface(roadfighter.konami2_sfc, rect, screen, rect)
    fade = float(roadfighter.konami_timmer) / float(const.KONAMI_FADE_TIME)
    if fade < 1.0:
        surface_fader(screen, max(0.0, fade), max(0.0, fade), max(0.0, fade), None)


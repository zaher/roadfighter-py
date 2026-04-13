from __future__ import annotations

from .. import constants as const
from ..auxiliar import surface_fader


def presentation_cycle(roadfighter) -> int:
    key_pressed = False
    if roadfighter.state_timmer == 0:
        roadfighter.presentation_state = 0
        roadfighter.presentation_timmer = 0

    if roadfighter.presentation_state == 0:
        roadfighter.presentation_timmer += 1
    if roadfighter.presentation_state == 1:
        roadfighter.presentation_timmer -= 1
    if roadfighter.presentation_state == 2:
        roadfighter.presentation_timmer += 1
    if roadfighter.presentation_state == 3:
        roadfighter.presentation_timmer -= 1

    if roadfighter.state_timmer >= 5:
        key_pressed = bool(roadfighter.keyboard.newly_pressed(roadfighter.old_keyboard))

    if roadfighter.presentation_state == 0 and (roadfighter.state_timmer >= 350 or key_pressed):
        roadfighter.presentation_state = 1
        if roadfighter.presentation_timmer > const.PRESENTATION_FADE_TIME:
            roadfighter.presentation_timmer = const.PRESENTATION_FADE_TIME
    if roadfighter.presentation_state == 2 and (roadfighter.state_timmer >= 700 or key_pressed):
        roadfighter.presentation_state = 3
        if roadfighter.presentation_timmer > const.PRESENTATION_FADE_TIME:
            roadfighter.presentation_timmer = const.PRESENTATION_FADE_TIME

    if roadfighter.presentation_state == 1 and roadfighter.presentation_timmer <= 0:
        roadfighter.presentation_state = 2
    if roadfighter.presentation_state == 3 and roadfighter.presentation_timmer <= 0:
        return const.KONAMI_STATE
    return const.PRESENTATION_STATE


def presentation_draw(roadfighter, screen) -> None:
    source = roadfighter.disclaimer_sfc if roadfighter.presentation_state < 2 else roadfighter.retroremakes_sfc
    roadfighter.blit_fullscreen(source, screen)
    fade = float(roadfighter.presentation_timmer) / float(const.PRESENTATION_FADE_TIME)
    if fade < 1.0:
        surface_fader(screen, max(0.0, fade), max(0.0, fade), max(0.0, fade), None)


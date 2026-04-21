from __future__ import annotations

import sdl2

from .. import constants as const
from ..auxiliar import surface_fader
from ..sound import Sound_create_music, Sound_music_volume, Sound_release_music


def gameover_cycle(roadfighter) -> int:
    if roadfighter.state_timmer == 0:
        roadfighter.gameover_state = 0
        roadfighter.gameover_timmer = 0
        Sound_music_volume(128)
        Sound_create_music("sound/gameover", 0)

    if roadfighter.gameover_state == 1:
        volume = (roadfighter.gameover_timmer * 128) // const.GAMEOVER_TIME
        Sound_music_volume(max(0, min(128, volume)))

    if roadfighter.gameover_state == 0:
        roadfighter.gameover_timmer += 1
    if roadfighter.gameover_state == 1:
        roadfighter.gameover_timmer -= 1

    if roadfighter.gameover_state == 0 and (
        roadfighter.state_timmer >= const.GAMEOVER_TIME * 6
        or (
            roadfighter.state_timmer >= const.GAMEOVER_TIME
            and (
                (roadfighter.keyboard[roadfighter.fire_key] and not roadfighter.old_keyboard[roadfighter.fire_key])
                or (roadfighter.keyboard[const.GLOBAL_SELECT_KEY] and not roadfighter.old_keyboard[const.GLOBAL_SELECT_KEY])
                or (roadfighter.keyboard[const.GLOBAL_ESCAPE_KEY] and not roadfighter.old_keyboard[const.GLOBAL_ESCAPE_KEY])
            )
        )
    ):
        roadfighter.gameover_state = 1
        if roadfighter.gameover_timmer >= const.GAMEOVER_TIME:
            roadfighter.gameover_timmer = const.GAMEOVER_TIME

    if roadfighter.gameover_state == 1 and roadfighter.gameover_timmer <= 0:
        Sound_release_music()
        Sound_music_volume(128)
        return const.KONAMI_STATE
    return const.GAMEOVER_STATE


def gameover_draw(roadfighter, screen) -> None:
    roadfighter.clear_screen(screen)
    if roadfighter.gameover_state == 1:
        if roadfighter.scoreboard_fade_timmer > 0:
            roadfighter.scoreboard_fade_timmer -= 1
        if roadfighter.scoreboard_x < roadfighter.screen_w:
            roadfighter.scoreboard_x += int((roadfighter.screen_w - roadfighter.desired_scoreboard_x) / const.GAMEOVER_TIME)
        if roadfighter.scoreboard_x > roadfighter.screen_w:
            roadfighter.scoreboard_x = roadfighter.screen_w
    roadfighter.scoreboard_draw(roadfighter.scoreboard_x, 0, screen)

    text_sfc = sdl2.SDL_ConvertSurfaceFormat(roadfighter.gameover_sfc, sdl2.SDL_PIXELFORMAT_RGBA32, 0)
    fade = min(1.0, float(roadfighter.gameover_timmer) / const.GAMEOVER_TIME)
    if fade < 1.0:
        surface_fader(text_sfc, fade, fade, fade, None)
    rect = roadfighter.make_rect((roadfighter.desired_scoreboard_x // 2) - (text_sfc.contents.w // 2), (roadfighter.screen_h // 2) - (text_sfc.contents.h // 2), text_sfc.contents.w, text_sfc.contents.h)
    sdl2.SDL_BlitSurface(text_sfc, None, screen, rect)
    sdl2.SDL_FreeSurface(text_sfc)

from __future__ import annotations

import sdl2
import sdl2.sdlimage as sdlimage

from .. import constants as const
from ..auxiliar import surface_fader
from ..filehandling import FileType, resolve_path
from ..game import CGame
from ..sound import Sound_create_music, Sound_music_volume, Sound_release_music


def interlevel_cycle(roadfighter) -> int:
    if roadfighter.state_timmer == 0:
        score1 = 0
        score2 = 0
        if roadfighter.levelintro_sfc is not None:
            sdl2.SDL_FreeSurface(roadfighter.levelintro_sfc)
            roadfighter.levelintro_sfc = None

        Sound_music_volume(128)
        if roadfighter.current_level > roadfighter.start_level and roadfighter.game is not None:
            scores = []
            roadfighter.game.get_scores(roadfighter.wrap_list(scores))
            if scores:
                score1 = scores[0]
            if roadfighter.n_players > 1 and len(scores) > 1:
                score2 = scores[1]
        else:
            Sound_create_music("sound/start", 0)

        if roadfighter.current_level > const.NLEVELS:
            roadfighter.current_level = 1
            roadfighter.game_mode += 1
            if roadfighter.game_mode >= 3:
                roadfighter.game_mode = 3

        scoreboard_name = "graphics/s_board12p.png" if roadfighter.n_players > 1 else "graphics/s_board11p.png"
        if roadfighter.current_level >= 6:
            scoreboard_name = "graphics/s_board22p.png" if roadfighter.n_players > 1 else "graphics/s_board21p.png"
        if roadfighter.scoreboard2_sfc is not None:
            sdl2.SDL_FreeSurface(roadfighter.scoreboard2_sfc)
        roadfighter.scoreboard2_sfc = sdlimage.IMG_Load(str(resolve_path(scoreboard_name, FileType.GAMEDATA)).encode("utf-8"))

        roadfighter.desired_scoreboard_x = roadfighter.screen_w - (128 if roadfighter.n_players > 1 else 144)
        roadfighter.levelintro_sfc = sdlimage.IMG_Load(
            str(resolve_path(f"graphics/stage{roadfighter.current_level}.jpg", FileType.GAMEDATA)).encode("utf-8")
        )

        if roadfighter.game is not None:
            roadfighter.game.close()
            roadfighter.game = None

        map_name = const.MAPS[roadfighter.current_level - 1]
        if roadfighter.n_players == 1:
            if roadfighter.is_player2:
                roadfighter.game = CGame(map_name, roadfighter.game_mode, roadfighter.left2_key, roadfighter.right2_key, roadfighter.fire2_key, score2, roadfighter.current_level, roadfighter.game_remake_extras, roadfighter.fuel_factor)
            else:
                roadfighter.game = CGame(map_name, roadfighter.game_mode, roadfighter.left_key, roadfighter.right_key, roadfighter.fire_key, score1, roadfighter.current_level, roadfighter.game_remake_extras, roadfighter.fuel_factor)
        else:
            roadfighter.game = CGame(map_name, roadfighter.game_mode, roadfighter.left_key, roadfighter.right_key, roadfighter.fire_key, roadfighter.left2_key, roadfighter.right2_key, roadfighter.fire2_key, score1, score2, roadfighter.current_level, roadfighter.game_remake_extras, roadfighter.fuel_factor)

        roadfighter.interlevel_state = 0
        roadfighter.interlevel_timmer = 0
        if roadfighter.current_level == 1:
            roadfighter.interlevel_state = 3

    if roadfighter.interlevel_state == 0:
        if roadfighter.state_timmer >= const.INTERLEVEL_TIME:
            roadfighter.interlevel_state = 1
            roadfighter.interlevel_timmer = 0
        else:
            roadfighter.interlevel_timmer += 1
    elif roadfighter.interlevel_state == 1:
        if roadfighter.state_timmer >= const.INTERLEVEL_TIME * 4 or (
            roadfighter.interlevel_timmer >= const.INTERLEVEL_TIME * 2
            and (
                    (roadfighter.keyboard[roadfighter.fire_key] and not roadfighter.old_keyboard[roadfighter.fire_key])
                    or (roadfighter.keyboard[roadfighter.fire2_key] and not roadfighter.old_keyboard[roadfighter.fire2_key])
                    or (roadfighter.keyboard[const.GLOBAL_ESCAPE_KEY] and not roadfighter.old_keyboard[const.GLOBAL_ESCAPE_KEY])
                )
        ):
            roadfighter.interlevel_state = 2
            if roadfighter.interlevel_timmer >= const.INTERLEVEL_TIME:
                roadfighter.interlevel_timmer = const.INTERLEVEL_TIME
        else:
            roadfighter.interlevel_timmer += 1
    elif roadfighter.interlevel_state == 2:
        if roadfighter.interlevel_timmer <= 0:
            roadfighter.interlevel_state = 3
            roadfighter.interlevel_timmer = 0
        else:
            roadfighter.interlevel_timmer -= 1
    elif roadfighter.interlevel_state == 3:
        if roadfighter.interlevel_timmer >= const.INTERLEVEL_TIME * 5 or (
            roadfighter.interlevel_timmer >= const.INTERLEVEL_TIME
            and (
                    (roadfighter.keyboard[roadfighter.fire_key] and not roadfighter.old_keyboard[roadfighter.fire_key])
                    or (roadfighter.keyboard[roadfighter.fire2_key] and not roadfighter.old_keyboard[roadfighter.fire2_key])
                    or (roadfighter.keyboard[const.GLOBAL_ESCAPE_KEY] and not roadfighter.old_keyboard[const.GLOBAL_ESCAPE_KEY])
                )
        ):
            roadfighter.interlevel_state = 4
            if roadfighter.interlevel_timmer >= const.INTERLEVEL_TIME:
                roadfighter.interlevel_timmer = const.INTERLEVEL_TIME
        else:
            roadfighter.interlevel_timmer += 1
    elif roadfighter.interlevel_state == 4:
        Sound_music_volume((roadfighter.interlevel_timmer * 128) // const.INTERLEVEL_TIME)
        if roadfighter.interlevel_timmer <= 0:
            Sound_release_music()
            Sound_music_volume(128)
            roadfighter.playing_reachedend = False
            return const.PLAYING_STATE
        roadfighter.interlevel_timmer -= 1
    return const.INTERLEVEL_STATE


def interlevel_draw(roadfighter, screen) -> None:
    roadfighter.clear_screen(screen)
    if roadfighter.interlevel_state in (0, 1, 2):
        rect = roadfighter.make_rect((roadfighter.desired_scoreboard_x // 2) - (roadfighter.gamemap_sfc.contents.w // 2), (roadfighter.screen_h // 2) - (roadfighter.gamemap_sfc.contents.h // 2), roadfighter.gamemap_sfc.contents.w, roadfighter.gamemap_sfc.contents.h)
        sdl2.SDL_BlitSurface(roadfighter.gamemap_sfc, None, screen, rect)
        if ((roadfighter.interlevel_timmer >> 3) & 0x01) != 0:
            car_x = (roadfighter.desired_scoreboard_x // 2) - (roadfighter.minicar1_tile.get_dx() // 2)
            if roadfighter.interlevel_state == 0:
                car_y = (roadfighter.screen_h // 2) + (roadfighter.gamemap_sfc.contents.h // 2) - (roadfighter.current_level - 2) * (roadfighter.gamemap_sfc.contents.h // 6) - (roadfighter.minicar1_tile.get_dy() // 2)
            elif roadfighter.interlevel_state == 1:
                car_y = (roadfighter.screen_h // 2) + (roadfighter.gamemap_sfc.contents.h // 2) - (roadfighter.current_level - 2) * (roadfighter.gamemap_sfc.contents.h // 6) - (roadfighter.minicar1_tile.get_dy() // 2)
                v = min(roadfighter.interlevel_timmer, const.INTERLEVEL_TIME * 2)
                car_y -= (v * (roadfighter.gamemap_sfc.contents.h // 6)) // (const.INTERLEVEL_TIME * 2)
            else:
                car_y = (roadfighter.screen_h // 2) + (roadfighter.gamemap_sfc.contents.h // 2) - (roadfighter.current_level - 1) * (roadfighter.gamemap_sfc.contents.h // 6) - (roadfighter.minicar1_tile.get_dy() // 2)
            roadfighter.minicar1_tile.draw(car_x, car_y, screen)
    if roadfighter.interlevel_state == 0:
        fade = float(roadfighter.interlevel_timmer) / float(const.INTERLEVEL_TIME)
        if fade < 1.0:
            roadfighter.fade_screen(screen, fade)
    elif roadfighter.interlevel_state == 2:
        fade = float(roadfighter.interlevel_timmer) / float(const.INTERLEVEL_TIME)
        if fade < 1.0:
            roadfighter.fade_screen(screen, fade)
    elif roadfighter.interlevel_state in (3, 4) and roadfighter.levelintro_sfc is not None:
        fade = min(1.0, float(roadfighter.interlevel_timmer) / const.INTERLEVEL_TIME)
        rect = roadfighter.make_rect(
            (roadfighter.desired_scoreboard_x // 2) - (roadfighter.levelintro_sfc.contents.w // 2),
            (roadfighter.screen_h // 2) - roadfighter.levelintro_sfc.contents.h,
            roadfighter.levelintro_sfc.contents.w,
            roadfighter.levelintro_sfc.contents.h,
        )
        sdl2.SDL_BlitSurface(roadfighter.levelintro_sfc, None, screen, rect)
        if fade < 1.0:
            surface_fader(screen, fade, fade, fade, rect)

    if roadfighter.scoreboard_x == -1:
        roadfighter.scoreboard_x = roadfighter.screen_w
    else:
        if roadfighter.scoreboard_x > roadfighter.desired_scoreboard_x:
            roadfighter.scoreboard_x -= int((roadfighter.screen_w - roadfighter.desired_scoreboard_x) / const.INTERLEVEL_TIME)
            if roadfighter.scoreboard_fade_timmer < 25:
                roadfighter.scoreboard_fade_timmer += 1
        if roadfighter.scoreboard_x < roadfighter.desired_scoreboard_x:
            roadfighter.scoreboard_x = roadfighter.desired_scoreboard_x
    roadfighter.scoreboard_draw(roadfighter.scoreboard_x, 0, screen)

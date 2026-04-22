from __future__ import annotations

import random
import time

import sdl2

from .. import constants as const
from ..filehandling import FileType, f1open
from ..sound import Sound_create_music, Sound_music_volume

record_replay = False
load_replay = False


def _close_replay(roadfighter) -> None:
    if roadfighter.replay_fp is not None:
        roadfighter.replay_fp.close()
        roadfighter.replay_fp = None


def _show_cursor() -> None:
    """Show mouse cursor when leaving playing state."""
    sdl2.SDL_ShowCursor(sdl2.SDL_ENABLE)


def playing_cycle(roadfighter) -> int:
    active_record = record_replay or roadfighter.record_replay
    active_load = load_replay or roadfighter.load_replay

    if roadfighter.state_timmer == 0:
        # Hide mouse cursor when race starts
        sdl2.SDL_ShowCursor(sdl2.SDL_DISABLE)
        if active_record:
            seed = int(time.time())
            roadfighter.replay_fp = f1open("replay.txt", "w+", FileType.USERDATA)
            roadfighter.replay_fp.write(f"{seed}\n")
            roadfighter.replay_fp.flush()
            random.seed(seed)
        elif active_load:
            roadfighter.replay_fp = f1open("replay.txt", "r+", FileType.USERDATA)
            seed_line = roadfighter.replay_fp.readline()
            random.seed(int(seed_line.strip()))

    if active_record and roadfighter.replay_fp is not None:
        for key in sorted(roadfighter.keyboard.changed_keys(roadfighter.old_keyboard)):
            roadfighter.replay_fp.write(f"{1 if roadfighter.keyboard[key] else 0} {key}\n")
        roadfighter.replay_fp.write("-1\n")
        roadfighter.replay_fp.flush()
    elif active_load and roadfighter.replay_fp is not None:
        while True:
            line = roadfighter.replay_fp.readline()
            if not line:
                _close_replay(roadfighter)
                _show_cursor()
                return const.GAMEOVER_STATE
            line = line.strip()
            if not line:
                continue
            if line == "-1":
                break
            value, key = line.split()
            roadfighter.keyboard.set(int(key), int(value) == 1)

    if not roadfighter.game.cycle(roadfighter.keyboard, roadfighter.old_keyboard):
        if roadfighter.game.level_completed():
            roadfighter.current_level += 1
            if active_record or active_load:
                _close_replay(roadfighter)
            _show_cursor()
            return const.INTERLEVEL_STATE
        if roadfighter.game.backspace_pressed:
            roadfighter.game.close()
            roadfighter.game = None
            roadfighter.current_level = roadfighter.start_level
            if active_record or active_load:
                _close_replay(roadfighter)
            _show_cursor()
            return const.INTERLEVEL_STATE
        roadfighter.gameover_state = 0
        if active_record or active_load:
            _close_replay(roadfighter)
        _show_cursor()
        return const.GAMEOVER_STATE
    if not roadfighter.playing_reachedend and roadfighter.game.level_completed():
        roadfighter.playing_reachedend = True
        Sound_create_music("sound/levelcomplete", 0)
    if not roadfighter.playing_reachedend:
        volume = (roadfighter.game.get_game_timmer() * 128) // 25
        Sound_music_volume(max(0, min(128, volume)))
    scores = []
    roadfighter.game.get_scores(roadfighter.wrap_list(scores))
    for score in scores:
        roadfighter.high_score = max(roadfighter.high_score, score)
    return const.PLAYING_STATE


def playing_draw(roadfighter, screen) -> None:
    roadfighter.clear_screen(screen)
    roadfighter.scoreboard_draw(roadfighter.scoreboard_x, 0, screen)
    if roadfighter.n_players == 1:
        viewport = roadfighter.make_rect(roadfighter.desired_scoreboard_x - 352, 0, 352, roadfighter.screen_h)
    else:
        viewport = roadfighter.make_rect(0, 0, roadfighter.scoreboard_x, roadfighter.screen_h)
    roadfighter.game.draw(screen, viewport)

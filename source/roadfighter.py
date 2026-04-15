"""Top-level CRoadFighter port."""

from __future__ import annotations

from ctypes import byref
import os

import sdl2
import sdl2.sdlimage as sdlimage
import sdl2.sdlttf as sdlttf

from . import constants as const
from .auxiliar import multiline_text_surface2, sge_transform, surface_fader
from .configuration import Configuration, default_configuration, load_configuration, save_configuration
from .filehandling import FileType, resolve_path
from .game import CGame
from .keyboard import KeyboardState
from .joystick import JoystickState
from .constants import JOY_LEFT, JOY_RIGHT, JOY_FIRE
from .list import List
from .sound import Sound_create_sound, Sound_release_music
from .states.gameover_state import gameover_cycle, gameover_draw
from .states.interlevel_state import interlevel_cycle, interlevel_draw
from .states.konami_state import konami_cycle, konami_draw
from .states.menu_state import menu_cycle, menu_draw
from .states.playing_state import playing_cycle, playing_draw
from .states.presentation_state import presentation_cycle, presentation_draw
from .tile import CTile


def _load_surface(path: str):
    resolved = resolve_path(path, FileType.GAMEDATA)
    surface = sdlimage.IMG_Load(str(resolved).encode("utf-8"))
    if not surface:
        raise FileNotFoundError(str(resolved))
    return sdl2.SDL_ConvertSurfaceFormat(surface, sdl2.SDL_PIXELFORMAT_RGBA32, 0)


class ListWrapper:
    def __init__(self, target_list: list):
        self.target_list = target_list

    def Add(self, item):
        self.target_list.append(item)
        return item


class RoadFighter:
    def __init__(self, start_level: int = 1) -> None:
        self.start_level = start_level
        self.screen_w = const.SCREEN_X
        self.screen_h = const.SCREEN_Y

        self.state = const.PRESENTATION_STATE
        self.state_timmer = 0
        self.current_level = 0
        self.high_score = 0
        self.game: CGame | None = None

        self.presentation_state = 0
        self.presentation_timmer = 0
        self.konami_state = 0
        self.konami_timmer = 0
        self.interlevel_state = 0
        self.interlevel_timmer = 0
        self.gameover_state = 0
        self.gameover_timmer = 0
        self.scoreboard_fade_timmer = 0
        self.menu_current_menu = 0
        self.menu_state = 0
        self.menu_effect = 0
        self.menu_timmer = 0
        self.menu_tittle_text = ""
        self.menu_options_text = ""
        self.menu_nitems = 0
        self.menu_item = 0
        self.menu_redefining_key = -1
        self.menu_credits_timmer = 0
        self._menu_surface_cache = {}
        self._score_surface_cache = {}

        self.game_mode = 0
        self.n_players = 1
        self.game_remake_extras = True
        self.playing_reachedend = False
        self.scoreboard_x = -1
        self.desired_scoreboard_x = self.screen_w

        self.keyboard = KeyboardState()
        self.old_keyboard = KeyboardState()
        self.joystick = JoystickState()
        self.old_joystick = JoystickState()
        
        # Load configuration and set up joystick mapping
        cfg = load_configuration()
        self.keyboard.set_joystick_mapping(cfg.left_key, cfg.right_key, cfg.fire_key)
        # Map second player joystick if supported (for now maps to player 2 keys)
        # In future this would handle a second joystick
        # self.keyboard.set_joystick_mapping(cfg.left2_key, cfg.right2_key, cfg.fire2_key)
        self.replay_fp = None
        self.record_replay = os.environ.get("ROADFIGHTER_RECORD_REPLAY", "").lower() in {"1", "true", "yes", "on"}
        self.load_replay = os.environ.get("ROADFIGHTER_LOAD_REPLAY", "").lower() in {"1", "true", "yes", "on"}

        comic_font = str(resolve_path("fonts/comicbd.ttf", FileType.GAMEDATA)).encode("utf-8")
        tangle_font = str(resolve_path("fonts/tanglewo.ttf", FileType.GAMEDATA)).encode("utf-8")
        self.font1 = sdlttf.TTF_OpenFont(comic_font, 16)
        self.font2big = sdlttf.TTF_OpenFont(tangle_font, const.FONT_SIZE)
        self.font2medium = sdlttf.TTF_OpenFont(tangle_font, int(const.FONT_SIZE * 0.8))
        self.font2small = sdlttf.TTF_OpenFont(tangle_font, int(const.FONT_SIZE * 0.65))

        self.disclaimer_sfc = _load_surface("graphics/disclaimer.jpg")
        self.retroremakes_sfc = _load_surface("graphics/retroremakes.bmp")
        self.konami1_sfc = _load_surface("graphics/konami1.jpg")
        self.konami2_sfc = _load_surface("graphics/konami2.jpg")
        self.tittle_sfc = _load_surface("graphics/title.jpg")
        self.arrow_sfc = _load_surface("graphics/arrow.bmp")
        self.scoreboard_sfc = _load_surface("graphics/scoreboard.bmp")
        self.scoreboard2_sfc = None
        self.scoreboardleft_sfc = _load_surface("graphics/scoreboard_left.bmp")
        self.gamemap_sfc = _load_surface("graphics/gamemap.bmp")
        self.minicar1_sfc = _load_surface("graphics/minicar1.bmp")
        self.minicar2_sfc = _load_surface("graphics/minicar2.bmp")
        self.gameover_sfc = _load_surface("graphics/gameover.jpg")
        self.levelintro_sfc = None
        self.minicar1_tile = CTile(0, 0, self.minicar1_sfc.contents.w // 2, self.minicar1_sfc.contents.h, self.minicar1_sfc, False)
        self.minicar2_tile = CTile(0, 0, self.minicar2_sfc.contents.w // 2, self.minicar2_sfc.contents.h, self.minicar2_sfc, False)

        credits_color = sdl2.SDL_Color(128, 128, 128, 255)
        credits_text = (
            "        "
            "Game created for the RETROREMAKES REMAKE COMPETITION"
            "        "
            "PROGRAMMING: Santi Ontanon (Brain)    "
            "GRAPHICS: Miikka Poikela (McBain)    "
            "MUSIC/SFX: Jorrith Schaap (Jorito)    "
            "BETA TESTING: Jason Eames (JEames), Miikka Poikela (McBain), Jorrith Schaap (Jorito), Santi Ontanon (Brain)"
            "        "
        )
        self.credits_sfc = sdlttf.TTF_RenderUTF8_Blended(self.font1, credits_text.encode("utf-8"), credits_color)
        self.credits2_sfc = sdlttf.TTF_RenderUTF8_Blended(self.font1, credits_text.encode("utf-8"), credits_color)

        self.S_menu_move = Sound_create_sound("sound/menu_move")
        self.S_menu_select = Sound_create_sound("sound/menu_select")
        self.S_menu_in = Sound_create_sound("sound/logo_in")
        self.S_menu_out = Sound_create_sound("sound/logo_out")

        cfg = load_configuration()
        self.left_key = cfg.left_key
        self.right_key = cfg.right_key
        self.fire_key = cfg.fire_key
        self.left2_key = cfg.left2_key
        self.right2_key = cfg.right2_key
        self.fire2_key = cfg.fire2_key
        self.game_remake_extras = cfg.game_remake_extras

    def wrap_list(self, target: list):
        return ListWrapper(target)

    def make_rect(self, x: int, y: int, w: int, h: int):
        return sdl2.SDL_Rect(x, y, w, h)

    def clear_screen(self, screen) -> None:
        sdl2.SDL_FillRect(screen, None, sdl2.SDL_MapRGB(screen.contents.format, 0, 0, 0))

    def blit_fullscreen(self, source, dest) -> None:
        rect = self.make_rect(0, 0, source.contents.w, source.contents.h)
        sdl2.SDL_BlitSurface(source, rect, dest, rect)

    def fade_screen(self, screen, factor: float) -> None:
        surface_fader(screen, factor, factor, factor, None)

    def fade_surface(self, surface, factor: float) -> None:
        surface_fader(surface, factor, factor, factor, None)

    def cycle(self) -> bool:
        old_state = self.state
        
        # Update joystick axis state and map to virtual keys
        self.joystick.update()
        
        # Map joystick virtual keys to keyboard state
        self.keyboard.set(JOY_LEFT, self.joystick[JOY_LEFT])
        self.keyboard.set(JOY_RIGHT, self.joystick[JOY_RIGHT])
        self.keyboard.set(JOY_FIRE, self.joystick[JOY_FIRE])
        
        if self.state == const.PRESENTATION_STATE:
            self.state = presentation_cycle(self)
        elif self.state == const.KONAMI_STATE:
            self.state = konami_cycle(self)
        elif self.state == const.MENU_STATE:
            self.state = menu_cycle(self)
        elif self.state == const.DEMO_STATE:
            self.state = const.KONAMI_STATE
        elif self.state == const.PLAYING_STATE:
            self.state = playing_cycle(self)
        elif self.state == const.INTERLEVEL_STATE:
            self.state = interlevel_cycle(self)
        elif self.state == const.GAMEOVER_STATE:
            self.state = gameover_cycle(self)
        elif self.state == const.QUIT_STATE:
            return False

        if self.state != old_state:
            self.state_timmer = 0
        else:
            self.state_timmer += 1
            
        # Save old states
        self.old_keyboard = self.keyboard.copy()
        self.old_joystick = self.joystick.copy()
        
        return True

    def close(self) -> None:
        if self.replay_fp is not None:
            self.replay_fp.close()
            self.replay_fp = None
        if self.game is not None:
            self.game.close()
            self.game = None

    def draw(self, screen) -> None:
        if self.state_timmer == 0:
            return
        if self.state == const.PRESENTATION_STATE:
            presentation_draw(self, screen)
        elif self.state == const.KONAMI_STATE:
            konami_draw(self, screen)
        elif self.state == const.MENU_STATE:
            menu_draw(self, screen)
        elif self.state == const.PLAYING_STATE:
            playing_draw(self, screen)
        elif self.state == const.INTERLEVEL_STATE:
            interlevel_draw(self, screen)
        elif self.state == const.GAMEOVER_STATE:
            gameover_draw(self, screen)

    def scoreboard_draw(self, x: int, y: int, screen) -> None:
        if self.scoreboard_sfc is None:
            return
        rect = self.make_rect(x, y, self.scoreboard_sfc.contents.w, self.scoreboard_sfc.contents.h)
        sdl2.SDL_BlitSurface(self.scoreboard_sfc, None, screen, rect)
        if rect.x + rect.w < self.screen_w:
            source = self.make_rect(self.scoreboard_sfc.contents.w - 1, 0, 1, self.scoreboard_sfc.contents.h)
            for i in range(rect.x + rect.w, self.screen_w):
                target = self.make_rect(i, rect.y, 1, rect.h)
                sdl2.SDL_BlitSurface(self.scoreboard_sfc, source, screen, target)

        if self.game is not None:
            speeds = []
            self.game.get_speeds(self.wrap_list(speeds))
            for j, speed in enumerate(reversed(speeds)):
                height = int(112 * (float(-speed) / const.MAX_SPEED))
                width = (33 - len(speeds)) // max(1, len(speeds))
                for row in range(367, 367 - height, -2):
                    bar = self.make_rect((x + 28) + (width + 1) * j, row, width, 1)
                    sdl2.SDL_FillRect(screen, bar, sdl2.SDL_MapRGB(screen.contents.format, 255, 255, 255))

            fuels = []
            self.game.get_fuels(self.wrap_list(fuels))
            for j, fuel in enumerate(reversed(fuels)):
                height = int(112 * (float(fuel) / const.MAX_FUEL))
                width = (33 - len(fuels)) // max(1, len(fuels))
                for row in range(367, 367 - height, -2):
                    bar = self.make_rect((x + 76) + (width + 1) * j, row, width, 1)
                    sdl2.SDL_FillRect(screen, bar, sdl2.SDL_MapRGB(screen.contents.format, 255, 255, 255))

        if self.scoreboard2_sfc is not None:
            minimap_rect = self.make_rect(self.scoreboard_x + 41, 97, 55, 143)
            sdl2.SDL_BlitSurface(self.scoreboard2_sfc, None, screen, minimap_rect)
            fade = max(0.0, min(1.0, self.scoreboard_fade_timmer / 25.0))
            if fade != 1.0:
                surface_fader(screen, fade, fade, fade, minimap_rect)

        if self.game is not None and ((self.state_timmer >> 3) & 0x01) != 0:
            positions = []
            self.game.get_positions(self.wrap_list(positions))
            car_x = x + 68 + len(positions) * self.minicar1_tile.get_dx() // 2 - self.minicar1_tile.get_dx()
            for index, pos in enumerate(positions):
                car_y = int(108 + pos * (121 - self.minicar1_tile.get_dy()))
                (self.minicar1_tile if index == 0 else self.minicar2_tile).draw(car_x, car_y, screen)
                car_x -= self.minicar1_tile.get_dx()

        if self.game is not None:
            self.render_score(str(self.high_score), x + 103, 21, (0, 255, 0), screen)
            scores = []
            self.game.get_scores(self.wrap_list(scores))
            for index, score in enumerate(scores):
                if ((self.state_timmer >> 5) % len(scores)) == index:
                    color = (255, 0, 0) if index == 0 else (255, 255, 0)
                    self.render_score(str(score), x + 103, 64, color, screen)

        if self.n_players == 1:
            factor = float(self.screen_w - self.scoreboard_x) / float(self.screen_w - self.desired_scoreboard_x)
            rect = self.make_rect((-self.scoreboardleft_sfc.contents.w) + int((self.desired_scoreboard_x - 352) * factor), 0, self.scoreboardleft_sfc.contents.w, self.scoreboardleft_sfc.contents.h)
            sdl2.SDL_BlitSurface(self.scoreboardleft_sfc, None, screen, rect)

    def render_score(self, text: str, x: int, y: int, color, screen) -> None:
        key = (text, color)
        sfc = self._score_surface_cache.get(key)
        if sfc is None:
            sfc = sdlttf.TTF_RenderUTF8_Blended(self.font1, text.encode("utf-8"), sdl2.SDL_Color(*color, 255))
            self._score_surface_cache[key] = sfc
        rect = self.make_rect(x - sfc.contents.w, y, sfc.contents.w, sfc.contents.h)
        sdl2.SDL_BlitSurface(sfc, None, screen, rect)

    def assign_redefined_key(self, key: int) -> None:
        if self.menu_redefining_key == 0 and key not in (self.left_key, self.fire_key):
            self.right_key = key
        elif self.menu_redefining_key == 1 and key not in (self.right_key, self.fire_key):
            self.left_key = key
        elif self.menu_redefining_key == 2 and key not in (self.right_key, self.left_key):
            self.fire_key = key
        elif self.menu_redefining_key == 3 and key not in (self.left2_key, self.fire2_key):
            self.right2_key = key
        elif self.menu_redefining_key == 4 and key not in (self.right2_key, self.fire2_key):
            self.left2_key = key
        elif self.menu_redefining_key == 5 and key not in (self.right2_key, self.left2_key):
            self.fire2_key = key

    def refresh_menu_text(self, key_name_func) -> None:
        if self.menu_state not in (1, 2, 3):
            return
        if self.menu_current_menu == 0:
            self.menu_tittle_text = "PLAY SELECT:"
            self.menu_options_text = "ONE PLAYER\nTWO PLAYERS\nOPTIONS\nQUIT\n"
            self.menu_nitems = 4
        elif self.menu_current_menu == 1:
            self.menu_tittle_text = "OPTIONS:"
            extras = "ON" if self.game_remake_extras else "OFF"
            self.menu_options_text = f"PLAYER 1 KEYS\nPLAYER 2 KEYS\nEXTRAS: {extras}\nDEFAULT\nBACK\n"
            self.menu_nitems = 5
        elif self.menu_current_menu == 2:
            self.menu_tittle_text = "PLAYER 1:"
            self.menu_options_text = (
                f"RIGHT : {'' if self.menu_redefining_key == 0 else key_name_func(self.right_key)}\n"
                f"LEFT : {'' if self.menu_redefining_key == 1 else key_name_func(self.left_key)}\n"
                f"FIRE : {'' if self.menu_redefining_key == 2 else key_name_func(self.fire_key)}\n"
                "BACK\n"
            )
            self.menu_nitems = 4
        elif self.menu_current_menu == 3:
            self.menu_tittle_text = "PLAYER 2:"
            self.menu_options_text = (
                f"RIGHT : {'' if self.menu_redefining_key == 3 else key_name_func(self.right2_key)}\n"
                f"LEFT : {'' if self.menu_redefining_key == 4 else key_name_func(self.left2_key)}\n"
                f"FIRE : {'' if self.menu_redefining_key == 5 else key_name_func(self.fire2_key)}\n"
                "BACK\n"
            )
            self.menu_nitems = 4
        elif self.menu_current_menu == 4:
            self.menu_tittle_text = "ONE PLAYER:"
            self.menu_options_text = "LEVEL A\nLEVEL B\nLEVEL C\nBACK\n"
            self.menu_nitems = 4
        elif self.menu_current_menu == 5:
            self.menu_tittle_text = "TWO PLAYERS:"
            self.menu_options_text = "LEVEL A\nLEVEL B\nLEVEL C\nBACK\n"
            self.menu_nitems = 4

    def resolve_menu_transition(self) -> int:
        if self.menu_current_menu == 0:
            if self.menu_item == 0:
                self.menu_state = 1
                self.menu_timmer = 0
                self.menu_current_menu = 4
            elif self.menu_item == 1:
                self.menu_state = 1
                self.menu_timmer = 0
                self.menu_current_menu = 5
            elif self.menu_item == 2:
                self.menu_state = 1
                self.menu_timmer = 0
                self.menu_current_menu = 1
            elif self.menu_item == 3:
                self.menu_state = 4
                self.menu_timmer = const.EFFECT_LENGTH
            return const.MENU_STATE
        if self.menu_current_menu == 1:
            if self.menu_item == 0:
                self.menu_state = 1
                self.menu_timmer = 0
                self.menu_current_menu = 2
            elif self.menu_item == 1:
                self.menu_state = 1
                self.menu_timmer = 0
                self.menu_current_menu = 3
            elif self.menu_item == 4:
                self.menu_state = 1
                self.menu_timmer = 0
                self.menu_current_menu = 0
                self.save_current_configuration()
            return const.MENU_STATE
        if self.menu_current_menu in (2, 3):
            if self.menu_item == 3:
                self.menu_state = 1
                self.menu_timmer = 0
                self.menu_current_menu = 1
            return const.MENU_STATE
        if self.menu_current_menu in (4, 5):
            if self.menu_item == 3:
                self.menu_state = 1
                self.menu_timmer = 0
                self.menu_current_menu = 0
                return const.MENU_STATE
            self.menu_state = 4
            self.menu_timmer = const.EFFECT_LENGTH
            return const.MENU_STATE
        return const.MENU_STATE

    def save_current_configuration(self) -> None:
        save_configuration(
            Configuration(
                left_key=self.left_key,
                right_key=self.right_key,
                fire_key=self.fire_key,
                left2_key=self.left2_key,
                right2_key=self.right2_key,
                fire2_key=self.fire2_key,
                game_remake_extras=self.game_remake_extras,
            )
        )

    def resolve_menu_exit(self) -> int:
        if self.menu_current_menu == 0 and self.menu_item == 3:
            Sound_release_music()
            return const.QUIT_STATE
        if self.menu_current_menu == 4 and self.menu_item in (0, 1, 2):
            self.game_mode = self.menu_item
            self.n_players = 1
            self.current_level = self.start_level
            self.scoreboard_x = -1
            self.interlevel_state = 0
            self.interlevel_timmer = 0
            Sound_release_music()
            return const.INTERLEVEL_STATE
        if self.menu_current_menu == 5 and self.menu_item in (0, 1, 2):
            self.game_mode = self.menu_item
            self.n_players = 2
            self.current_level = self.start_level
            self.scoreboard_x = -1
            self.interlevel_state = 0
            self.interlevel_timmer = 0
            Sound_release_music()
            return const.INTERLEVEL_STATE
        return const.MENU_STATE

    def draw_menu_effect(self, screen) -> None:
        self.clear_screen(screen)
        if self.menu_effect == 0:
            self.blit_fullscreen(self.tittle_sfc, screen)
            factor = max(0.0, min(1.0, float(self.menu_timmer) / const.EFFECT_LENGTH))
            if factor < 1.0:
                surface_fader(screen, factor, factor, factor, None)
        elif self.menu_effect == 1:
            y = int(self.screen_h * float(self.menu_timmer) / const.EFFECT_LENGTH)
            y = max(0, min(self.screen_h, y)) - self.screen_h
            rect = self.make_rect(0, y, self.screen_w, self.screen_h)
            sdl2.SDL_BlitSurface(self.tittle_sfc, None, screen, rect)
        elif self.menu_effect == 2:
            factor = max(0.0, min(1.0, float(self.menu_timmer) / const.EFFECT_LENGTH))
            sge_transform(self.tittle_sfc, screen, 0, factor, factor, self.tittle_sfc.contents.w // 2, self.tittle_sfc.contents.h // 2, self.tittle_sfc.contents.w // 2, self.tittle_sfc.contents.h // 2, 0)
        else:
            factor = max(0.0, min(1.0, float(self.menu_timmer) / const.EFFECT_LENGTH))
            angle = (1.0 - factor) * 260.0
            sge_transform(self.tittle_sfc, screen, angle, factor, factor, self.tittle_sfc.contents.w // 2, self.tittle_sfc.contents.h // 2, self.tittle_sfc.contents.w // 2, self.tittle_sfc.contents.h // 2, 0)

    def draw_menu_text(self, screen, y_position: float) -> None:
        glow = abs(__import__("math").sin(self.state_timmer / 10.0)) / 2.0 + 0.125
        cache_key = (self.menu_tittle_text, self.menu_options_text, self.menu_nitems, self.menu_item if self.menu_state == 2 else -1, int(glow * 8), self.menu_state)
        cached = self._menu_surface_cache.get(cache_key)
        if cached is None:
            title_surface = sdlttf.TTF_RenderUTF8_Blended(self.font2big, self.menu_tittle_text.encode("utf-8"), sdl2.SDL_Color(255, 255, 255, 255))
            if self.menu_nitems > 5:
                options_surface = multiline_text_surface2(self.menu_options_text, 0, self.font2small, sdl2.SDL_Color(224, 224, 224, 255), sdl2.SDL_Color(255, 255, 255, 255), self.menu_item if self.menu_state == 2 else -1, glow if self.menu_state == 2 else 0.0)
                y_inc = int(const.FONT_SIZE * 0.65)
                y_start = 9
            elif self.menu_nitems > 4:
                options_surface = multiline_text_surface2(self.menu_options_text, 2, self.font2medium, sdl2.SDL_Color(224, 224, 224, 255), sdl2.SDL_Color(255, 255, 255, 255), self.menu_item if self.menu_state == 2 else -1, glow if self.menu_state == 2 else 0.0)
                y_inc = int(2 + const.FONT_SIZE * 0.8)
                y_start = 12
            else:
                options_surface = multiline_text_surface2(self.menu_options_text, 4, self.font2big, sdl2.SDL_Color(224, 224, 224, 255), sdl2.SDL_Color(255, 255, 255, 255), self.menu_item if self.menu_state == 2 else -1, glow if self.menu_state == 2 else 0.0)
                y_inc = 4 + const.FONT_SIZE
                y_start = 15
            cached = (title_surface, options_surface, y_inc, y_start)
            self._menu_surface_cache[cache_key] = cached
        title_surface, options_surface, y_inc, y_start = cached

        bar_length = int(title_surface.contents.w * 1.1)
        bar = self.make_rect(self.screen_w // 2 - bar_length // 2, int(self.screen_h * y_position), bar_length, 4)
        sdl2.SDL_FillRect(screen, bar, sdl2.SDL_MapRGB(screen.contents.format, 64, 64, 64))
        inner = self.make_rect(bar.x + 1, bar.y + 1, bar_length - 2, 2)
        sdl2.SDL_FillRect(screen, inner, sdl2.SDL_MapRGB(screen.contents.format, 255, 255, 255))

        if self.menu_state in (1, 3):
            factor = max(0.0, min(1.0, float(self.menu_timmer) / const.TEXT_EFFECT_LENGTH))
            tmp = int(factor * title_surface.contents.h)
            src = self.make_rect(0, 0, title_surface.contents.w, tmp)
            dst = self.make_rect(self.screen_w // 2 - title_surface.contents.w // 2, int(self.screen_h * y_position - tmp), title_surface.contents.w, tmp)
            sdl2.SDL_BlitSurface(title_surface, src, screen, dst)
            tmp = int(factor * options_surface.contents.h)
            src = self.make_rect(0, options_surface.contents.h - tmp, options_surface.contents.w, tmp)
            dst = self.make_rect(self.screen_w // 2 - options_surface.contents.w // 2, int(self.screen_h * y_position + 8), options_surface.contents.w, tmp)
            sdl2.SDL_BlitSurface(options_surface, src, screen, dst)
        else:
            title_rect = self.make_rect(self.screen_w // 2 - title_surface.contents.w // 2, int(self.screen_h * y_position - title_surface.contents.h), title_surface.contents.w, title_surface.contents.h)
            sdl2.SDL_BlitSurface(title_surface, None, screen, title_rect)
            options_rect = self.make_rect(self.screen_w // 2 - options_surface.contents.w // 2, int(self.screen_h * y_position + 8), options_surface.contents.w, options_surface.contents.h)
            sdl2.SDL_BlitSurface(options_surface, None, screen, options_rect)
            arrow_rect = self.make_rect(self.screen_w // 2 - options_surface.contents.w // 2 - self.arrow_sfc.contents.w - 10, int(self.screen_h * y_position + y_start) + self.menu_item * y_inc, self.arrow_sfc.contents.w, self.arrow_sfc.contents.h)
            sdl2.SDL_BlitSurface(self.arrow_sfc, None, screen, arrow_rect)

    def draw_scrolling_credits(self, screen) -> None:
        factor = max(0.0, min(1.0, float(self.menu_timmer) / const.EFFECT_LENGTH))
        sdl2.SDL_BlitSurface(self.credits_sfc, None, self.credits2_sfc, None)
        if self.menu_state in (0, 4):
            surface_fader(self.credits2_sfc, factor, factor, factor, None)
        self.menu_credits_timmer += 2
        if self.menu_credits_timmer > self.screen_w:
            if self.menu_credits_timmer - self.screen_w > self.credits_sfc.contents.w:
                self.menu_credits_timmer = 0
                start_x = 0
            else:
                start_x = self.menu_credits_timmer - self.screen_w
        else:
            start_x = 0
        start_x2 = self.screen_w - self.menu_credits_timmer
        if start_x2 < 0:
            start_x2 = 0
        src = self.make_rect(start_x, 0, self.credits_sfc.contents.w - start_x, self.credits_sfc.contents.h)
        dst = self.make_rect(start_x2, self.screen_h - self.credits_sfc.contents.h, src.w, src.h)
        sdl2.SDL_BlitSurface(self.credits2_sfc, src, screen, dst)

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

import sdl2
from ctypes import byref
from sdl2 import SDL_Rect
from sdl2.sdlimage import IMG_Load
from sdl2.sdlmixer import MIX_MAX_VOLUME
from sdl2.sdlttf import TTF_CloseFont, TTF_OpenFont

from . import constants as const
from .auxiliar import create_rgb_surface, draw_line, sdl2 as _unused_sdl2, surface_fader
from .constants import (
    BIGGEST_OBJECT,
    CAR_APPEARING_OFFSET,
    CONSTITUTION_CAR,
    CONSTITUTION_FUEL,
    CONSTITUTION_NONE,
    CONSTITUTION_OIL,
    CONSTITUTION_PLAYER,
    CONSTITUTION_SOLID,
    CONSTITUTION_WATER,
    DEFAULT_START_DELAY,
    FADE_TIME,
    MAPS,
    OBSTACLE_CHANCE,
    OBSTACLE_OIL,
    OBSTACLE_WATER,
    QUICK_PARTS,
    SEMAPHORE_TIME,
)
from .debug import output_debug_message
from .filehandling import FileType, resolve_path
from .list import List
from .object import CObject
from .objects.enemy_fast_car_object import CEnemyFastCarObject
from .objects.enemy_normal_car_object import CEnemyNormalCarObject
from .objects.enemy_racer_car_object import CEnemyRacerCarObject
from .objects.enemy_slidder_car_object import CEnemySlidderCarObject
from .objects.enemy_truck_object import CEnemyTruckObject
from .objects.fuel_object import CFuelObject
from .objects.player_car_object import CPlayerCarObject
from .objects.semaphore_object import CSemaphoreObject
from .sound import (
    Sound_create_music,
    Sound_create_sound,
    Sound_delete_sound,
    Sound_music_volume,
    Sound_play,
)
from .tile import CTile, TILE_SOURCE


@dataclass
class CTyreMark:
    x: int
    y: int
    x2: int
    y2: int


class TokenScanner:
    def __init__(self, text: str) -> None:
        self.tokens = text.split()
        self.index = 0

    def next(self) -> str:
        token = self.tokens[self.index]
        self.index += 1
        return token

    def int(self) -> int:
        return int(self.next())


def _load_image(relative_path: str):
    loaded = IMG_Load(str(resolve_path(relative_path, FileType.GAMEDATA)).encode("utf-8"))
    if not loaded:
        raise FileNotFoundError(relative_path)
    converted = sdl2.SDL_ConvertSurfaceFormat(loaded, sdl2.SDL_PIXELFORMAT_ARGB8888, 0)
    sdl2.SDL_FreeSurface(loaded)
    return converted


class CGame:
    def __init__(self, mapname: str, mode: int, *args):
        self.dx = 0
        self.dy = 0
        self.game_state = 0
        self.game_timmer = 0
        self.game_mode = mode
        self.current_level = 1
        self.game_remake_extras = False
        self.paused = False

        self.tile_sources: list[TILE_SOURCE] = []
        self.tiles: list[list[CTile]] = [[] for _ in range(256)]

        self.player1_car = None
        self.player2_car = None
        self.enemy_cars = None
        self.fuel_sfc = None
        self.empty_sfc = None
        self.fuelscores_sfc = None
        self.obstacles_sfc = None
        self.checkpoint_sfc = None
        self.goal_sfc = None
        self.pause_sfc = None
        self.explosion_sfc = None

        self.player_tiles: list[CTile] = []
        self.enemy_tiles: list[CTile] = []
        self.extra_tiles: list[CTile] = []
        self.explosion_tiles: list[CTile] = []

        self.font = None

        self.S_takefuel = None
        self.S_redlight = None
        self.S_greenlight = None
        self.S_crash = None
        self.S_water = None
        self.S_carstart = None
        self.S_fuelempty = None
        self.S_caradvance = None
        self.S_collision = None
        self.S_truck = None
        self.S_carengine = None
        self.S_carskid = None

        self.background = List[CObject]()
        self.middleground = List[CObject]()
        self.foreground = List[CObject]()
        self.tyre_marks = List[CTyreMark]()
        self.tyre_marks_surface = None
        self.tyre_marks_surface_dirty = True
        self._tyre_marks_count = 0

        self.quick_background = [List[CObject]() for _ in range(QUICK_PARTS)]
        self.quick_middleground = [List[CObject]() for _ in range(QUICK_PARTS)]
        self.quick_foreground = [List[CObject]() for _ in range(QUICK_PARTS)]

        self.objects = List[CObject]()
        self.todelete = List[CObject]()

        self.focusing_objects = List[CObject]()
        self.checkpoint_delay = List[int]()
        self.focusing_fy = List[float]()
        self.focusing_next_car = List[int]()
        self.focusing_next_car_index = List[int]()

        self.start_delay = DEFAULT_START_DELAY
        self.start_delay2 = 0
        self.fastcar_counter = 0
        self.esc_pressed = False
        self.backspace_pressed = False

        self.init_game(mapname)

        if len(args) == 6:
            left_key, right_key, fire_key, score, current_level, extras = args
            self.current_level = current_level
            self.game_remake_extras = extras
            if self.start_delay != DEFAULT_START_DELAY:
                self.objects.Add(CEnemyRacerCarObject((self.dx // 2) + 14, self.dy - 128, self.enemy_tiles[0], self.start_delay, self))
            player = CPlayerCarObject((self.dx // 2) - 30, self.dy - 128, self.player_tiles, 0, 8, left_key, right_key, fire_key, score, self.start_delay + 8, self)
            self.objects.Add(player)
            self.focusing_objects.Add(player)
            self.checkpoint_delay.Add(-1)
            self.focusing_fy.Add(0.66)
            self.focusing_next_car.Add(const.CAR_INTERVAL)
            self.focusing_next_car_index.Add(0)
        elif len(args) == 10:
            left_key1, right_key1, fire_key1, left_key2, right_key2, fire_key2, score1, score2, current_level, extras = args
            self.current_level = current_level
            self.game_remake_extras = extras

            player1 = CPlayerCarObject((self.dx // 2) - 30, self.dy - 128, self.player_tiles, 0, 8, left_key1, right_key1, fire_key1, score1, self.start_delay + 8, self)
            self.objects.Add(player1)
            self.focusing_objects.Add(player1)
            self.checkpoint_delay.Add(-1)
            self.focusing_fy.Add(0.66)
            self.focusing_next_car.Add(const.CAR_INTERVAL)
            self.focusing_next_car_index.Add(0)

            player2 = CPlayerCarObject((self.dx // 2) + 14, self.dy - 128, self.player_tiles, 9, 17, left_key2, right_key2, fire_key2, score2, self.start_delay + 8, self)
            self.objects.Add(player2)
            self.focusing_objects.Add(player2)
            self.checkpoint_delay.Add(-1)
            self.focusing_fy.Add(0.66)
            self.focusing_next_car.Add(const.CAR_INTERVAL)
            self.focusing_next_car_index.Add(0)
        else:
            raise TypeError("CGame constructor arguments do not match original overloads")

    def close(self) -> None:
        self.delete_quick_tables()
        if self.font is not None:
            TTF_CloseFont(self.font)
            self.font = None
        for surface_name in (
            "player1_car",
            "player2_car",
            "enemy_cars",
            "fuel_sfc",
            "empty_sfc",
            "fuelscores_sfc",
            "checkpoint_sfc",
            "goal_sfc",
            "obstacles_sfc",
            "pause_sfc",
            "explosion_sfc",
            "tyre_marks_surface",
        ):
            surface = getattr(self, surface_name)
            if surface is not None:
                sdl2.SDL_FreeSurface(surface)
                setattr(self, surface_name, None)
        for sound_name in (
            "S_takefuel",
            "S_redlight",
            "S_greenlight",
            "S_crash",
            "S_carstart",
            "S_fuelempty",
            "S_caradvance",
            "S_carengine",
            "S_carskid",
            "S_water",
            "S_collision",
            "S_truck",
        ):
            sound = getattr(self, sound_name)
            if sound is not None:
                Sound_delete_sound(sound)
                setattr(self, sound_name, None)

    def __del__(self) -> None:
        # SDL teardown order is explicit in the main loop; avoid destructor-time
        # frees during interpreter shutdown.
        pass

    def init_game(self, mapname: str) -> None:
        self.game_timmer = 0
        self.game_state = 0
        self.start_delay = DEFAULT_START_DELAY

        if not self.load_map(mapname):
            raise RuntimeError(f"Could not load map {mapname}")

        self.init_quick_tables()
        self.font = TTF_OpenFont(str(resolve_path("fonts/tanglewo.ttf", FileType.GAMEDATA)).encode("utf-8"), 16)

        self.player1_car = _load_image("graphics/car1.png")
        self.player2_car = _load_image("graphics/car2.png")
        for start in range(0, 288, 32):
            self.player_tiles.append(CTile(0, start, 32, 32, self.player1_car, True))
        for start in range(0, 288, 32):
            self.player_tiles.append(CTile(0, start, 32, 32, self.player2_car, True))

        self.enemy_cars = _load_image("graphics/enemycars.png")
        self.enemy_tiles.append(CTile(0, 0, 32, 32, self.enemy_cars, True))
        self.enemy_tiles.append(CTile(0, 32, 32, 32, self.enemy_cars, True))
        self.enemy_tiles.append(CTile(0, 64, 32, 32, self.enemy_cars, True))
        self.enemy_tiles.append(CTile(0, 96, 32, 64, self.enemy_cars, True))

        self.fuel_sfc = _load_image("graphics/fuel.png")
        if self.start_delay != DEFAULT_START_DELAY:
            for offset_y in (176, 224, 272, 320, 368):
                self.objects.Add(CEnemyRacerCarObject((self.dx // 2) - 30, self.dy - offset_y, self.enemy_tiles[0], self.start_delay, self))
                self.objects.Add(CEnemyRacerCarObject((self.dx // 2) + 14, self.dy - offset_y, self.enemy_tiles[0], self.start_delay, self))

        self.empty_sfc = _load_image("graphics/empty.png")
        self.fuelscores_sfc = _load_image("graphics/fuel_scores.png")
        self.checkpoint_sfc = _load_image("graphics/checkpoint.png")
        self.goal_sfc = _load_image("graphics/goal.png")
        self.obstacles_sfc = _load_image("graphics/obstacles.png")
        self.pause_sfc = _load_image("graphics/pause.png")
        self.explosion_sfc = _load_image("graphics/explosion.png")

        self.extra_tiles.append(CTile(0, 0, 32, 32, self.fuel_sfc, True))
        self.extra_tiles.append(CTile(0, 0, self.empty_sfc.contents.w // 2, self.empty_sfc.contents.h, self.empty_sfc, False))
        quarter = self.fuelscores_sfc.contents.h // 4
        self.extra_tiles.append(CTile(0, 0, self.fuelscores_sfc.contents.w // 2, quarter, self.fuelscores_sfc, False))
        self.extra_tiles.append(CTile(0, quarter, self.fuelscores_sfc.contents.w // 2, quarter, self.fuelscores_sfc, False))
        self.extra_tiles.append(CTile(0, 2 * quarter, self.fuelscores_sfc.contents.w // 2, quarter, self.fuelscores_sfc, False))
        self.extra_tiles.append(CTile(0, 3 * quarter, self.fuelscores_sfc.contents.w // 2, quarter, self.fuelscores_sfc, False))
        third = self.obstacles_sfc.contents.h // 3
        self.extra_tiles.append(CTile(0, 0, self.obstacles_sfc.contents.w // 3, third, self.obstacles_sfc, True))
        self.extra_tiles.append(CTile(0, third, self.obstacles_sfc.contents.w // 3, third, self.obstacles_sfc, True))
        self.extra_tiles.append(CTile(0, 2 * third, self.obstacles_sfc.contents.w // 3, third, self.obstacles_sfc, True))
        self.extra_tiles.append(CTile(0, 0, self.pause_sfc.contents.w // 2, self.pause_sfc.contents.h, self.pause_sfc, False))
        self.extra_tiles.append(CTile(0, 0, self.checkpoint_sfc.contents.w // 2, self.checkpoint_sfc.contents.h, self.checkpoint_sfc, False))
        self.extra_tiles.append(CTile(0, 0, self.goal_sfc.contents.w // 2, self.goal_sfc.contents.h, self.goal_sfc, False))

        for start in range(0, 768, 64):
            self.explosion_tiles.append(CTile(0, start, 64, 64, self.explosion_sfc, False))

        const.MAX_FUEL = 2500
        const.FUEL_RECHARGE = 400
        const.FUEL_LOSS = 225
        const.CAR_INTERVAL = 38
        if self.game_mode == 1:
            const.MAX_FUEL = 1800
            const.FUEL_RECHARGE = 300
            const.FUEL_LOSS = 150
            const.CAR_INTERVAL = 24
        if self.game_mode == 2:
            const.MAX_FUEL = 1300
            const.FUEL_RECHARGE = 275
            const.FUEL_LOSS = 75
            const.CAR_INTERVAL = 16
        if self.game_mode == 3:
            const.MAX_FUEL = 1250
            const.FUEL_RECHARGE = 200
            const.FUEL_LOSS = 100
            const.CAR_INTERVAL = 12

        self.S_takefuel = Sound_create_sound("sound/takefuel")
        self.S_redlight = Sound_create_sound("sound/redlight")
        self.S_greenlight = Sound_create_sound("sound/greenlight")
        self.S_crash = Sound_create_sound("sound/car_crash")
        self.S_carstart = Sound_create_sound("sound/car_start")
        self.S_fuelempty = Sound_create_sound("sound/fuelempty")
        self.S_caradvance = Sound_create_sound("sound/car_pass")
        self.S_carengine = Sound_create_sound("sound/car_running")
        self.S_carskid = Sound_create_sound("sound/car_brake")
        self.S_water = Sound_create_sound("sound/water")
        self.S_collision = Sound_create_sound("sound/collision")
        self.S_truck = Sound_create_sound("sound/truck")

        self.fastcar_counter = 0
        self.esc_pressed = False
        self.backspace_pressed = False
        self.paused = False

    def get_dx(self) -> int:
        return self.dx

    def get_dy(self) -> int:
        return self.dy

    def get_game_timmer(self) -> int:
        return self.game_timmer

    def get_speeds(self, target: List[int]) -> None:
        for obj in self.focusing_objects:
            target.Add(obj.get_y_speed())

    def get_fuels(self, target: List[int]) -> None:
        for obj in self.focusing_objects:
            target.Add(obj.get_fuel())

    def get_positions(self, target: List[float]) -> None:
        for obj in self.focusing_objects:
            position = float(obj.get_y()) / float(self.dy - 48)
            position = max(0.0, min(1.0, position))
            target.Add(position)

    def get_scores(self, target: List[int]) -> None:
        for obj in self.focusing_objects:
            target.Add(obj.get_score())

    def level_completed(self) -> bool:
        completed = False
        for obj in self.focusing_objects:
            if obj.get_y() >= -32 and obj.get_fuel() > 0:
                return False
            if obj.get_y() < -32:
                completed = True
        return completed

    def init_quick_tables(self) -> None:
        part_size = max(1, self.dy // QUICK_PARTS)
        for collection, quick in (
            (self.background, self.quick_background),
            (self.middleground, self.quick_middleground),
            (self.foreground, self.quick_foreground),
        ):
            for obj in collection:
                index = obj.get_y() // part_size
                index = max(0, min(QUICK_PARTS - 1, index))
                quick[index].Add(obj)

    def delete_quick_tables(self) -> None:
        for index in range(QUICK_PARTS):
            self.quick_background[index].Delete()
            self.quick_middleground[index].Delete()
            self.quick_foreground[index].Delete()

    def get_quick_min_max(self, ymin: int, ymax: int) -> tuple[int, int]:
        part_size = max(1, self.dy // QUICK_PARTS)
        minimum = ((ymin - BIGGEST_OBJECT) // part_size) - 1
        maximum = ymax // part_size
        minimum = max(0, min(QUICK_PARTS - 1, minimum))
        maximum = max(0, min(QUICK_PARTS - 1, maximum))
        return minimum, maximum

    def create_tyre_mark(self, x: int, y: int, x2: int, y2: int) -> Optional[CTyreMark]:
        if y == y2:
            return None
        mark = CTyreMark(x, y, x2, y2)
        self.tyre_marks_surface_dirty = True
        return mark

    def load_map(self, mapname: str) -> bool:
        scanner = TokenScanner(resolve_path(mapname, FileType.GAMEDATA).read_text())
        if scanner.next().upper() != "TILE_SOURCES":
            return False
        n_sources = scanner.int()
        for _ in range(n_sources):
            source = TILE_SOURCE()
            filename = scanner.next()
            source.load_from_filename(filename)
            self.tile_sources.append(source)

        for bank in range(256):
            scanner.next()
            n_tiles = scanner.int()
            self.tiles[bank] = []
            for _ in range(n_tiles):
                filename = scanner.next()
                i1, i2, i3, i4, _mask_type, collision_mask_type = [scanner.int() for _ in range(6)]
                source = next((entry for entry in self.tile_sources if entry.cmp(filename)), None)
                if source is None:
                    return False
                self.tiles[bank].append(CTile(i1, i2, i3, i4, source.sfc, collision_mask_type == 2))

        scanner.next()
        n_objects = scanner.int()
        current_object = 0
        semaphore_object = 0
        semaphore_tiles = [[0, 0] for _ in range(5)]
        for _ in range(n_objects):
            scanner.next()
            object_name = scanner.next()
            if object_name == '"semaphore"':
                semaphore_object = current_object
            n_bitmaps = scanner.int()
            for j in range(n_bitmaps):
                tile_bank, tile_num, n_links = scanner.int(), scanner.int(), scanner.int()
                if object_name == '"semaphore"':
                    semaphore_tiles[j][0] = tile_bank
                    semaphore_tiles[j][1] = tile_num
                for _ in range(n_links):
                    scanner.int()
                    scanner.int()
            n_parts = scanner.int()
            for _ in range(n_parts):
                for _ in range(5):
                    scanner.int()
            scanner.int()
            scanner.int()
            scanner.int()
            scanner.int()
            for _ in range(23):
                for _ in range(n_parts):
                    scanner.next()
            for _ in range(5):
                scanner.int()
            for _ in range(4):
                scanner.int()
            if scanner.int() != 0:
                return False
            if scanner.int() != 0:
                return False
            for _ in range(4):
                scanner.int()
            token = scanner.next()
            if token == "DAMAGE":
                scanner.next()
            scanner.next()
            if scanner.int() != 0:
                return False
            for _ in range(10):
                scanner.int()
            current_object += 1

        scanner.next()
        if scanner.int() != 0:
            return False
        scanner.next()
        if scanner.int() != 1:
            return False
        scanner.next()
        scanner.next()
        scanner.next()
        if scanner.int() != 0:
            return False
        scanner.next()
        if scanner.int() != 1:
            return False
        scanner.next()
        if scanner.int() != 0:
            return False
        scanner.next()
        scanner.int()
        scanner.int()

        scanner.next()
        self.dx = scanner.int() * 16
        self.dy = scanner.int() * 16
        scanner.int()

        n_background = scanner.int()
        for _ in range(n_background):
            x, y, tile_bank, tile_num = scanner.int(), scanner.int(), scanner.int(), scanner.int()
            self.background.Add(CObject(x, y, self.tiles[tile_bank][tile_num], CONSTITUTION_NONE, self))

        n_background_objects = scanner.int()
        for _ in range(n_background_objects):
            x, y, object_type = scanner.int(), scanner.int(), scanner.int()
            if scanner.int() != 0:
                return False
            if object_type == semaphore_object:
                self.objects.Add(CSemaphoreObject(
                    x,
                    y,
                    self.tiles[semaphore_tiles[0][0]][semaphore_tiles[0][1]],
                    self.tiles[semaphore_tiles[1][0]][semaphore_tiles[1][1]],
                    self.tiles[semaphore_tiles[2][0]][semaphore_tiles[2][1]],
                    self.tiles[semaphore_tiles[3][0]][semaphore_tiles[3][1]],
                    self.tiles[semaphore_tiles[4][0]][semaphore_tiles[4][1]],
                    self,
                ))
                self.start_delay = SEMAPHORE_TIME * 7

        n_middleground = scanner.int()
        for _ in range(n_middleground):
            x, y, tile_bank, tile_num = scanner.int(), scanner.int(), scanner.int(), scanner.int()
            self.middleground.Add(CObject(x, y, self.tiles[tile_bank][tile_num], CONSTITUTION_NONE, self))

        n_middleground_objects = scanner.int()
        for _ in range(n_middleground_objects):
            x, y, object_type = scanner.int(), scanner.int(), scanner.int()
            if scanner.int() != 0:
                return False
            if object_type == semaphore_object:
                self.objects.Add(CSemaphoreObject(
                    x,
                    y,
                    self.tiles[semaphore_tiles[0][0]][semaphore_tiles[0][1]],
                    self.tiles[semaphore_tiles[1][0]][semaphore_tiles[1][1]],
                    self.tiles[semaphore_tiles[2][0]][semaphore_tiles[2][1]],
                    self.tiles[semaphore_tiles[3][0]][semaphore_tiles[3][1]],
                    self.tiles[semaphore_tiles[4][0]][semaphore_tiles[4][1]],
                    self,
                ))
                self.start_delay = SEMAPHORE_TIME * 7

        n_foreground = scanner.int()
        for _ in range(n_foreground):
            x, y, tile_bank, tile_num = scanner.int(), scanner.int(), scanner.int(), scanner.int()
            self.foreground.Add(CObject(x, y, self.tiles[tile_bank][tile_num], CONSTITUTION_NONE, self))

        n_foreground_objects = scanner.int()
        for _ in range(n_foreground_objects):
            x, y, object_type = scanner.int(), scanner.int(), scanner.int()
            if scanner.int() != 0:
                return False
            if object_type == semaphore_object:
                self.objects.Add(CSemaphoreObject(
                    x,
                    y,
                    self.tiles[semaphore_tiles[0][0]][semaphore_tiles[0][1]],
                    self.tiles[semaphore_tiles[1][0]][semaphore_tiles[1][1]],
                    self.tiles[semaphore_tiles[2][0]][semaphore_tiles[2][1]],
                    self.tiles[semaphore_tiles[3][0]][semaphore_tiles[3][1]],
                    self.tiles[semaphore_tiles[4][0]][semaphore_tiles[4][1]],
                    self,
                ))
                self.start_delay = SEMAPHORE_TIME * 7
        return True

    def cycle(self, keyboard, old_keyboard) -> bool:
        if keyboard.get(sdl2.SDLK_F1, False) and not old_keyboard.get(sdl2.SDLK_F1, False):
            self.paused = not self.paused
        if self.paused:
            return True

        if self.start_delay > 0:
            self.start_delay -= 1
            self.start_delay2 = 25
            if self.start_delay == 0:
                if self.S_greenlight:
                    Sound_play(self.S_greenlight)
                self.start_delay2 = 25
        elif self.start_delay2 > 0:
            self.start_delay2 -= 1
            if self.start_delay2 == 0:
                Sound_create_music("sound/game_theme" if (self.current_level % 2) == 1 else "sound/game_theme2", -1)

        if self.game_state == 0 and self.game_timmer == 0 and self.S_carstart:
            Sound_play(self.S_carstart)

        if keyboard.get(sdl2.SDLK_ESCAPE, False) and not old_keyboard.get(sdl2.SDLK_ESCAPE, False) and self.game_state == 0:
            self.game_state = 1
            self.game_timmer = FADE_TIME
            self.esc_pressed = True
        if keyboard.get(sdl2.SDLK_BACKSPACE, False) and not old_keyboard.get(sdl2.SDLK_BACKSPACE, False) and self.game_state == 0:
            self.game_state = 1
            self.game_timmer = FADE_TIME
            self.backspace_pressed = True

        for collection in (self.background, self.middleground, self.foreground):
            for obj in collection:
                obj.cycle(keyboard, old_keyboard)

        for obj in list(self.objects):
            if not obj.cycle(keyboard, old_keyboard):
                self.todelete.Add(obj)
        while not self.todelete.EmptyP():
            obj = self.todelete.ExtractIni()
            if obj is not None:
                self.objects.DeleteElement(obj)

        if self.game_state == 0:
            self.game_timmer += 1
        if self.game_state == 1:
            self.game_timmer -= 1

        self._spawn_race_objects()

        if self.game_state == 0:
            found = False
            for obj in self.focusing_objects:
                if obj.get_fuel() > 0 or obj.get_y_speed() != 0:
                    found = True
            if not found:
                self.game_state = 1
                self.game_timmer = FADE_TIME * 2

        if self.game_state == 0 and self.level_completed():
            self.game_state = 1
            self.game_timmer = FADE_TIME * 4

        return not (self.game_state == 1 and self.game_timmer < 0)

    def draw(self, surface, vp: SDL_Rect) -> None:
        if self.focusing_objects.Length() > 0:
            dx = vp.w // self.focusing_objects.Length()
            view = SDL_Rect(vp.x + (self.focusing_objects.Length() - 1) * dx, vp.y, dx - 1 if self.focusing_objects.Length() > 1 else dx, vp.h)
            objects = list(self.focusing_objects)
            focus_fy = list(self.focusing_fy)
            checkpoint_delay = list(self.checkpoint_delay)
            for index, obj in enumerate(objects):
                self._draw_viewport(surface, view, obj, focus_fy[index], checkpoint_delay[index], index)
                view.x -= dx

        fade = float(self.game_timmer) / float(FADE_TIME)
        fade = max(0.0, min(1.0, fade))
        if fade < 1.0:
            surface_fader(surface, fade, fade, fade, vp)
        if self.paused:
            surface_fader(surface, 0.5, 0.5, 0.5, vp)
            self.extra_tiles[9].draw(vp.x + vp.w // 2 - self.extra_tiles[9].get_dx() // 2, vp.y + vp.h // 2 - 64, surface)

    def _draw_viewport(self, surface, logic_vp: SDL_Rect, focusing, fy: float, cp_delay: int, _index: int) -> None:
        speed_ratio = float(-focusing.get_y_speed()) / const.MAX_SPEED if const.MAX_SPEED else 0.0
        fy = (2 * fy + (0.66 + (0.85 - 0.66) * speed_ratio)) / 3
        sx = focusing.get_x() - logic_vp.w // 2
        sy = int(focusing.get_y() - logic_vp.h * fy)
        if sx + logic_vp.w > self.dx:
            sx = self.dx - logic_vp.w
        if sy + logic_vp.h > self.dy:
            sy = self.dy - logic_vp.h
        sx = max(0, sx)
        sy = max(0, sy)

        vp = SDL_Rect(logic_vp.x, logic_vp.y, logic_vp.w, logic_vp.h)
        if vp.w > self.dx:
            vp.x = logic_vp.x + vp.w - self.dx
            vp.w = self.dx
        sx -= vp.x
        sy -= vp.y

        sdl2.SDL_SetClipRect(surface, byref(vp))

        min_index, max_index = self.get_quick_min_max(sy + vp.y, sy + vp.y + vp.h)
        for i in range(min_index, max_index + 1):
            for obj in self.quick_background[i]:
                obj.draw(sx, sy, surface)
        for i in range(min_index, max_index + 1):
            for obj in self.quick_middleground[i]:
                obj.draw(sx, sy, surface)

        if self.game_remake_extras and self.tyre_marks.Length() > 0:
            # Use cached tyre marks surface for better performance
            current_count = self.tyre_marks.Length()
            if self.tyre_marks_surface_dirty or self.tyre_marks_surface is None or current_count != self._tyre_marks_count:
                # Rebuild cached surface when tyre marks change
                if self.tyre_marks_surface is not None:
                    sdl2.SDL_FreeSurface(self.tyre_marks_surface)
                self.tyre_marks_surface = create_rgb_surface(self.dx, self.dy)
                sdl2.SDL_SetSurfaceBlendMode(self.tyre_marks_surface, sdl2.SDL_BLENDMODE_BLEND)
                for tyre_mark in self.tyre_marks:
                    draw_line(self.tyre_marks_surface, tyre_mark.x, tyre_mark.y, tyre_mark.x2, tyre_mark.y2, 0xFF000000)
                    draw_line(self.tyre_marks_surface, tyre_mark.x + 1, tyre_mark.y, tyre_mark.x2 + 1, tyre_mark.y2, 0xFF000000)
                self.tyre_marks_surface_dirty = False
                self._tyre_marks_count = current_count
            # Blit cached surface
            rect = SDL_Rect(-sx, -sy, self.dx, self.dy)
            sdl2.SDL_BlitSurface(self.tyre_marks_surface, None, surface, byref(rect))

        for obj in self.objects:
            obj.draw(sx, sy, surface)
        for i in range(min_index, max_index + 1):
            for obj in self.quick_foreground[i]:
                obj.draw(sx, sy, surface)

        if focusing.get_y() < 384:
            cp_delay += 1
            focusing.reach_goal()
        if cp_delay >= 0:
            tile = self.extra_tiles[11] if self.current_level == 6 else self.extra_tiles[10]
            if vp.w >= tile.get_dx():
                amp = max(0, min(128, cp_delay))
                amp = int((128 - amp) * (128 - amp) / 128)
                offs = abs(int(math.cos(float(cp_delay * cp_delay) / 500.0) * amp))
                tile.draw(vp.x + (vp.w // 2) - (tile.get_dx() // 2), vp.y + 64 - offs, surface)
            else:
                x1 = -tile.get_dx()
                x2 = (vp.w - tile.get_dx()) // 2
                tile.draw(vp.x + x1 + ((x2 - x1) // 32) * cp_delay, vp.y + 32, surface)
        sdl2.SDL_SetClipRect(surface, None)

    def object_collision(self, xoffs: int, yoffs: int, obj: CObject, constitution: int):
        if (constitution & CONSTITUTION_SOLID) != 0:
            minimum, maximum = self.get_quick_min_max(obj.get_y() + yoffs, obj.get_y() + yoffs + obj.get_dy())
            for i in range(minimum, maximum + 1):
                for collection in (self.quick_background[i], self.quick_middleground[i], self.quick_foreground[i]):
                    for other in collection:
                        if other.collision(xoffs, yoffs, obj):
                            return other
        for other in self.objects:
            if other is not obj and other.constitution_test(constitution) and other.collision(xoffs, yoffs, obj):
                return other
        return None

    def add_enemy_car(self, enemy_type: int, y: int):
        obj = None
        if enemy_type == 0:
            obj = CEnemyNormalCarObject(0, y, self.enemy_tiles[1], 0, self)
        if enemy_type == 1:
            obj = CEnemyRacerCarObject(0, y, self.enemy_tiles[0], 0, self)
        if enemy_type == 2:
            obj = CEnemySlidderCarObject(0, y, self.enemy_tiles[2], 0, self)
        if enemy_type == 3:
            obj = CEnemyTruckObject(0, y, self.enemy_tiles[3], 0, self)
        if enemy_type == 4:
            obj = CFuelObject(0, y, self.extra_tiles[0], self)
        if enemy_type == 5:
            obj = CEnemyFastCarObject(0, y, self.enemy_tiles[0], 0, self)
        if obj is None:
            return None
        left, right = 0, self.dx
        coll = False
        last_coll = False
        state = 0
        for i in range(0, self.dx, 4):
            coll = self.object_collision(i, 0, obj, CONSTITUTION_SOLID | CONSTITUTION_CAR) is not None
            if state == 0 and last_coll and not coll:
                left = i
                state = 1
            if state == 1 and not last_coll and coll:
                right = i - 4
                state = 2
            last_coll = coll
        if left == 0 or right == self.dx or left > right:
            return None
        if enemy_type in (0, 1, 2, 5):
            obj.x = int(left + 8 + (random.randrange(right - left - 16)))
            if abs(obj.x - left) < abs(obj.x - right):
                obj.following_right_border = False
                obj.distance_to_border = obj.x - left
            else:
                obj.following_right_border = True
                obj.distance_to_border = right - obj.x
        elif enemy_type == 3:
            obj.x = int(left + 8 + (random.randrange(right - left - 16)))
        elif enemy_type == 4:
            obj.x = (left + right) // 2
        self.objects.Insert(obj)
        return obj

    def add_obstacle(self, obstacle_type: int, y: int):
        obj = None
        if obstacle_type == 0:
            obj = CObject(0, y, self.extra_tiles[6], CONSTITUTION_OIL, self)
        if obstacle_type == 1:
            obj = CObject(0, y, self.extra_tiles[7], CONSTITUTION_WATER, self)
        if obstacle_type == 2:
            obj = CObject(0, y, self.extra_tiles[8], CONSTITUTION_SOLID, self)
        if obj is None:
            return None
        left, right = 0, self.dx
        coll = False
        last_coll = False
        state = 0
        for i in range(0, self.dx, 4):
            coll = self.object_collision(i, 0, obj, CONSTITUTION_SOLID) is not None
            if state == 0 and last_coll and not coll:
                left = i
                state = 1
            if state == 1 and not last_coll and coll:
                right = i - 4
                state = 2
            last_coll = coll
        if (right - left) < 80:
            return None
        obj.x = int(left + 8 + (random.randrange(right - left - 16)))
        self.objects.Insert(obj)
        return obj

    def min_distance_to_players(self, y: int) -> int:
        mindistance = const.PLAYING_WINDOW * 2
        for obj in self.focusing_objects:
            distance = abs(obj.get_y() - y)
            if mindistance > distance:
                mindistance = distance
        return mindistance

    def min_distance_to_other_players(self, y: int, player) -> int:
        mindistance = const.PLAYING_WINDOW * 2
        for obj in self.focusing_objects:
            if obj is not player:
                distance = abs(obj.get_y() - y)
                if mindistance > distance:
                    mindistance = distance
        return mindistance

    def min_distance_to_car(self, y: int) -> int:
        mindistance = const.PLAYING_WINDOW * 2
        for obj in self.objects:
            distance = abs(obj.get_y() - y)
            if mindistance > distance:
                mindistance = distance
        return mindistance

    def first_player(self, player) -> bool:
        first = None
        for obj in self.focusing_objects:
            if first is None or obj.get_y() < first.get_y():
                first = obj
        return first is player

    def find_closest_player(self, x: int, y: int):
        closest = None
        mindistance = 0
        for obj in self.focusing_objects:
            distance = abs(obj.get_y() - y) + abs(obj.get_x() - x)
            if closest is None or distance < mindistance:
                closest = obj
                mindistance = distance
        return closest

    def _spawn_race_objects(self) -> None:
        players = list(self.focusing_objects)
        next_car = list(self.focusing_next_car)
        next_car_index = list(self.focusing_next_car_index)
        for index, obj in enumerate(players):
            if (-obj.get_y_speed()) > 0.8 * const.MAX_SPEED:
                next_car[index] -= 1
            if next_car[index] <= 0:
                new_car_y = obj.get_y() - CAR_APPEARING_OFFSET
                if (self.first_player(obj) or self.min_distance_to_other_players(new_car_y, obj) > const.PLAYING_WINDOW) and self.min_distance_to_car(new_car_y) > 64:
                    patterns = {
                        1: [0, 1, 0, 0, 0, 4, 0, 1, 0, 0, 0, 0, 0, 2, 0, 1, 0, 1, 0, 4, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 4, -1, 6],
                        2: [0, 1, 0, 2, 0, 0, 0, 4, 0, 0, 2, 2, 0, 2, 0, 0, 0, 2, 0, 4, 2, 2, 2, 0, 0, 0, 1, 0, 1, 0, 0, 0, 4, -1, 8],
                        3: [0, 2, 0, 1, 2, 2, 0, 4, 3, 0, 0, 0, 0, 1, 3, 0, 0, 2, 0, 0, 4, 0, 2, 0, 1, 3, 0, 0, 1, 0, 2, 0, 1, 2, 2, 0, 4, -1, 8],
                        4: [0, 1, 3, 0, 0, 2, 0, 4, 3, 0, 0, 1, 3, 0, 0, 2, 3, 0, 0, 4, 3, 0, 0, 0, 3, 0, 0, 2, 0, 0, 0, 1, 3, 0, 0, 2, 0, 4, -1, 8],
                        5: [3, 0, 0, 1, 2, 2, 2, 2, 0, 4, 2, 0, 2, 0, 1, 2, 2, 3, 0, 0, 1, 3, 0, 2, 2, 3, 0, 0, 1, 2, 2, 2, 2, 0, 4, -1, 10],
                        6: [0, 0, 0, 2, 2, 2, 0, 2, 2, 2, 0, 4, 3, 0, 0, 2, 2, 2, 0, 1, 3, 0, 2, 2, 3, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 2, 2, 2, 0, -1, 10],
                    }
                    pattern = patterns[self.current_level]
                    if pattern[next_car_index[index]] == -1:
                        next_car_index[index] = pattern[next_car_index[index] + 1]
                    self.add_enemy_car(pattern[next_car_index[index]], new_car_y)
                    chance = OBSTACLE_CHANCE[self.game_mode][self.current_level - 1]
                    if chance != -1 and random.randrange(chance) == 0:
                        roll = random.randrange(100)
                        if roll < OBSTACLE_OIL[self.game_mode][self.current_level - 1]:
                            self.add_obstacle(0, new_car_y)
                        else:
                            roll -= OBSTACLE_OIL[self.game_mode][self.current_level - 1]
                            if roll < OBSTACLE_WATER[self.game_mode][self.current_level - 1]:
                                self.add_obstacle(1, new_car_y)
                            else:
                                self.add_obstacle(2, new_car_y)
                    self.fastcar_counter += 1
                    fast_chance = const.FASTCAR_CHANCE[self.game_mode][self.current_level - 1]
                    if fast_chance != -1 and self.fastcar_counter > fast_chance:
                        self.fastcar_counter = 0
                        self.add_enemy_car(5, obj.get_y() + 128)
                    if const.CAR_INTERVAL in (12, 16):
                        next_car[index] = const.CAR_INTERVAL + random.randrange(16) - 8
                    else:
                        next_car[index] = const.CAR_INTERVAL
                    next_car_index[index] += 1
        self.focusing_next_car.Delete()
        self.focusing_next_car_index.Delete()
        for value in next_car:
            self.focusing_next_car.Add(value)
        for value in next_car_index:
            self.focusing_next_car_index.Add(value)

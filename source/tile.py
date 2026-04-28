from __future__ import annotations

from ctypes import byref
from dataclasses import dataclass

import sdl2
from sdl2 import SDL_Rect
from sdl2.sdlimage import IMG_Load

from .auxiliar import (
    create_rgb_surface,
    getpixel,
    sge_transform,
    surface_bicolor,
    surface_bw,
    surface_mask_from_bitmap,
    surface_shader,
)
from .filehandling import FileType, resolve_path

# Cache for shader surfaces to avoid recomputing every frame
_shader_cache: dict[tuple[int, int, int, int, int, int], object] = {}
_bicolor_cache: dict[tuple[int, int, int, int, int, int, int, int, int, int], object] = {}


class CollisionMap:
    _cache: dict[int, "CollisionMap"] = {}
    
    def __new__(cls, surface):
        surface_id = id(surface)
        if surface_id in cls._cache:
            return cls._cache[surface_id]
        instance = super().__new__(cls)
        cls._cache[surface_id] = instance
        return instance
    
    def __init__(self, surface) -> None:
        if hasattr(self, 'width'):
            return
        sfc = surface.contents if hasattr(surface, "contents") else surface
        self.width = sfc.w
        self.height = sfc.h
        self.mask = [[False for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                color = getpixel(surface, x, y)
                r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
                sdl2.SDL_GetRGBA(color, sfc.format, byref(r), byref(g), byref(b), byref(a))
                self.mask[y][x] = a.value != 0

    def collides_with(self, other: "CollisionMap", offset_x: int, offset_y: int) -> bool:
        # Fast bounding box rejection first
        # self is at (0,0), other is at (offset_x, offset_y)
        if offset_x >= self.width or offset_x + other.width <= 0:
            return False
        if offset_y >= self.height or offset_y + other.height <= 0:
            return False
        # Compute overlap region
        start_x = max(0, offset_x)
        start_y = max(0, offset_y)
        end_x = min(self.width, offset_x + other.width)
        end_y = min(self.height, offset_y + other.height)
        if start_x >= end_x or start_y >= end_y:
            return False
        # Pixel-perfect collision check on overlapping region
        # Use local variables for faster attribute access
        self_mask = self.mask
        other_mask = other.mask
        oy = offset_y
        ox = offset_x
        for y in range(start_y, end_y):
            self_row = self_mask[y]
            other_row = other_mask[y - oy]
            for x in range(start_x, end_x):
                if self_row[x] and other_row[x - ox]:
                    return True
        return False


class CTile:
    def __init__(self, x: int = 0, y: int = 0, dx: int = 0, dy: int = 0, orig=None, collision: bool = False) -> None:
        self.r = SDL_Rect(x, y, dx, dy)
        self.orig = None
        self.mask_visualization = None
        self.mask_collision = None
        self.collision_data: CollisionMap | None = None
        if orig is not None:
            self.orig = create_rgb_surface(dx, dy)
            sdl2.SDL_SetSurfaceBlendMode(self.orig, sdl2.SDL_BLENDMODE_NONE)
            sdl2.SDL_BlitSurface(orig, self.r, self.orig, None)
            surface_mask_from_bitmap(self.orig, orig, self.r.x + self.r.w, self.r.y)
            sdl2.SDL_SetSurfaceBlendMode(self.orig, sdl2.SDL_BLENDMODE_BLEND)
            if collision:
                r2 = SDL_Rect(self.r.x + self.r.w * 2, self.r.y, self.r.w, self.r.h)
                self.mask_collision = create_rgb_surface(self.r.w, self.r.h)
                sdl2.SDL_BlitSurface(orig, r2, self.mask_collision, None)
                surface_bw(self.mask_collision, 128)
                self.collision_data = CollisionMap(self.mask_collision)

    def draw(self, x: int, y: int, dest) -> None:
        if self.orig is None:
            return
        rect = SDL_Rect(x, y, self.r.w, self.r.h)
        sdl2.SDL_BlitSurface(self.orig, None, dest, byref(rect))

    def draw_mask(self, x: int, y: int, dest) -> None:
        if self.orig is None:
            return
        if self.mask_visualization is None:
            self.mask_visualization = create_rgb_surface(self.r.w, self.r.h)
            for i in range(self.r.w):
                for j in range(self.r.h):
                    color = getpixel(self.orig, i, j)
                    r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
                    sdl2.SDL_GetRGBA(color, self.orig.contents.format, byref(r), byref(g), byref(b), byref(a))
                    mapped = sdl2.SDL_MapRGBA(self.mask_visualization.contents.format, a.value, a.value, a.value, 0)
                    from .auxiliar import putpixel

                    putpixel(self.mask_visualization, i, j, mapped)
        rect = SDL_Rect(x, y, self.r.w, self.r.h)
        sdl2.SDL_BlitSurface(self.mask_visualization, None, dest, byref(rect))

    def draw_collision_mask(self, x: int, y: int, dest) -> None:
        if self.mask_collision is None:
            return
        rect = SDL_Rect(x, y, self.r.w, self.r.h)
        sdl2.SDL_BlitSurface(self.mask_collision, None, dest, byref(rect))

    def draw_scaled(self, x: int, y: int, dest, scale: float) -> None:
        if self.orig is not None:
            sge_transform(self.orig, dest, 0.0, scale, scale, 0, 0, x, y, 0)

    def draw_shaded(self, x: int, y: int, dest, factor: int, red: int, green: int, blue: int, alpha: int) -> None:
        if self.orig is None:
            return
        # Create cache key based on surface id and shader parameters
        cache_key = (id(self.orig), factor, red, green, blue, alpha)
        cached = _shader_cache.get(cache_key)
        if cached is None:
            cached = sdl2.SDL_ConvertSurfaceFormat(self.orig, sdl2.SDL_PIXELFORMAT_ARGB8888, 0)
            surface_shader(cached, float(factor) / 100.0, red, green, blue, alpha)
            # LRU eviction - remove oldest entry if cache is full
            if len(_shader_cache) >= 100:
                oldest_key = next(iter(_shader_cache))
                old_sfc = _shader_cache.pop(oldest_key)
                sdl2.SDL_FreeSurface(old_sfc)
            _shader_cache[cache_key] = cached
        else:
            # Move to end to mark as recently used (LRU)
            del _shader_cache[cache_key]
            _shader_cache[cache_key] = cached
        rect = SDL_Rect(x, y, self.r.w, self.r.h)
        sdl2.SDL_BlitSurface(cached, None, dest, byref(rect))

    def draw_bicolor(self, x: int, y: int, dest, factor: int, r1: int, g1: int, b1: int, a1: int, r2: int, g2: int, b2: int, a2: int) -> None:
        if self.orig is None:
            return
        # Create cache key based on surface id and shader parameters
        cache_key = (id(self.orig), factor, r1, g1, b1, a1, r2, g2, b2, a2)
        cached = _bicolor_cache.get(cache_key)
        if cached is None:
            cached = sdl2.SDL_ConvertSurfaceFormat(self.orig, sdl2.SDL_PIXELFORMAT_ARGB8888, 0)
            surface_bicolor(cached, float(factor) / 100.0, r1, g1, b1, a1, r2, g2, b2, a2)
            # LRU eviction - remove oldest entry if cache is full
            if len(_bicolor_cache) >= 100:
                oldest_key = next(iter(_bicolor_cache))
                old_sfc = _bicolor_cache.pop(oldest_key)
                sdl2.SDL_FreeSurface(old_sfc)
            _bicolor_cache[cache_key] = cached
        else:
            # Move to end to mark as recently used (LRU)
            del _bicolor_cache[cache_key]
            _bicolor_cache[cache_key] = cached
        rect = SDL_Rect(x, y, self.r.w, self.r.h)
        sdl2.SDL_BlitSurface(cached, None, dest, byref(rect))

    def clear(self) -> None:
        self.orig = None
        self.mask_visualization = None
        self.mask_collision = None
        self.collision_data = None

    def free(self) -> None:
        for surface_name in ("orig", "mask_visualization", "mask_collision"):
            surface = getattr(self, surface_name)
            if surface is not None:
                sdl2.SDL_FreeSurface(surface)
                setattr(self, surface_name, None)
        self.collision_data = None

    def instance(self, tile: "CTile") -> None:
        self.r = SDL_Rect(tile.r.x, tile.r.y, tile.r.w, tile.r.h)
        self.orig = tile.orig
        self.mask_visualization = tile.mask_visualization
        self.mask_collision = tile.mask_collision
        self.collision_data = tile.collision_data

    def get_dx(self) -> int:
        return self.r.w

    def get_dy(self) -> int:
        return self.r.h


@dataclass
class TILE_SOURCE:
    fname: str | None = None
    sfc: object | None = None

    def __init__(self, filename: str | None = None) -> None:
        self.fname = None
        self.sfc = None
        if filename is not None:
            self.load_from_filename(filename)

    def load_from_filename(self, filename: str) -> None:
        self.fname = filename
        loaded = IMG_Load(str(resolve_path(filename, FileType.GAMEDATA)).encode("utf-8"))
        if not loaded:
            raise FileNotFoundError(filename)
        self.sfc = create_rgb_surface(loaded.contents.w, loaded.contents.h)
        sdl2.SDL_BlitSurface(loaded, None, self.sfc, None)
        sdl2.SDL_FreeSurface(loaded)

    def save(self, handle) -> bool:
        handle.write(f"{self.fname}\n")
        return True

    def load(self, handle) -> bool:
        line = handle.readline().strip()
        if not line:
            return False
        self.load_from_filename(line)
        return True

    def cmp(self, name: str) -> bool:
        return self.fname == name

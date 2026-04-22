from __future__ import annotations

import math
import time
from ctypes import byref

import sdl2
import sdl2.ext
from sdl2 import SDL_Rect
from sdl2.sdlttf import TTF_RenderText_Blended

from .constants import COLOUR_DEPTH
from .list import List

AMASK = 0xFF000000
BMASK = 0x000000FF
GMASK = 0x0000FF00
RMASK = 0x00FF0000


_init_tick_count = 0.0
_fade_overlay_cache: dict[tuple[int, int], object] = {}


def setupTickCount() -> None:
    global _init_tick_count
    _init_tick_count = time.monotonic()


def GetTickCount() -> int:
    return int((time.monotonic() - _init_tick_count) * 1000)


def pause(milliseconds: int) -> None:
    start = GetTickCount()
    while GetTickCount() - start < milliseconds:
        pass


def cos(value: float) -> float:
    return math.cos(value)


def _surface_value(surface):
    return surface.contents if hasattr(surface, "contents") else surface


def _pixels2d(surface):
    return sdl2.ext.pixels2d(_surface_value(surface), transpose=False)


def _clip_rect(surface) -> SDL_Rect:
    rect = SDL_Rect()
    sdl2.SDL_GetClipRect(surface, byref(rect))
    return rect


def create_rgb_surface(width: int, height: int):
    return sdl2.SDL_CreateRGBSurface(
        0,
        width,
        height,
        COLOUR_DEPTH,
        0x00FF0000,
        0x0000FF00,
        0x000000FF,
        0xFF000000,
    )


def getpixel(surface, x: int, y: int) -> int:
    sfc = _surface_value(surface)
    if x < 0 or y < 0 or x >= sfc.w or y >= sfc.h:
        return 0
    pixels = _pixels2d(sfc)
    return int(pixels[y][x])


def putpixel(surface, x: int, y: int, pixel: int) -> None:
    sfc = _surface_value(surface)
    clip = _clip_rect(surface)
    if x < clip.x or x >= clip.x + clip.w or y < clip.y or y >= clip.y + clip.h:
        return
    if x < 0 or y < 0 or x >= sfc.w or y >= sfc.h:
        return
    pixels = _pixels2d(sfc)
    pixels[y][x] = pixel


def maximumpixel(surface, x: int, y: int, pixel: int) -> None:
    sfc = _surface_value(surface)
    if x < 0 or y < 0 or x >= sfc.w or y >= sfc.h:
        return
    old = getpixel(surface, x, y)
    r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
    r2, g2, b2, a2 = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
    sdl2.SDL_GetRGBA(old, sfc.format, byref(r), byref(g), byref(b), byref(a))
    sdl2.SDL_GetRGBA(pixel, sfc.format, byref(r2), byref(g2), byref(b2), byref(a2))
    merged = sdl2.SDL_MapRGB(sfc.format, max(r.value, r2.value), max(g.value, g2.value), max(b.value, b2.value))
    putpixel(surface, x, y, merged)


def draw_rectangle(surface, x: int, y: int, w: int, h: int, pixel: int) -> None:
    for i in range(w):
        putpixel(surface, x + i, y, pixel)
        putpixel(surface, x + i, y + h - 1, pixel)
    for i in range(h):
        putpixel(surface, x, y + i, pixel)
        putpixel(surface, x + w - 1, y + i, pixel)


def draw_line(surface, x1: int, y1: int, x2: int, y2: int, pixel: int) -> None:
    """Draw a line using Bresenham's algorithm (optimized for software surfaces)."""
    sfc = _surface_value(surface)
    # Get clip rect to avoid drawing outside bounds
    clip = _clip_rect(surface)
    
    act_x = x1
    act_y = y1
    errterm = 0
    d_x = x2 - x1
    d_y = y2 - y1
    incy = -1 if d_y < 0 else 1
    incx = -1 if d_x < 0 else 1
    d_x = abs(d_x)
    d_y = abs(d_y)
    
    # Fast path for horizontal/vertical lines
    if d_x == 0:
        # Vertical line
        start_y = max(min(y1, y2), clip.y)
        end_y = min(max(y1, y2), clip.y + clip.h - 1)
        for y in range(start_y, end_y + 1):
            if clip.x <= x1 < clip.x + clip.w:
                putpixel(surface, x1, y, pixel)
        return
    if d_y == 0:
        # Horizontal line
        start_x = max(min(x1, x2), clip.x)
        end_x = min(max(x1, x2), clip.x + clip.w - 1)
        for x in range(start_x, end_x + 1):
            if clip.y <= y1 < clip.y + clip.h:
                putpixel(surface, x, y1, pixel)
        return
    
    # General case - Bresenham's algorithm with clipping checks
    pixels = _pixels2d(sfc)
    format_ptr = sfc.format
    
    if d_x > d_y:
        for _ in range(d_x + 1):
            if (clip.x <= act_x < clip.x + clip.w and 
                clip.y <= act_y < clip.y + clip.h):
                pixels[act_y][act_x] = pixel
            errterm += d_y
            if errterm >= d_x:
                errterm -= d_x
                act_y += incy
            act_x += incx
    else:
        for _ in range(d_y + 1):
            if (clip.x <= act_x < clip.x + clip.w and 
                clip.y <= act_y < clip.y + clip.h):
                pixels[act_y][act_x] = pixel
            errterm += d_x
            if errterm >= d_y:
                errterm -= d_y
                act_x += incx
            act_y += incy


def surface_fader(surface, r_factor: float, g_factor: float, b_factor: float, rect: SDL_Rect | None) -> None:
    sfc = _surface_value(surface)
    if rect is None:
        rect = SDL_Rect(0, 0, sfc.w, sfc.h)
    if rect.w <= 0 or rect.h <= 0:
        return

    # The port mostly uses uniform fades to black; use SDL blending instead of
    # touching every pixel in Python.
    if abs(r_factor - g_factor) < 1e-6 and abs(g_factor - b_factor) < 1e-6:
        factor = max(0.0, min(1.0, r_factor))
        if factor >= 1.0:
            return
        alpha = int((1.0 - factor) * 255.0)
        key = (rect.w, rect.h)
        overlay = _fade_overlay_cache.get(key)
        if overlay is None:
            overlay = create_rgb_surface(rect.w, rect.h)
            sdl2.SDL_SetSurfaceBlendMode(overlay, sdl2.SDL_BLENDMODE_BLEND)
            _fade_overlay_cache[key] = overlay
        sdl2.SDL_FillRect(overlay, None, sdl2.SDL_MapRGBA(overlay.contents.format, 0, 0, 0, alpha))
        dst = SDL_Rect(rect.x, rect.y, rect.w, rect.h)
        sdl2.SDL_BlitSurface(overlay, None, surface, dst)
        return

    pixels = _pixels2d(sfc)
    for y in range(rect.y, min(rect.y + rect.h, sfc.h)):
        for x in range(rect.x, min(rect.x + rect.w, sfc.w)):
            color = int(pixels[y][x])
            r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
            sdl2.SDL_GetRGBA(color, sfc.format, byref(r), byref(g), byref(b), byref(a))
            pixels[y][x] = sdl2.SDL_MapRGBA(
                sfc.format,
                int(r.value * r_factor),
                int(g.value * g_factor),
                int(b.value * b_factor),
                a.value,
            )


def surface_shader(surface, factor: float, red: int, green: int, blue: int, alpha: int) -> None:
    sfc = _surface_value(surface)
    ifactor = max(0, min(256, int(factor * 256)))
    inv_ifactor = 256 - ifactor
    pixels = _pixels2d(sfc)
    for y in range(sfc.h):
        for x in range(sfc.w):
            color = int(pixels[y][x])
            r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
            sdl2.SDL_GetRGBA(color, sfc.format, byref(r), byref(g), byref(b), byref(a))
            rr = ((red * ifactor) + (r.value * inv_ifactor)) >> 8 if red >= 0 else r.value
            gg = ((green * ifactor) + (g.value * inv_ifactor)) >> 8 if green >= 0 else g.value
            bb = ((blue * ifactor) + (b.value * inv_ifactor)) >> 8 if blue >= 0 else b.value
            aa = ((alpha * ifactor) + (a.value * inv_ifactor)) >> 8 if alpha >= 0 else a.value
            pixels[y][x] = sdl2.SDL_MapRGBA(sfc.format, rr, gg, bb, aa)


def surface_bicolor(surface, factor: float, r1: int, g1: int, b1: int, a1: int, r2: int, g2: int, b2: int, a2: int) -> None:
    sfc = _surface_value(surface)
    ifactor = max(0, min(256, int(factor * 256)))
    inv_ifactor = 256 - ifactor
    pixels = _pixels2d(sfc)
    for y in range(sfc.h):
        for x in range(sfc.w):
            color = int(pixels[y][x])
            r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
            sdl2.SDL_GetRGBA(color, sfc.format, byref(r), byref(g), byref(b), byref(a))
            bw_color = (74 * r.value + 154 * g.value + 28 * b.value) >> 8
            rr = ((((r1 * bw_color) + (r2 * (256 - bw_color))) >> 8) * ifactor + r.value * inv_ifactor) >> 8 if r1 >= 0 and r2 >= 0 else r.value
            gg = ((((g1 * bw_color) + (g2 * (256 - bw_color))) >> 8) * ifactor + g.value * inv_ifactor) >> 8 if g1 >= 0 and g2 >= 0 else g.value
            bb = ((((b1 * bw_color) + (b2 * (256 - bw_color))) >> 8) * ifactor + b.value * inv_ifactor) >> 8 if b1 >= 0 and b2 >= 0 else b.value
            aa = ((((a1 * bw_color) + (a2 * (256 - bw_color))) >> 8) * ifactor + a.value * inv_ifactor) >> 8 if a1 >= 0 and a2 >= 0 else a.value
            pixels[y][x] = sdl2.SDL_MapRGBA(sfc.format, rr, gg, bb, aa)


def surface_automatic_alpha(surface) -> None:
    sfc = _surface_value(surface)
    pixels = _pixels2d(sfc)
    for y in range(sfc.h):
        for x in range(sfc.w):
            color = int(pixels[y][x])
            r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
            sdl2.SDL_GetRGBA(color, sfc.format, byref(r), byref(g), byref(b), byref(a))
            alpha = 255 if (r.value or g.value or b.value) else 0
            pixels[y][x] = sdl2.SDL_MapRGBA(sfc.format, r.value, g.value, b.value, alpha)


def surface_bw(surface, threshold: int) -> None:
    sfc = _surface_value(surface)
    pixels = _pixels2d(sfc)
    for y in range(sfc.h):
        for x in range(sfc.w):
            color = int(pixels[y][x])
            r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
            sdl2.SDL_GetRGBA(color, sfc.format, byref(r), byref(g), byref(b), byref(a))
            alpha = 255 if (r.value >= threshold or g.value >= threshold or b.value >= threshold) else 0
            pixels[y][x] = sdl2.SDL_MapRGBA(sfc.format, alpha, alpha, alpha, alpha)


def surface_mask_from_bitmap(surface, mask, x: int, y: int) -> None:
    sfc = _surface_value(surface)
    mask_sfc = _surface_value(mask)
    pixels = _pixels2d(sfc)
    mask_pixels = _pixels2d(mask_sfc)
    for ix in range(sfc.w):
        for iy in range(sfc.h):
            mask_color = int(mask_pixels[y + iy][x + ix])
            mr, mg, mb, ma = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
            sdl2.SDL_GetRGBA(mask_color, mask_sfc.format, byref(mr), byref(mg), byref(mb), byref(ma))
            mean = (mr.value + mg.value + mb.value) // 3
            color = int(pixels[iy][ix])
            r, g, b, a = sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8(), sdl2.Uint8()
            sdl2.SDL_GetRGBA(color, sfc.format, byref(r), byref(g), byref(b), byref(a))
            pixels[iy][ix] = sdl2.SDL_MapRGBA(sfc.format, r.value, g.value, b.value, mean)


def _render_lines(text: str, font, colors: list[tuple[int, int, int]]) -> list:
    lines = []
    for index, line in enumerate(text.splitlines()):
        color = sdl2.SDL_Color(*colors[min(index, len(colors) - 1)], 255)
        lines.append(TTF_RenderText_Blended(font, line.encode("utf-8"), color))
    return lines


def multiline_text_surface(text: str, line_dist: int, font, color) -> object:
    lines = [line for line in text.splitlines() if line is not None]
    surfaces = []
    max_width = 0
    total_height = 0
    for line in lines:
        surface = TTF_RenderText_Blended(font, line.encode("utf-8"), color)
        surfaces.append(surface)
        max_width = max(max_width, surface.contents.w)
        total_height += surface.contents.h
    if surfaces:
        total_height += line_dist * (len(surfaces) - 1)
    result = create_rgb_surface(max_width or 1, total_height or 1)
    y = 0
    for surface in surfaces:
        rect = SDL_Rect((max_width - surface.contents.w) // 2, y, surface.contents.w, surface.contents.h)
        sdl2.SDL_BlitSurface(surface, None, result, rect)
        y += surface.contents.h + line_dist
        sdl2.SDL_FreeSurface(surface)
    return result


def multiline_text_surface2(text: str, line_dist: int, font, c1, c2, line: int, glow: float):
    rendered = []
    max_width = 0
    total_height = 0
    for current_line, item in enumerate(text.splitlines()):
        if current_line == line:
            # Glow from red to bright white based on glow intensity
            # Normalize glow from [0.125, 0.625] to [0, 1] range
            normalized_glow = (glow - 0.125) / 0.5
            normalized_glow = max(0.0, min(1.0, normalized_glow))
            r = 255  # Full red always
            g = int(255 * normalized_glow)  # Green increases with glow
            b = int(255 * normalized_glow)  # Blue increases with glow
            color = sdl2.SDL_Color(r, g, b, 255)
        else:
            color = c1
        surface = TTF_RenderText_Blended(font, item.encode("utf-8"), color)
        if surface is None:
            # Skip lines that fail to render
            continue
        rendered.append((current_line, surface))
        max_width = max(max_width, surface.contents.w)
        total_height += surface.contents.h
    if rendered:
        total_height += line_dist * (len(rendered) - 1)
    result = create_rgb_surface(max_width or 1, total_height or 1)
    y = 0
    for current_line, surface in rendered:
        rect = SDL_Rect((max_width - surface.contents.w) // 2, y, surface.contents.w, surface.contents.h)
        sdl2.SDL_BlitSurface(surface, None, result, rect)
        y += surface.contents.h + line_dist
        sdl2.SDL_FreeSurface(surface)
    return result


def _transformed_bounds(width: int, height: int, hot_x: float, hot_y: float, angle_deg: float, sx: float, sy: float):
    angle = math.radians(angle_deg)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    corners = [
        (-hot_x, -hot_y),
        (width - hot_x, -hot_y),
        (-hot_x, height - hot_y),
        (width - hot_x, height - hot_y),
    ]
    points = []
    for x, y in corners:
        tx = (x * sx) * cosine - (y * sy) * sine
        ty = (x * sx) * sine + (y * sy) * cosine
        points.append((tx, ty))
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return math.floor(min(xs)), math.ceil(max(xs)), math.floor(min(ys)), math.ceil(max(ys))


def sge_transform(src, dest, angle_deg: float, scale_x: float, scale_y: float, hot_x: int, hot_y: int, pos_x: int, pos_y: int, _flags: int) -> None:
    from sdl2 import sdlgfx
    
    src_sfc = _surface_value(src)
    dest_sfc = _surface_value(dest)
    if scale_x <= 0 or scale_y <= 0:
        return
    
    # Use SDL_gfx optimized rotozoom instead of pixel-per-pixel Python loop
    transformed = sdlgfx.rotozoomSurfaceXY(src, angle_deg, scale_x, scale_y, sdlgfx.SMOOTHING_OFF)
    if not transformed:
        return
    
    try:
        transformed_sfc = _surface_value(transformed)
        dst_w = transformed_sfc.w
        dst_h = transformed_sfc.h
        
        # Calculate position using bounds for backward compatibility
        min_x, max_x, min_y, max_y = _transformed_bounds(src_sfc.w, src_sfc.h, hot_x, hot_y, angle_deg, scale_x, scale_y)
        x = pos_x + min_x
        y = pos_y + min_y
        
        rect = sdl2.SDL_Rect(int(x), int(y), dst_w, dst_h)
        sdl2.SDL_BlitSurface(transformed, None, dest, rect)
    finally:
        sdl2.SDL_FreeSurface(transformed)

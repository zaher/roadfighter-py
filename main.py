from __future__ import annotations

import sys

import sdl2
import sdl2.sdlimage as sdlimage
import sdl2.sdlttf as sdlttf

from source import constants as const
from source.auxiliar import GetTickCount, create_rgb_surface, pause, setupTickCount
from source.roadfighter import RoadFighter
from source.sound import Sound_initialization


def initialize_sdl(fullscreen: bool):
    if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_AUDIO) < 0:
        raise RuntimeError("SDL_Init failed")
    if sdlimage.IMG_Init(sdlimage.IMG_INIT_JPG | sdlimage.IMG_INIT_PNG) == 0:
        raise RuntimeError("IMG_Init failed")
    if sdlttf.TTF_Init() != 0:
        raise RuntimeError("TTF_Init failed")
    Sound_initialization()
    pause(1000)
    flags = sdl2.SDL_WINDOW_RESIZABLE
    if fullscreen:
        flags |= sdl2.SDL_WINDOW_FULLSCREEN
    window = sdl2.SDL_CreateWindow(
        const.APPLICATION_NAME.encode("utf-8"),
        sdl2.SDL_WINDOWPOS_CENTERED,
        sdl2.SDL_WINDOWPOS_CENTERED,
        const.SCREEN_X * 2,
        const.SCREEN_Y * 2,
        flags,
    )
    if not window:
        raise RuntimeError("SDL_CreateWindow failed")
    surface = sdl2.SDL_GetWindowSurface(window)
    return window, surface


def toggle_fullscreen(window, fullscreen: bool):
    fullscreen = not fullscreen
    flags = sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP if fullscreen else 0
    if sdl2.SDL_SetWindowFullscreen(window, flags) != 0:
        raise RuntimeError("SDL_SetWindowFullscreen failed")
    sdl2.SDL_ShowCursor(sdl2.SDL_DISABLE if fullscreen else sdl2.SDL_ENABLE)
    return fullscreen, sdl2.SDL_GetWindowSurface(window)


def present_scaled(logical_surface, window_surface) -> None:
    ww = window_surface.contents.w
    wh = window_surface.contents.h
    scale = min(ww / const.SCREEN_X, wh / const.SCREEN_Y)
    target_w = max(1, int(const.SCREEN_X * scale))
    target_h = max(1, int(const.SCREEN_Y * scale))
    dst = sdl2.SDL_Rect((ww - target_w) // 2, (wh - target_h) // 2, target_w, target_h)
    sdl2.SDL_FillRect(window_surface, None, sdl2.SDL_MapRGB(window_surface.contents.format, 0, 0, 0))
    sdl2.SDL_BlitScaled(logical_surface, None, window_surface, dst)


def main(argv: list[str]) -> int:
    setupTickCount()
    fullscreen = False
    start_level = 1
    if len(argv) == 2:
        try:
            value = int(argv[1])
            if 1 <= value <= 6:
                start_level = value
        except ValueError:
            pass
    window, window_surface = initialize_sdl(fullscreen)
    logical_surface = create_rgb_surface(const.SCREEN_X, const.SCREEN_Y)
    game = RoadFighter(start_level=start_level)
    event = sdl2.SDL_Event()
    time = GetTickCount()
    running = True
    while running:
        while sdl2.SDL_PollEvent(event):
            if event.type == sdl2.SDL_QUIT:
                running = False
            elif event.type == sdl2.SDL_WINDOWEVENT and event.window.event == sdl2.SDL_WINDOWEVENT_SIZE_CHANGED:
                window_surface = sdl2.SDL_GetWindowSurface(window)
            elif event.type == sdl2.SDL_KEYDOWN:
                key = event.key.keysym.sym
                game.keyboard.set(key, True)
                modifiers = sdl2.SDL_GetModState()
                if key == sdl2.SDLK_RETURN and (modifiers & sdl2.KMOD_ALT):
                    fullscreen, window_surface = toggle_fullscreen(window, fullscreen)
                elif sys.platform == "darwin" and key == sdl2.SDLK_f and (modifiers & sdl2.KMOD_GUI):
                    fullscreen, window_surface = toggle_fullscreen(window, fullscreen)
                if key == const.GLOBAL_QUIT_KEY:
                    running = False
            elif event.type == sdl2.SDL_KEYUP:
                game.keyboard.set(event.key.keysym.sym, False)

        act_time = GetTickCount()
        if act_time - time >= const.REDRAWING_PERIOD:
            time = act_time
            running = running and game.cycle()
            game.draw(logical_surface)
            present_scaled(logical_surface, window_surface)
            sdl2.SDL_UpdateWindowSurface(window)
    game.close()
    sdl2.SDL_FreeSurface(logical_surface)
    sdl2.SDL_DestroyWindow(window)
    sdlttf.TTF_Quit()
    sdl2.SDL_Quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

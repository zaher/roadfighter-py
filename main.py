from __future__ import annotations

import sys

import sdl2
import sdl2.sdlimage as sdlimage
import sdl2.sdlttf as sdlttf

from source import constants as const
from source.auxiliar import GetTickCount, create_rgb_surface, pause, setupTickCount
from source.roadfighter import RoadFighter
from source.sound import Sound_initialization

def get_joystick_index(instance_id: int, joysticks: list) -> int:
    """Find joystick index by SDL instance ID (uses cached IDs)"""
    for idx, (joystick, cached_id) in enumerate(joysticks):
        if joystick and cached_id == instance_id:
            return idx
    return -1

def initialize_sdl(fullscreen: bool):
    if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_AUDIO | sdl2.SDL_INIT_JOYSTICK) < 0:
        raise RuntimeError("SDL_Init failed")

    # Initialize joysticks if available
    joysticks = []  # Stores tuples of (joystick_pointer, instance_id)
    num_joysticks = sdl2.SDL_NumJoysticks()
    for i in range(min(num_joysticks, 2)):  # Support up to 2 joysticks
        joystick = sdl2.SDL_JoystickOpen(i)
        if not joystick:
            print(f"Warning: Could not open joystick {i}")
        else:
            instance_id = sdl2.SDL_JoystickInstanceID(joystick)
            print(f"Joystick {i} initialized: {sdl2.SDL_JoystickName(joystick).decode()} (ID: {instance_id})")
            joysticks.append((joystick, instance_id))
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
        int(const.SCREEN_X * 2),
        int(const.SCREEN_Y * 2),
        flags,
    )
    if not window:
        raise RuntimeError("SDL_CreateWindow failed")
    
    # Create hardware-accelerated renderer
    renderer = sdl2.SDL_CreateRenderer(
        window, 
        -1, 
        sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC
    )
    if not renderer:
        print("Warning: Failed to create accelerated renderer, falling back to software")
        renderer = sdl2.SDL_CreateRenderer(window, -1, sdl2.SDL_RENDERER_SOFTWARE)
        if not renderer:
            raise RuntimeError("SDL_CreateRenderer failed")
    
    # Set logical size for automatic scaling
    sdl2.SDL_RenderSetLogicalSize(renderer, const.SCREEN_X, const.SCREEN_Y)
    
    # Create render target texture for the game screen
    screen_texture = sdl2.SDL_CreateTexture(
        renderer,
        sdl2.SDL_PIXELFORMAT_ARGB8888,
        sdl2.SDL_TEXTUREACCESS_STREAMING,
        const.SCREEN_X,
        const.SCREEN_Y
    )
    if not screen_texture:
        raise RuntimeError("Failed to create screen texture")
    
    return window, renderer, screen_texture, joysticks


def toggle_fullscreen(window, fullscreen: bool):
    fullscreen = not fullscreen
    flags = sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP if fullscreen else 0
    if sdl2.SDL_SetWindowFullscreen(window, flags) != 0:
        raise RuntimeError("SDL_SetWindowFullscreen failed")
    sdl2.SDL_ShowCursor(sdl2.SDL_DISABLE if fullscreen else sdl2.SDL_ENABLE)
    return fullscreen


def surface_to_texture(surface, renderer):
    """Convert a surface to a texture for GPU rendering."""
    texture = sdl2.SDL_CreateTextureFromSurface(renderer, surface)
    return texture


def present_surface(surface, renderer, screen_texture):
    """Present a surface using the GPU renderer."""
    # Update texture with surface pixels
    sdl2.SDL_UpdateTexture(screen_texture, None, surface.contents.pixels, surface.contents.pitch)
    
    # Clear and render
    sdl2.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255)
    sdl2.SDL_RenderClear(renderer)
    sdl2.SDL_RenderCopy(renderer, screen_texture, None, None)
    sdl2.SDL_RenderPresent(renderer)


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
    window, renderer, screen_texture, joysticks = initialize_sdl(fullscreen)
    
    # Create surface for software rendering (backward compatibility)
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
                pass  # Renderer handles scaling automatically
            elif event.type == sdl2.SDL_KEYDOWN:
                key = event.key.keysym.sym
                ## Key Down
                game.keyboard.set(key, True)
                modifiers = sdl2.SDL_GetModState()
                if key == sdl2.SDLK_RETURN and (modifiers & sdl2.KMOD_ALT):
                    fullscreen = toggle_fullscreen(window, fullscreen)
                elif sys.platform == "darwin" and key == sdl2.SDLK_f and (modifiers & sdl2.KMOD_GUI):
                    fullscreen = toggle_fullscreen(window, fullscreen)
                if key == const.GLOBAL_QUIT_KEY:
                    running = False
            ## Key Up
            elif event.type == sdl2.SDL_KEYUP:
                game.keyboard.set(event.key.keysym.sym, False)
            ## Axis
            elif event.type == sdl2.SDL_JOYAXISMOTION:
                joy_index = get_joystick_index(event.jaxis.which, joysticks)
                if event.jaxis.axis < 2 and joy_index >= 0:
                    game.keyboard.set_joy_axis(joy_index, event.jaxis.axis, event.jaxis.value)
            ## Joy Button Down
            elif event.type == sdl2.SDL_JOYBUTTONDOWN:
                joy_index = get_joystick_index(event.jbutton.which, joysticks)
                if joy_index >= 0:
                    game.keyboard.set_joy_button(joy_index, event.jbutton.button, True)
            ## Joy Button Up
            elif event.type == sdl2.SDL_JOYBUTTONUP:
                joy_index = get_joystick_index(event.jbutton.which, joysticks)
                if joy_index >= 0:
                    game.keyboard.set_joy_button(joy_index, event.jbutton.button, False)

        act_time = GetTickCount()
        if act_time - time >= const.REDRAWING_PERIOD:
            time = act_time
            running = running and game.cycle()
            
            # Draw to surface (backward compatible)
            game.draw(logical_surface)
            
            # Present via GPU
            present_surface(logical_surface, renderer, screen_texture)
            
    game.close()
    for joystick, instance_id in joysticks:
        if joystick:
            sdl2.SDL_JoystickClose(joystick)
    sdl2.SDL_DestroyTexture(screen_texture)
    sdl2.SDL_DestroyRenderer(renderer)
    sdl2.SDL_DestroyWindow(window)
    sdlttf.TTF_Quit()
    sdl2.SDL_Quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

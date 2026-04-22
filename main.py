from __future__ import annotations

import argparse
import sys

import sdl2
import sdl2.sdlimage as sdlimage
import sdl2.sdlttf as sdlttf

from source import constants as const
from source.auxiliar import GetTickCount, create_rgb_surface, pause, setupTickCount
from source.debug import debug_print, set_debug
from source.roadfighter import RoadFighter
from source.sound import Sound_initialization


def get_controller_index(instance_id: int, controllers: list) -> int:
    """Find controller index by SDL instance ID (uses cached IDs)"""
    for idx, (controller, cached_id, is_gamecontroller) in enumerate(controllers):
        if controller and cached_id == instance_id:
            return idx
    return -1


def initialize_sdl(fullscreen: bool, debug: bool = False):
    if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_AUDIO | sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER) < 0:
        raise RuntimeError("SDL_Init failed")

    # Load game controller mappings from file
    mapping_file = b"./mapping/gamecontrollerdb.txt"
    mappings_loaded = sdl2.SDL_GameControllerAddMappingsFromFile(mapping_file)
    if mappings_loaded > 0:
        debug_print(f"Loaded {mappings_loaded} game controller mappings from {mapping_file.decode()}")
    elif mappings_loaded < 0:
        debug_print(f"Warning: Failed to load game controller mappings from {mapping_file.decode()}")

    # Initialize controllers if available
    # Stores tuples of (controller_pointer, instance_id, is_gamecontroller)
    controllers = []
    num_joysticks = sdl2.SDL_NumJoysticks()
    for i in range(min(num_joysticks, 2)):  # Support up to 2 controllers
        # First try to open as game controller
        if sdl2.SDL_IsGameController(i):
            gamecontroller = sdl2.SDL_GameControllerOpen(i)
            if not gamecontroller:
                debug_print(f"Warning: Could not open game controller {i}")
            else:
                joystick = sdl2.SDL_GameControllerGetJoystick(gamecontroller)
                instance_id = sdl2.SDL_JoystickInstanceID(joystick)
                name = sdl2.SDL_GameControllerName(gamecontroller)
                if name:
                    name = name.decode()
                else:
                    name = "Unknown"
                debug_print(f"GameController {i} initialized: {name} (ID: {instance_id})")
                controllers.append((gamecontroller, instance_id, True))
        else:
            # Fall back to joystick API
            joystick = sdl2.SDL_JoystickOpen(i)
            if not joystick:
                debug_print(f"Warning: Could not open joystick {i}")
            else:
                instance_id = sdl2.SDL_JoystickInstanceID(joystick)
                name = sdl2.SDL_JoystickName(joystick)
                if name:
                    name = name.decode()
                else:
                    name = "Unknown"
                debug_print(f"Joystick {i} initialized: {name} (ID: {instance_id})")
                controllers.append((joystick, instance_id, False))
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
        debug_print("Warning: Failed to create accelerated renderer, falling back to software")
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

    return window, renderer, screen_texture, controllers


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

    parser = argparse.ArgumentParser(
        description="Road Fighter - A retro remake of the classic Konami racing game",
        epilog="Examples:\n"
               "  %(prog)s                    # Start at level 1, select mode from menu\n"
               "  %(prog)s 3                  # Start at level 3\n"
               "  %(prog)s -l b               # Start level 1 in mode B\n"
               "  %(prog)s --level c 5        # Start at level 5 in mode C\n"
               "  %(prog)s --record-replay    # Record gameplay to replay.txt\n"
               "  %(prog)s --load-replay      # Play back replay from replay.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "start_level",
        nargs="?",
        type=int,
        default=1,
        choices=range(1, 7),
        metavar="LEVEL",
        help="Starting level number (1-6). Higher levels are more difficult with more traffic. (default: 1)"
    )
    parser.add_argument(
        "--level", "-l",
        type=str,
        default=None,
        choices=["a", "b", "c"],
        dest="level_type",
        help="Game mode/level type. A=Normal, B=More traffic, C=Night driving. "
             "If not specified, you will select from the menu."
    )
    parser.add_argument(
        "--record-replay",
        action="store_true",
        help="Record all keyboard inputs to replay.txt for later playback. "
             "The replay includes the random seed, so the same game can be replayed exactly."
    )
    parser.add_argument(
        "--load-replay",
        action="store_true",
        help="Load and play back a previously recorded replay from replay.txt. "
             "The game will run automatically using the recorded inputs."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output for SDL and joystick initialization messages."
    )

    args = parser.parse_args(argv[1:])
    set_debug(args.debug)

    fullscreen = False
    start_level = args.start_level
    level_type = args.level_type
    record_replay = args.record_replay
    load_replay = args.load_replay

    window, renderer, screen_texture, controllers = initialize_sdl(fullscreen, args.debug)

    # Create surface for software rendering (backward compatibility)
    logical_surface = create_rgb_surface(const.SCREEN_X, const.SCREEN_Y)

    game = RoadFighter(start_level=start_level, level_type=level_type, record_replay=record_replay, load_replay=load_replay)
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
            # Game Controller Events (preferred)
            ## Controller Axis
            elif event.type == sdl2.SDL_CONTROLLERAXISMOTION:
                ctrl_index = get_controller_index(event.caxis.which, controllers)
                if ctrl_index >= 0:
                    game.keyboard.set_joy_axis(ctrl_index, event.caxis.axis, event.caxis.value)
            ## Controller Button Down
            elif event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
                ctrl_index = get_controller_index(event.cbutton.which, controllers)
                if ctrl_index >= 0:
                    game.keyboard.set_joy_button(ctrl_index, event.cbutton.button, True)
            ## Controller Button Up
            elif event.type == sdl2.SDL_CONTROLLERBUTTONUP:
                ctrl_index = get_controller_index(event.cbutton.which, controllers)
                if ctrl_index >= 0:
                    game.keyboard.set_joy_button(ctrl_index, event.cbutton.button, False)
            # Joystick Events (fallback for non-gamecontroller devices)
            ## Axis
            elif event.type == sdl2.SDL_JOYAXISMOTION:
                ctrl_index = get_controller_index(event.jaxis.which, controllers)
                if ctrl_index >= 0:
                    game.keyboard.set_joy_axis(ctrl_index, event.jaxis.axis, event.jaxis.value)
            ## Joy Button Down
            elif event.type == sdl2.SDL_JOYBUTTONDOWN:
                ctrl_index = get_controller_index(event.jbutton.which, controllers)
                if ctrl_index >= 0:
                    game.keyboard.set_joy_button(ctrl_index, event.jbutton.button, True)
            ## Joy Button Up
            elif event.type == sdl2.SDL_JOYBUTTONUP:
                ctrl_index = get_controller_index(event.jbutton.which, controllers)
                if ctrl_index >= 0:
                    game.keyboard.set_joy_button(ctrl_index, event.jbutton.button, False)
            ## Hat Motion
            elif event.type == sdl2.SDL_JOYHATMOTION:
                ctrl_index = get_controller_index(event.jhat.which, controllers)
                if ctrl_index >= 0:
                    game.keyboard.set_joy_hat(ctrl_index, event.jhat.hat, event.jhat.value)
        act_time = GetTickCount()
        if act_time - time >= const.REDRAWING_PERIOD:
            time = act_time
            running = running and game.cycle()

            # Draw to surface (backward compatible)
            game.draw(logical_surface)

            # Present via GPU
            present_surface(logical_surface, renderer, screen_texture)

    game.close()
    for controller, instance_id, is_gamecontroller in controllers:
        if controller:
            if is_gamecontroller:
                sdl2.SDL_GameControllerClose(controller)
            else:
                sdl2.SDL_JoystickClose(controller)
    sdl2.SDL_DestroyTexture(screen_texture)
    sdl2.SDL_DestroyRenderer(renderer)
    sdl2.SDL_DestroyWindow(window)
    sdlttf.TTF_Quit()
    sdl2.SDL_Quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

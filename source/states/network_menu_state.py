"""Network menu state for P2P multiplayer."""

from __future__ import annotations

import socket

import sdl2

from .. import constants as const
from ..auxiliar import multiline_text_surface2, surface_fader
from ..sound import Sound_play, Sound_release_music
from ..network.p2p import P2PNetwork
from ..network.protocol import PlayerInput


# Network menu states
NETWORK_MENU_MAIN = 0
NETWORK_MENU_HOST = 1
NETWORK_MENU_JOIN = 2
NETWORK_MENU_CONNECTING = 3
NETWORK_MENU_WAITING = 4
NETWORK_MENU_ERROR = 5


def network_menu_cycle(roadfighter) -> int:
    """Handle network menu state machine."""
    
    # Initialize network menu on first entry
    if roadfighter.state_timmer == 0:
        roadfighter.network_menu_state = NETWORK_MENU_MAIN
        roadfighter.network_menu_timmer = 0
        roadfighter.network_menu_item = 0
        roadfighter.network_menu_text = ""
        roadfighter.network_menu_subtext = ""
        roadfighter.network_menu_error = ""
        roadfighter.network_menu_port = "5555"
        roadfighter.network_menu_ip = "127.0.0.1"
        roadfighter.network_menu_editing = False
        roadfighter.network_menu_edit_field = None  # 'ip' or 'port'
        
        # Clean up any existing network
        if roadfighter.network:
            roadfighter.network.stop()
            roadfighter.network = None
    
    # Handle different network menu states
    if roadfighter.network_menu_state == NETWORK_MENU_MAIN:
        return _handle_main_menu(roadfighter)
    elif roadfighter.network_menu_state == NETWORK_MENU_HOST:
        return _handle_host_menu(roadfighter)
    elif roadfighter.network_menu_state == NETWORK_MENU_JOIN:
        return _handle_join_menu(roadfighter)
    elif roadfighter.network_menu_state == NETWORK_MENU_CONNECTING:
        return _handle_connecting(roadfighter)
    elif roadfighter.network_menu_state == NETWORK_MENU_WAITING:
        return _handle_waiting(roadfighter)
    elif roadfighter.network_menu_state == NETWORK_MENU_ERROR:
        return _handle_error(roadfighter)
    
    return const.NETWORK_MENU_STATE


def _handle_main_menu(roadfighter) -> int:
    """Handle the main network menu (Host/Join/Back)."""
    roadfighter.network_menu_text = "NETWORK GAME:"
    roadfighter.network_menu_subtext = "HOST GAME\nJOIN GAME\nBACK\n"
    roadfighter.menu_nitems = 3
    
    # Navigation
    if roadfighter.keyboard[sdl2.SDLK_DOWN] and not roadfighter.old_keyboard[sdl2.SDLK_DOWN]:
        Sound_play(roadfighter.S_menu_move)
        roadfighter.network_menu_item += 1
    if roadfighter.keyboard[sdl2.SDLK_UP] and not roadfighter.old_keyboard[sdl2.SDLK_UP]:
        Sound_play(roadfighter.S_menu_move)
        roadfighter.network_menu_item -= 1
    
    roadfighter.network_menu_item = max(0, min(roadfighter.menu_nitems - 1, roadfighter.network_menu_item))
    
    # Selection
    selecting = (
        roadfighter.keyboard[roadfighter.fire_key] and not roadfighter.old_keyboard[roadfighter.fire_key]
    ) or (
        roadfighter.keyboard[const.GLOBAL_SELECT_KEY] and not roadfighter.old_keyboard[const.GLOBAL_SELECT_KEY]
    )
    
    cancel = roadfighter.keyboard[sdl2.SDLK_ESCAPE] and not roadfighter.old_keyboard[sdl2.SDLK_ESCAPE]
    
    if selecting:
        Sound_play(roadfighter.S_menu_select)
        if roadfighter.network_menu_item == 0:  # Host
            roadfighter.network_menu_state = NETWORK_MENU_HOST
            roadfighter.network_menu_item = 0
        elif roadfighter.network_menu_item == 1:  # Join
            roadfighter.network_menu_state = NETWORK_MENU_JOIN
            roadfighter.network_menu_item = 0
        else:  # Back
            # Return to main menu
            roadfighter.menu_current_menu = 0
            roadfighter.menu_state = 1
            roadfighter.menu_timmer = 0
            roadfighter.menu_item = 0
            return const.MENU_STATE
    
    if cancel:
        Sound_play(roadfighter.S_menu_select)
        roadfighter.menu_current_menu = 0
        roadfighter.menu_state = 1
        roadfighter.menu_timmer = 0
        roadfighter.menu_item = 0
        return const.MENU_STATE
    
    return const.NETWORK_MENU_STATE


def _handle_host_menu(roadfighter) -> int:
    """Handle the host game menu."""
    roadfighter.network_menu_text = "HOST GAME:"
    
    if not roadfighter.network_menu_editing:
        roadfighter.network_menu_subtext = f"PORT: {roadfighter.network_menu_port}\nSTART HOSTING\nBACK\n"
        roadfighter.menu_nitems = 3
        
        # Navigation
        if roadfighter.keyboard[sdl2.SDLK_DOWN] and not roadfighter.old_keyboard[sdl2.SDLK_DOWN]:
            Sound_play(roadfighter.S_menu_move)
            roadfighter.network_menu_item += 1
        if roadfighter.keyboard[sdl2.SDLK_UP] and not roadfighter.old_keyboard[sdl2.SDLK_UP]:
            Sound_play(roadfighter.S_menu_move)
            roadfighter.network_menu_item -= 1
        
        roadfighter.network_menu_item = max(0, min(roadfighter.menu_nitems - 1, roadfighter.network_menu_item))
        
        # Selection
        selecting = (
            roadfighter.keyboard[roadfighter.fire_key] and not roadfighter.old_keyboard[roadfighter.fire_key]
        ) or (
            roadfighter.keyboard[const.GLOBAL_SELECT_KEY] and not roadfighter.old_keyboard[const.GLOBAL_SELECT_KEY]
        )
        
        cancel = roadfighter.keyboard[sdl2.SDLK_ESCAPE] and not roadfighter.old_keyboard[sdl2.SDLK_ESCAPE]
        
        if selecting:
            Sound_play(roadfighter.S_menu_select)
            if roadfighter.network_menu_item == 0:  # Edit port
                roadfighter.network_menu_editing = True
                roadfighter.network_menu_edit_field = 'port'
            elif roadfighter.network_menu_item == 1:  # Start hosting
                try:
                    port = int(roadfighter.network_menu_port)
                    if port < 1024 or port > 65535:
                        raise ValueError("Port out of range")
                    
                    # Initialize network as host
                    roadfighter.network = P2PNetwork(
                        is_host=True,
                        port=port,
                        player_name="Host"
                    )
                    roadfighter.network.on_connect = lambda: _on_network_connect(roadfighter)
                    roadfighter.network.on_disconnect = lambda r: _on_network_disconnect(roadfighter, r)
                    roadfighter.network.start()
                    
                    roadfighter.network_menu_state = NETWORK_MENU_WAITING
                    roadfighter.network_menu_item = 0
                    
                except ValueError as e:
                    roadfighter.network_menu_error = f"Invalid port: {e}"
                    roadfighter.network_menu_state = NETWORK_MENU_ERROR
                except Exception as e:
                    roadfighter.network_menu_error = f"Error: {e}"
                    roadfighter.network_menu_state = NETWORK_MENU_ERROR
            else:  # Back
                roadfighter.network_menu_state = NETWORK_MENU_MAIN
                roadfighter.network_menu_item = 0
        
        if cancel:
            Sound_play(roadfighter.S_menu_select)
            roadfighter.network_menu_state = NETWORK_MENU_MAIN
            roadfighter.network_menu_item = 0
    
    else:  # Editing port
        roadfighter.network_menu_text = "ENTER PORT:"
        roadfighter.network_menu_subtext = f"> {roadfighter.network_menu_port}_\n\nPRESS ENTER TO CONFIRM\nESC TO CANCEL"
        
        # Handle text input
        for key in roadfighter.keyboard.newly_pressed(roadfighter.old_keyboard):
            if sdl2.SDLK_0 <= key <= sdl2.SDLK_9:
                if len(roadfighter.network_menu_port) < 5:
                    roadfighter.network_menu_port += chr(key - sdl2.SDLK_0 + ord('0'))
            elif key == sdl2.SDLK_BACKSPACE:
                if roadfighter.network_menu_port:
                    roadfighter.network_menu_port = roadfighter.network_menu_port[:-1]
            elif key == sdl2.SDLK_RETURN:
                roadfighter.network_menu_editing = False
                roadfighter.network_menu_edit_field = None
            elif key == sdl2.SDLK_ESCAPE:
                roadfighter.network_menu_editing = False
                roadfighter.network_menu_edit_field = None
    
    return const.NETWORK_MENU_STATE


def _handle_join_menu(roadfighter) -> int:
    """Handle the join game menu."""
    roadfighter.network_menu_text = "JOIN GAME:"
    
    if not roadfighter.network_menu_editing:
        roadfighter.network_menu_subtext = (
            f"IP: {roadfighter.network_menu_ip}\n"
            f"PORT: {roadfighter.network_menu_port}\n"
            f"CONNECT\n"
            f"BACK\n"
        )
        roadfighter.menu_nitems = 4
        
        # Navigation
        if roadfighter.keyboard[sdl2.SDLK_DOWN] and not roadfighter.old_keyboard[sdl2.SDLK_DOWN]:
            Sound_play(roadfighter.S_menu_move)
            roadfighter.network_menu_item += 1
        if roadfighter.keyboard[sdl2.SDLK_UP] and not roadfighter.old_keyboard[sdl2.SDLK_UP]:
            Sound_play(roadfighter.S_menu_move)
            roadfighter.network_menu_item -= 1
        
        roadfighter.network_menu_item = max(0, min(roadfighter.menu_nitems - 1, roadfighter.network_menu_item))
        
        # Selection
        selecting = (
            roadfighter.keyboard[roadfighter.fire_key] and not roadfighter.old_keyboard[roadfighter.fire_key]
        ) or (
            roadfighter.keyboard[const.GLOBAL_SELECT_KEY] and not roadfighter.old_keyboard[const.GLOBAL_SELECT_KEY]
        )
        
        cancel = roadfighter.keyboard[sdl2.SDLK_ESCAPE] and not roadfighter.old_keyboard[sdl2.SDLK_ESCAPE]
        
        if selecting:
            Sound_play(roadfighter.S_menu_select)
            if roadfighter.network_menu_item == 0:  # Edit IP
                roadfighter.network_menu_editing = True
                roadfighter.network_menu_edit_field = 'ip'
            elif roadfighter.network_menu_item == 1:  # Edit port
                roadfighter.network_menu_editing = True
                roadfighter.network_menu_edit_field = 'port'
            elif roadfighter.network_menu_item == 2:  # Connect
                try:
                    port = int(roadfighter.network_menu_port)
                    if port < 1024 or port > 65535:
                        raise ValueError("Port out of range")
                    
                    # Initialize network as client
                    roadfighter.network = P2PNetwork(
                        is_host=False,
                        host_ip=roadfighter.network_menu_ip,
                        port=port,
                        player_name="Player"
                    )
                    roadfighter.network.on_connect = lambda: _on_network_connect(roadfighter)
                    roadfighter.network.on_disconnect = lambda r: _on_network_disconnect(roadfighter, r)
                    roadfighter.network.start()
                    
                    roadfighter.network_menu_state = NETWORK_MENU_CONNECTING
                    roadfighter.network_menu_timmer = 0
                    roadfighter.network_menu_item = 0
                    
                except ValueError as e:
                    roadfighter.network_menu_error = f"Invalid port: {e}"
                    roadfighter.network_menu_state = NETWORK_MENU_ERROR
                except Exception as e:
                    roadfighter.network_menu_error = f"Error: {e}"
                    roadfighter.network_menu_state = NETWORK_MENU_ERROR
            else:  # Back
                roadfighter.network_menu_state = NETWORK_MENU_MAIN
                roadfighter.network_menu_item = 0
        
        if cancel:
            Sound_play(roadfighter.S_menu_select)
            roadfighter.network_menu_state = NETWORK_MENU_MAIN
            roadfighter.network_menu_item = 0
    
    else:  # Editing field
        if roadfighter.network_menu_edit_field == 'ip':
            roadfighter.network_menu_text = "ENTER IP:"
            current_text = roadfighter.network_menu_ip
        else:
            roadfighter.network_menu_text = "ENTER PORT:"
            current_text = roadfighter.network_menu_port
        
        roadfighter.network_menu_subtext = f"> {current_text}_\n\nPRESS ENTER TO CONFIRM\nESC TO CANCEL"
        
        # Handle text input
        for key in roadfighter.keyboard.newly_pressed(roadfighter.old_keyboard):
            if roadfighter.network_menu_edit_field == 'port':
                # Port only accepts numbers
                if sdl2.SDLK_0 <= key <= sdl2.SDLK_9:
                    if len(current_text) < 5:
                        current_text += chr(key - sdl2.SDLK_0 + ord('0'))
            else:
                # IP accepts numbers and dots
                if sdl2.SDLK_0 <= key <= sdl2.SDLK_9 or key == sdl2.SDLK_PERIOD:
                    if len(current_text) < 15:
                        if key == sdl2.SDLK_PERIOD:
                            current_text += '.'
                        else:
                            current_text += chr(key - sdl2.SDLK_0 + ord('0'))
            
            if key == sdl2.SDLK_BACKSPACE:
                if current_text:
                    current_text = current_text[:-1]
            elif key == sdl2.SDLK_RETURN:
                roadfighter.network_menu_editing = False
                roadfighter.network_menu_edit_field = None
            elif key == sdl2.SDLK_ESCAPE:
                roadfighter.network_menu_editing = False
                roadfighter.network_menu_edit_field = None
            
            # Update the actual field
            if roadfighter.network_menu_edit_field == 'ip':
                roadfighter.network_menu_ip = current_text
            else:
                roadfighter.network_menu_port = current_text
    
    return const.NETWORK_MENU_STATE


def _handle_connecting(roadfighter) -> int:
    """Handle the connecting state."""
    roadfighter.network_menu_text = "CONNECTING..."
    roadfighter.network_menu_subtext = f"Connecting to {roadfighter.network_menu_ip}:{roadfighter.network_menu_port}\n\nPRESS ESC TO CANCEL"
    
    # Update network to process connection
    if roadfighter.network:
        roadfighter.network.update()
        
        if roadfighter.network.connected:
            # Connection successful - will be handled by callback
            pass
        elif roadfighter.network.connection_state == "disconnected":
            roadfighter.network_menu_error = "Connection failed"
            roadfighter.network_menu_state = NETWORK_MENU_ERROR
            if roadfighter.network:
                roadfighter.network.stop()
                roadfighter.network = None
    
    # Cancel
    if roadfighter.keyboard[sdl2.SDLK_ESCAPE] and not roadfighter.old_keyboard[sdl2.SDLK_ESCAPE]:
        if roadfighter.network:
            roadfighter.network.stop()
            roadfighter.network = None
        roadfighter.network_menu_state = NETWORK_MENU_JOIN
        roadfighter.network_menu_item = 0
    
    return const.NETWORK_MENU_STATE


def _handle_waiting(roadfighter) -> int:
    """Handle the waiting for client state (host)."""
    roadfighter.network_menu_text = "WAITING FOR PLAYER..."
    
    # Get local IP to display
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "localhost"
    
    roadfighter.network_menu_subtext = (
        f"Your IP: {local_ip}\n"
        f"Port: {roadfighter.network_menu_port}\n\n"
        f"Waiting for opponent...\n\n"
        f"PRESS ESC TO CANCEL"
    )
    
    # Update network
    if roadfighter.network:
        roadfighter.network.update()
        
        if roadfighter.network.connection_state == "disconnected":
            roadfighter.network_menu_error = "Connection lost"
            roadfighter.network_menu_state = NETWORK_MENU_ERROR
            if roadfighter.network:
                roadfighter.network.stop()
                roadfighter.network = None
    
    # Cancel
    if roadfighter.keyboard[sdl2.SDLK_ESCAPE] and not roadfighter.old_keyboard[sdl2.SDLK_ESCAPE]:
        if roadfighter.network:
            roadfighter.network.stop()
            roadfighter.network = None
        roadfighter.network_menu_state = NETWORK_MENU_HOST
        roadfighter.network_menu_item = 0
    
    return const.NETWORK_MENU_STATE


def _handle_error(roadfighter) -> int:
    """Handle error state."""
    roadfighter.network_menu_text = "ERROR"
    roadfighter.network_menu_subtext = f"{roadfighter.network_menu_error}\n\nPRESS ANY KEY TO CONTINUE"
    
    # Wait for any key
    if roadfighter.keyboard.newly_pressed(roadfighter.old_keyboard):
        roadfighter.network_menu_state = NETWORK_MENU_MAIN
        roadfighter.network_menu_item = 0
        roadfighter.network_menu_error = ""
    
    return const.NETWORK_MENU_STATE


def _on_network_connect(roadfighter):
    """Callback when network connection is established."""
    print(f"[NETWORK] Connected! Starting game...")
    
    # Set up network game parameters
    roadfighter.n_players = 2
    roadfighter.is_network_game = True
    
    # Transition to game setup
    roadfighter.network_menu_state = NETWORK_MENU_MAIN
    
    # Trigger game start via menu exit
    roadfighter.menu_current_menu = 6  # Network game menu
    roadfighter.menu_item = 0  # First difficulty (Level A)
    roadfighter.menu_state = 4  # Exit menu state
    roadfighter.menu_timmer = const.EFFECT_LENGTH
    
    # Release music like normal game start
    Sound_release_music()


def _on_network_disconnect(roadfighter, reason: str):
    """Callback when network connection is lost."""
    print(f"[NETWORK] Disconnected: {reason}")
    roadfighter.network_menu_error = f"Disconnected: {reason}"
    roadfighter.network_menu_state = NETWORK_MENU_ERROR


def network_menu_draw(roadfighter, screen) -> None:
    """Draw the network menu."""
    y_position = 0.55
    
    # Clear screen and draw title
    roadfighter.clear_screen(screen)
    roadfighter.blit_fullscreen(roadfighter.tittle_sfc, screen)
    
    # Draw menu text
    if hasattr(roadfighter, 'network_menu_text') and roadfighter.network_menu_text:
        glow = abs(__import__("math").sin(roadfighter.state_timmer / 10.0)) * 0.5 + 0.5
        
        # Title
        from sdl2.sdlttf import TTF_RenderUTF8_Blended
        from sdl2 import SDL_Color
        
        title_surface = TTF_RenderUTF8_Blended(
            roadfighter.font2big,
            roadfighter.network_menu_text.encode("utf-8"),
            SDL_Color(255, 255, 255, 255)
        )
        
        # Check if title rendered successfully
        if title_surface is None:
            return
        
        # Options text
        options_surface = multiline_text_surface2(
            roadfighter.network_menu_subtext,
            4,
            roadfighter.font2medium,
            SDL_Color(224, 224, 224, 255),
            SDL_Color(255, 255, 255, 255),
            roadfighter.network_menu_item if not roadfighter.network_menu_editing else -1,
            glow if not roadfighter.network_menu_editing else 0.0
        )
        
        # Check if options rendered successfully
        if options_surface is None:
            sdl2.SDL_FreeSurface(title_surface)
            return
        
        # Draw title bar
        bar_length = int(title_surface.contents.w * 1.1)
        bar = roadfighter.make_rect(
            roadfighter.screen_w // 2 - bar_length // 2,
            int(roadfighter.screen_h * y_position),
            bar_length,
            4
        )
        sdl2.SDL_FillRect(screen, bar, sdl2.SDL_MapRGB(screen.contents.format, 64, 64, 64))
        inner = roadfighter.make_rect(bar.x + 1, bar.y + 1, bar_length - 2, 2)
        sdl2.SDL_FillRect(screen, inner, sdl2.SDL_MapRGB(screen.contents.format, 255, 255, 255))
        
        # Draw title
        title_rect = roadfighter.make_rect(
            roadfighter.screen_w // 2 - title_surface.contents.w // 2,
            int(roadfighter.screen_h * y_position - title_surface.contents.h),
            title_surface.contents.w,
            title_surface.contents.h
        )
        sdl2.SDL_BlitSurface(title_surface, None, screen, title_rect)
        
        # Draw options
        options_rect = roadfighter.make_rect(
            roadfighter.screen_w // 2 - options_surface.contents.w // 2,
            int(roadfighter.screen_h * y_position + 8),
            options_surface.contents.w,
            options_surface.contents.h
        )
        sdl2.SDL_BlitSurface(options_surface, None, screen, options_rect)
        
        # Draw arrow if not editing
        if not roadfighter.network_menu_editing and roadfighter.network_menu_state in (NETWORK_MENU_MAIN, NETWORK_MENU_HOST, NETWORK_MENU_JOIN):
            y_inc = int(const.FONT_SIZE * 0.8) + 2
            y_start = 12
            arrow_rect = roadfighter.make_rect(
                roadfighter.screen_w // 2 - options_surface.contents.w // 2 - roadfighter.arrow_sfc.contents.w - 10,
                int(roadfighter.screen_h * y_position + y_start) + roadfighter.network_menu_item * y_inc,
                roadfighter.arrow_sfc.contents.w,
                roadfighter.arrow_sfc.contents.h
            )
            sdl2.SDL_BlitSurface(roadfighter.arrow_sfc, None, screen, arrow_rect)
        
        # Clean up surfaces
        sdl2.SDL_FreeSurface(title_surface)
        sdl2.SDL_FreeSurface(options_surface)
    
    # Draw scrolling credits
    roadfighter.draw_scrolling_credits(screen)

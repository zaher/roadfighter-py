from __future__ import annotations

import ctypes
from pathlib import Path
from typing import Optional

from sdl2 import SDL_GetCurrentAudioDriver
from sdl2.audio import AUDIO_S16
from sdl2.sdlmixer import (
    MIX_DEFAULT_CHANNELS,
    MIX_MAX_VOLUME,
    Mix_AllocateChannels,
    Mix_Chunk,
    Mix_CloseAudio,
    Mix_FreeChunk,
    Mix_FreeMusic,
    Mix_HaltChannel,
    Mix_HaltMusic,
    Mix_LoadMUS,
    Mix_LoadWAV,
    Mix_OpenAudio,
    Mix_PauseMusic,
    Mix_PlayChannel,
    Mix_PlayMusic,
    Mix_ReserveChannels,
    Mix_ResumeMusic,
    Mix_SetPanning,
    Mix_Volume,
    Mix_VolumeMusic,
)

from .debug import output_debug_message
from .filehandling import FileType, resolve_path


AUDIO_BUFFER = 2048
SOUNDT = object

sound_enabled = False
music_sound = None
n_channels = -1


def _resolve_sound_file(base_name: str) -> Optional[Path]:
    for ext in (".WAV", ".OGG", ".MP3", ".wav", ".ogg", ".mp3"):
        path = resolve_path(f"{base_name}{ext}", FileType.GAMEDATA)
        if path.is_file() and path.stat().st_size > 0:
            return path
    return None


def Sound_initialization(nc: int = 0, nrc: int = 0) -> int:
    global sound_enabled, n_channels
    audio_rate = 44100
    audio_channels = MIX_DEFAULT_CHANNELS
    audio_bufsize = AUDIO_BUFFER
    n_channels = 8

    result = Mix_OpenAudio(audio_rate, AUDIO_S16, audio_channels, audio_bufsize)
    if result != 0:
        sound_enabled = False
        output_debug_message("Unable to open audio, running without sound.\n")
        return -1

    sound_enabled = True
    SDL_GetCurrentAudioDriver()
    if nc > 0:
        n_channels = Mix_AllocateChannels(nc)
    if nrc > 0:
        Mix_ReserveChannels(nrc)
    return n_channels


def Sound_release() -> None:
    global sound_enabled
    Sound_release_music()
    if sound_enabled:
        Mix_CloseAudio()
    sound_enabled = False


def Stop_playback() -> None:
    global sound_enabled
    if sound_enabled:
        Sound_pause_music()
        Mix_CloseAudio()
        sound_enabled = False


def Resume_playback(nc: int = 0, nrc: int = 0) -> int:
    result = Sound_initialization(nc, nrc)
    Sound_unpause_music()
    return result


def Sound_file_test(base_name: str) -> bool:
    return _resolve_sound_file(base_name) is not None


def Sound_create_sound(base_name: str):
    if not sound_enabled:
        return None
    path = _resolve_sound_file(base_name)
    if path is None:
        raise FileNotFoundError(f"Could not load sound file: {base_name}")
    return Mix_LoadWAV(str(path).encode("utf-8"))


def Sound_delete_sound(sound) -> None:
    if sound_enabled and sound is not None:
        Mix_FreeChunk(sound)


def Sound_play(sound, volume: Optional[int] = None) -> int:
    if not sound_enabled or sound is None:
        return -1
    channel = Mix_PlayChannel(-1, sound, 0)
    if volume is not None:
        Mix_Volume(channel, volume)
    return channel


def Sound_play_continuous(sound, volume: Optional[int] = None) -> int:
    if not sound_enabled or sound is None:
        return -1
    channel = Mix_PlayChannel(-1, sound, -1)
    if volume is not None:
        Mix_Volume(channel, volume)
    return channel


def Sound_play_ch(sound, channel: int, volume: Optional[int] = None) -> None:
    if not sound_enabled or sound is None or channel >= n_channels:
        return
    actual_channel = Mix_PlayChannel(channel, sound, 0)
    if volume is not None:
        Mix_Volume(actual_channel, volume)


def _create_stream(base_name: str):
    if not sound_enabled:
        return None
    path = _resolve_sound_file(base_name)
    if path is None:
        raise FileNotFoundError(f"Could not load music file: {base_name}")
    return Mix_LoadMUS(str(path).encode("utf-8"))


def Sound_create_music(base_name: str | None, loops: int) -> None:
    global music_sound
    if not sound_enabled:
        return
    if base_name is None:
        music_sound = None
        return
    music_sound = _create_stream(base_name)
    Mix_PlayMusic(music_sound, loops)


def Sound_release_music() -> None:
    global music_sound
    if not sound_enabled:
        return
    Mix_HaltMusic()
    if music_sound is not None:
        Mix_FreeMusic(music_sound)
        music_sound = None


def Sound_pause_music() -> None:
    Mix_PauseMusic()


def Sound_unpause_music() -> None:
    Mix_ResumeMusic()


def Sound_music_volume(volume: int) -> None:
    Mix_VolumeMusic(max(0, min(MIX_MAX_VOLUME, volume)))


def Sound_halt_channel(channel: int) -> None:
    if channel >= 0:
        Mix_HaltChannel(channel)


def Sound_make_working_chunk(source):
    if source is None:
        return None, None
    alen = source.contents.alen
    buffer = (ctypes.c_ubyte * alen)()
    chunk = Mix_Chunk()
    chunk.allocated = 1
    chunk.abuf = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    chunk.alen = alen
    chunk.volume = MIX_MAX_VOLUME
    return chunk, buffer


def Sound_resample_working_chunk(source, working_chunk, factor: float, pan: str = "both") -> None:
    if source is None or working_chunk is None:
        return

    src_frames = source.contents.alen // 4
    dst_frames = working_chunk.alen // 4
    src_samples = ctypes.cast(source.contents.abuf, ctypes.POINTER(ctypes.c_int16))
    dst_samples = ctypes.cast(working_chunk.abuf, ctypes.POINTER(ctypes.c_int16))

    ctypes.memset(working_chunk.abuf, 0, working_chunk.alen)

    for j in range(dst_frames):
        k = int(j * factor)
        if k >= src_frames:
            break
        left = src_samples[k * 2]
        right = src_samples[k * 2 + 1]
        if pan == "right_only":
            dst_samples[j * 2] = 0
            dst_samples[j * 2 + 1] = (left + right) // 2
        elif pan == "left_only":
            dst_samples[j * 2] = (left + right) // 2
            dst_samples[j * 2 + 1] = 0
        else:
            dst_samples[j * 2] = left
            dst_samples[j * 2 + 1] = right


def Sound_play_working_chunk(working_chunk, channel: int = -1) -> int:
    if not sound_enabled or working_chunk is None:
        return -1
    chunk_ptr = ctypes.pointer(working_chunk)
    if channel >= 0:
        Mix_HaltChannel(channel)
    return Mix_PlayChannel(channel, chunk_ptr, 0)


def Sound_play_chunk_loop(working_chunk, channel: int = -1) -> int:
    """Play a working chunk in an infinite loop on the given channel."""
    if not sound_enabled or working_chunk is None:
        return -1
    chunk_ptr = ctypes.pointer(working_chunk)
    return Mix_PlayChannel(channel, chunk_ptr, -1)


class EngineSoundPlayer:
    """Continuous looping engine sound with real-time pitch shifting using SDL audio."""

    def __init__(self, source_sound, channel: int = -1):
        self.source_sound = source_sound
        self.channel = channel
        self.working_chunk = None
        self.buffer = None
        self.current_factor = 1.0
        self.is_playing = False
        self._pan = "both"
        if source_sound is not None:
            self.working_chunk, self.buffer = Sound_make_working_chunk(source_sound)

    def set_pan(self, pan: str) -> None:
        """Set panning: 'both', 'left_only', or 'right_only'."""
        self._pan = pan

    def update_pitch(self, speed_ratio: float) -> None:
        """Update pitch based on car speed ratio (0.0 to 1.0)."""
        # Pitch shift from -1 semitone (0.8408964) to +1 semitone (1.259921)
        factor = 0.8408964 + (1.259921 - 0.8408964) * speed_ratio
        factor = max(0.8408964, min(1.259921, factor))
        self.current_factor = factor

    def play(self) -> int:
        """Start playing the engine sound in a continuous loop."""
        if not sound_enabled or self.working_chunk is None:
            return -1
        if self.is_playing:
            return self.channel
        
        # Resample with initial factor
        Sound_resample_working_chunk(
            self.source_sound, self.working_chunk, self.current_factor, self._pan
        )
        
        # Play on a channel with -1 loops (infinite)
        chunk_ptr = ctypes.pointer(self.working_chunk)
        self.channel = Mix_PlayChannel(self.channel, chunk_ptr, -1)
        self.is_playing = self.channel >= 0
        return self.channel

    def stop(self) -> None:
        """Stop the engine sound."""
        if self.channel >= 0:
            Mix_HaltChannel(self.channel)
        self.is_playing = False
        self.channel = -1

    def refresh(self) -> None:
        """Refresh the sound buffer with updated pitch (call periodically)."""
        if not sound_enabled or not self.is_playing or self.working_chunk is None:
            return
        
        # Resample the source with the current factor
        Sound_resample_working_chunk(
            self.source_sound, self.working_chunk, self.current_factor, self._pan
        )
        
        # Restart playback on the same channel to apply new buffer
        chunk_ptr = ctypes.pointer(self.working_chunk)
        Mix_HaltChannel(self.channel)
        self.channel = Mix_PlayChannel(self.channel, chunk_ptr, -1)
        if self.channel < 0:
            self.is_playing = False


def EngineSound_create(source_sound, channel: int = -1):
    """Create an engine sound player for continuous looping with pitch shifting."""
    if not sound_enabled or source_sound is None:
        return None
    return EngineSoundPlayer(source_sound, channel)


def EngineSound_delete(engine_player) -> None:
    """Delete an engine sound player."""
    if engine_player is not None:
        engine_player.stop()
        engine_player.working_chunk = None
        engine_player.buffer = None


def EngineSound_play(engine_player, speed_ratio: float = 0.0, pan: str = "both") -> int:
    """Start playing engine sound with initial pitch based on speed ratio."""
    if engine_player is None:
        return -1
    engine_player.set_pan(pan)
    engine_player.update_pitch(speed_ratio)
    return engine_player.play()


def EngineSound_stop(engine_player) -> None:
    """Stop the engine sound."""
    if engine_player is not None:
        engine_player.stop()


def EngineSound_update(engine_player, speed_ratio: float) -> None:
    """Update engine sound pitch based on current speed ratio (call each frame)."""
    if engine_player is None or not engine_player.is_playing:
        return
    engine_player.update_pitch(speed_ratio)
    engine_player.refresh()

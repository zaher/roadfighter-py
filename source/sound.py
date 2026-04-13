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

    for j in range(dst_frames):
        k_float = (j * factor) % src_frames
        k = int(k_float)
        k2 = (k + 1) % src_frames
        frac = k_float - k
        left = int(src_samples[k * 2] * (1.0 - frac) + src_samples[k2 * 2] * frac)
        right = int(src_samples[k * 2 + 1] * (1.0 - frac) + src_samples[k2 * 2 + 1] * frac)
        if pan == "right_only":
            dst_samples[j * 2] = 0
            dst_samples[j * 2 + 1] = (left + right) // 2
        elif pan == "left_only":
            dst_samples[j * 2] = (left + right) // 2
            dst_samples[j * 2 + 1] = 0
        else:
            dst_samples[j * 2] = left
            dst_samples[j * 2 + 1] = right


def Sound_play_working_chunk(working_chunk, channel: int = -1, loops: int = 0) -> int:
    if not sound_enabled or working_chunk is None:
        return -1
    chunk_ptr = ctypes.pointer(working_chunk)
    return Mix_PlayChannel(channel, chunk_ptr, loops)

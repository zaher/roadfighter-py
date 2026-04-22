"""Network protocol definitions for P2P multiplayer."""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class MessageType(IntEnum):
    """Message type identifiers."""
    INPUT = 0x01          # Player input state
    SYNC = 0x02           # Game state checksum for verification
    FULL_STATE = 0x03     # Full player state (for initial sync/recovery)
    PING = 0x04           # Latency measurement
    PONG = 0x05           # Ping response
    CHAT = 0x10           # Text message
    CONNECT = 0x20        # Connection request
    CONNECT_ACK = 0x21    # Connection accepted
    DISCONNECT = 0x22     # Disconnect notification
    PAUSE = 0x30          # Pause game request
    RESUME = 0x31         # Resume game


@dataclass
class PlayerInput:
    """Player input state for a single frame."""
    frame_number: int
    left: bool
    right: bool
    up: bool
    down: bool
    fire: bool
    
    def pack(self) -> bytes:
        """Pack input into bytes."""
        buttons = (
            (self.left << 0) |
            (self.right << 1) |
            (self.up << 2) |
            (self.down << 3) |
            (self.fire << 4)
        )
        return struct.pack('!IB', self.frame_number, buttons)
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional[PlayerInput]:
        """Unpack bytes into PlayerInput."""
        if len(data) < 5:
            return None
        frame_number, buttons = struct.unpack('!IB', data[:5])
        return cls(
            frame_number=frame_number,
            left=bool(buttons & 0x01),
            right=bool(buttons & 0x02),
            up=bool(buttons & 0x04),
            down=bool(buttons & 0x08),
            fire=bool(buttons & 0x10),
        )


@dataclass
class PingMessage:
    """Ping for latency measurement."""
    timestamp: float
    
    def pack(self) -> bytes:
        return struct.pack('!Bd', MessageType.PING, self.timestamp)
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional[PingMessage]:
        if len(data) < 9:
            return None
        msg_type, timestamp = struct.unpack('!Bd', data[:9])
        if msg_type != MessageType.PING:
            return None
        return cls(timestamp=timestamp)


@dataclass
class PongMessage:
    """Pong response with original timestamp."""
    original_timestamp: float
    server_timestamp: float
    
    def pack(self) -> bytes:
        return struct.pack('!Bdd', MessageType.PONG, self.original_timestamp, self.server_timestamp)
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional[PongMessage]:
        if len(data) < 17:
            return None
        msg_type, orig_ts, server_ts = struct.unpack('!Bdd', data[:17])
        if msg_type != MessageType.PONG:
            return None
        return cls(original_timestamp=orig_ts, server_timestamp=server_ts)


@dataclass
class PlayerState:
    """Full player state for synchronization."""
    frame_number: int
    x: float
    y: float
    x_speed: float
    y_speed: float
    fuel: int
    score: int
    state: int  # Player state machine state
    
    def pack(self) -> bytes:
        return struct.pack(
            '!Biff ffiiI',
            MessageType.FULL_STATE,
            self.frame_number,
            self.x, self.y,
            self.x_speed, self.y_speed,
            self.fuel, self.score,
            self.state
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional[PlayerState]:
        if len(data) < 29:
            return None
        msg_type = data[0]
        if msg_type != MessageType.FULL_STATE:
            return None
        return cls(
            frame_number=struct.unpack('!I', data[1:5])[0],
            x=struct.unpack('!f', data[5:9])[0],
            y=struct.unpack('!f', data[9:13])[0],
            x_speed=struct.unpack('!f', data[13:17])[0],
            y_speed=struct.unpack('!f', data[17:21])[0],
            fuel=struct.unpack('!i', data[21:25])[0],
            score=struct.unpack('!i', data[25:29])[0],
            state=struct.unpack('!I', data[29:33])[0] if len(data) >= 33 else 0,
        )


@dataclass
class SyncMessage:
    """Checksum for deterministic sync verification."""
    frame_number: int
    checksum: int
    
    def pack(self) -> bytes:
        return struct.pack('!BII', MessageType.SYNC, self.frame_number, self.checksum)
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional[SyncMessage]:
        if len(data) < 9:
            return None
        msg_type, frame, checksum = struct.unpack('!BII', data[:9])
        if msg_type != MessageType.SYNC:
            return None
        return cls(frame_number=frame, checksum=checksum)


@dataclass
class ConnectMessage:
    """Initial connection message."""
    version: int = 1
    player_name: str = "Player"
    
    def pack(self) -> bytes:
        name_bytes = self.player_name.encode('utf-8')[:32]
        return struct.pack('!BB', MessageType.CONNECT, self.version) + name_bytes
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional[ConnectMessage]:
        if len(data) < 2:
            return None
        msg_type, version = struct.unpack('!BB', data[:2])
        if msg_type != MessageType.CONNECT:
            return None
        name = data[2:].decode('utf-8', errors='ignore').strip('\x00')
        return cls(version=version, player_name=name)


@dataclass
class ConnectAckMessage:
    """Connection accepted response."""
    accepted: bool
    player_id: int  # 0 = host, 1 = client
    
    def pack(self) -> bytes:
        return struct.pack('!BBB', MessageType.CONNECT_ACK, int(self.accepted), self.player_id)
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional[ConnectAckMessage]:
        if len(data) < 3:
            return None
        msg_type, accepted, player_id = struct.unpack('!BBB', data[:3])
        if msg_type != MessageType.CONNECT_ACK:
            return None
        return cls(accepted=bool(accepted), player_id=player_id)


@dataclass
class DisconnectMessage:
    """Graceful disconnect notification."""
    reason: str = ""
    
    def pack(self) -> bytes:
        reason_bytes = self.reason.encode('utf-8')[:64]
        return struct.pack('!B', MessageType.DISCONNECT) + reason_bytes
    
    @classmethod
    def unpack(cls, data: bytes) -> Optional[DisconnectMessage]:
        if len(data) < 1:
            return None
        if data[0] != MessageType.DISCONNECT:
            return None
        reason = data[1:].decode('utf-8', errors='ignore').strip('\x00')
        return cls(reason=reason)


def parse_message(data: bytes) -> Optional[object]:
    """Parse a message from raw bytes."""
    if len(data) < 1:
        return None
    
    msg_type = data[0]
    
    parsers = {
        MessageType.INPUT: PlayerInput.unpack,
        MessageType.SYNC: SyncMessage.unpack,
        MessageType.FULL_STATE: PlayerState.unpack,
        MessageType.PING: PingMessage.unpack,
        MessageType.PONG: PongMessage.unpack,
        MessageType.CONNECT: ConnectMessage.unpack,
        MessageType.CONNECT_ACK: ConnectAckAckMessage.unpack,
        MessageType.DISCONNECT: DisconnectMessage.unpack,
    }
    
    parser = parsers.get(msg_type)
    if parser:
        return parser(data)
    
    return None

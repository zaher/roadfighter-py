"""P2P Network handler for multiplayer games."""

from __future__ import annotations

import socket
import struct
import threading
import time
from collections import deque
from typing import Callable, Optional, Tuple

from .protocol import (
    ConnectAckMessage,
    ConnectMessage,
    DisconnectMessage,
    MessageType,
    parse_message,
    PingMessage,
    PlayerInput,
    PlayerState,
    PongMessage,
    SyncMessage,
)


class NetworkStats:
    """Network connection statistics."""
    
    def __init__(self):
        self.packets_sent = 0
        self.packets_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0
        self.latency_ms = 0.0
        self.packets_lost = 0
        self.last_update_time = time.time()
        
    def update(self):
        """Update statistics (call periodically)."""
        now = time.time()
        self.last_update_time = now


class P2PNetwork:
    """Peer-to-peer network handler using UDP."""
    
    DEFAULT_PORT = 5555
    RECV_BUFFER_SIZE = 4096
    CONNECTION_TIMEOUT = 10.0  # Seconds before considering disconnected
    PING_INTERVAL = 1.0  # Send ping every second
    INPUT_SEND_INTERVAL = 1 / 60  # Send inputs at 60Hz
    
    def __init__(
        self,
        is_host: bool,
        host_ip: Optional[str] = None,
        port: int = DEFAULT_PORT,
        player_name: str = "Player"
    ):
        self.is_host = is_host
        self.port = port
        self.player_name = player_name
        self.remote_addr: Optional[Tuple[str, int]] = None
        
        # Socket setup
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)
        
        if is_host:
            self.socket.bind(('0.0.0.0', port))
            print(f"[NETWORK] Hosting on port {port}")
        else:
            if not host_ip:
                raise ValueError("Client mode requires host_ip")
            self.remote_addr = (host_ip, port)
            print(f"[NETWORK] Will connect to {host_ip}:{port}")
        
        # Connection state
        self.connected = False
        self.connecting = False
        self.connection_state = "idle"  # idle, connecting, connected, disconnected
        self.remote_player_name = ""
        self.remote_player_id = -1
        self.local_player_id = 0 if is_host else 1
        
        # Timing
        self.last_received_time = 0.0
        self.last_ping_time = 0.0
        self.last_input_send_time = 0.0
        self.connection_start_time = 0.0
        
        # Input buffering
        self.local_input_buffer: deque[Tuple[int, PlayerInput]] = deque(maxlen=120)
        self.remote_input_buffer: deque[Tuple[int, PlayerInput]] = deque(maxlen=120)
        self.current_frame = 0
        
        # Callbacks
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None
        self.on_input_received: Optional[Callable[[PlayerInput], None]] = None
        self.on_state_received: Optional[Callable[[PlayerState], None]] = None
        
        # Statistics
        self.stats = NetworkStats()
        
        # Background thread
        self.running = False
        self.receive_thread: Optional[threading.Thread] = None
        
    def start(self) -> bool:
        """Start the network handler."""
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        
        if not self.is_host:
            # Client initiates connection
            self._send_connect()
            self.connection_state = "connecting"
            self.connecting = True
            self.connection_start_time = time.time()
        
        return True
    
    def stop(self):
        """Stop the network handler."""
        if self.connected:
            self._send_disconnect("Game ended")
        
        self.running = False
        self.connected = False
        self.connection_state = "disconnected"
        
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1.0)
        
        try:
            self.socket.close()
        except:
            pass
    
    def update(self):
        """Call this every frame to handle network updates."""
        if not self.running:
            return
        
        now = time.time()
        
        # Check for timeout
        if self.connected and (now - self.last_received_time) > self.CONNECTION_TIMEOUT:
            print(f"[NETWORK] Connection timed out")
            self._handle_disconnect("Connection timed out")
            return
        
        # Check for connection timeout (when connecting)
        if self.connecting and (now - self.connection_start_time) > self.CONNECTION_TIMEOUT:
            print(f"[NETWORK] Connection attempt timed out")
            self.connection_state = "disconnected"
            self.connecting = False
            return
        
        # Send periodic ping
        if self.connected and (now - self.last_ping_time) > self.PING_INTERVAL:
            self._send_ping()
            self.last_ping_time = now
        
        self.current_frame += 1
    
    def send_input(self, input_state: PlayerInput):
        """Send local player input to remote peer."""
        if not self.connected:
            return
        
        now = time.time()
        if (now - self.last_input_send_time) < self.INPUT_SEND_INTERVAL:
            return  # Rate limit to avoid flooding
        
        input_state.frame_number = self.current_frame
        data = input_state.pack()
        self._send_raw(data)
        self.last_input_send_time = now
        
        # Store locally for reconciliation
        self.local_input_buffer.append((self.current_frame, input_state))
    
    def send_state(self, state: PlayerState):
        """Send full player state (for sync/recovery)."""
        if not self.connected:
            return
        state.frame_number = self.current_frame
        self._send_raw(state.pack())
    
    def send_sync(self, checksum: int):
        """Send sync checksum."""
        if not self.connected:
            return
        sync = SyncMessage(frame_number=self.current_frame, checksum=checksum)
        self._send_raw(sync.pack())
    
    def get_remote_input(self, frame: int) -> Optional[PlayerInput]:
        """Get remote player input for a specific frame."""
        for frm, inp in self.remote_input_buffer:
            if frm == frame:
                return inp
        return None
    
    def get_latest_remote_input(self) -> Optional[PlayerInput]:
        """Get the most recent remote player input."""
        if self.remote_input_buffer:
            return self.remote_input_buffer[-1][1]
        return None
    
    def is_peer_connected(self) -> bool:
        """Check if peer is connected."""
        return self.connected and self.remote_addr is not None
    
    def get_latency_ms(self) -> float:
        """Get current latency in milliseconds."""
        return self.stats.latency_ms
    
    def _receive_loop(self):
        """Background thread for receiving packets."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(self.RECV_BUFFER_SIZE)
                self.stats.packets_received += 1
                self.stats.bytes_received += len(data)
                self._handle_packet(data, addr)
            except BlockingIOError:
                time.sleep(0.001)  # Small sleep to prevent busy-wait
            except OSError:
                break  # Socket closed
            except Exception as e:
                print(f"[NETWORK] Receive error: {e}")
    
    def _handle_packet(self, data: bytes, addr: Tuple[str, int]):
        """Handle a received packet."""
        self.last_received_time = time.time()
        
        # Accept packets from any address (for initial connection)
        if not self.remote_addr:
            self.remote_addr = addr
        
        if len(data) < 1:
            return
        
        msg_type = data[0]
        
        # Handle connection messages
        if msg_type == MessageType.CONNECT:
            self._handle_connect(data, addr)
        elif msg_type == MessageType.CONNECT_ACK:
            self._handle_connect_ack(data)
        elif msg_type == MessageType.DISCONNECT:
            self._handle_disconnect_msg(data)
        elif self.connected:
            # Only process game messages if connected
            if msg_type == MessageType.INPUT:
                self._handle_input(data)
            elif msg_type == MessageType.FULL_STATE:
                self._handle_state(data)
            elif msg_type == MessageType.PING:
                self._handle_ping(data)
            elif msg_type == MessageType.PONG:
                self._handle_pong(data)
            elif msg_type == MessageType.SYNC:
                self._handle_sync(data)
    
    def _handle_connect(self, data: bytes, addr: Tuple[str, int]):
        """Handle incoming connection request."""
        msg = ConnectMessage.unpack(data)
        if msg:
            print(f"[NETWORK] Connection request from {addr[0]}:{addr[1]} - {msg.player_name}")
            self.remote_player_name = msg.player_name
            self.remote_addr = addr
            
            # Send acknowledgement
            ack = ConnectAckMessage(accepted=True, player_id=1)
            self._send_raw(ack.pack(), addr)
            
            self.connected = True
            self.connection_state = "connected"
            self.remote_player_id = 1
            print(f"[NETWORK] Connection established with {msg.player_name}")
            
            if self.on_connect:
                self.on_connect()
    
    def _handle_connect_ack(self, data: bytes):
        """Handle connection acknowledgement."""
        msg = ConnectAckMessage.unpack(data)
        if msg and msg.accepted:
            self.connected = True
            self.connecting = False
            self.connection_state = "connected"
            self.local_player_id = msg.player_id
            self.remote_player_id = 0 if msg.player_id == 1 else 1
            print(f"[NETWORK] Connected to host as player {self.local_player_id}")
            
            if self.on_connect:
                self.on_connect()
    
    def _handle_disconnect_msg(self, data: bytes):
        """Handle disconnect message."""
        msg = DisconnectMessage.unpack(data)
        reason = msg.reason if msg else "Unknown reason"
        print(f"[NETWORK] Peer disconnected: {reason}")
        self._handle_disconnect(reason)
    
    def _handle_input(self, data: bytes):
        """Handle player input message."""
        inp = PlayerInput.unpack(data)
        if inp:
            self.remote_input_buffer.append((inp.frame_number, inp))
            if self.on_input_received:
                self.on_input_received(inp)
    
    def _handle_state(self, data: bytes):
        """Handle full state message."""
        state = PlayerState.unpack(data)
        if state and self.on_state_received:
            self.on_state_received(state)
    
    def _handle_ping(self, data: bytes):
        """Handle ping message - respond with pong."""
        ping = PingMessage.unpack(data)
        if ping:
            pong = PongMessage(
                original_timestamp=ping.timestamp,
                server_timestamp=time.time()
            )
            self._send_raw(pong.pack())
    
    def _handle_pong(self, data: bytes):
        """Handle pong message - calculate latency."""
        pong = PongMessage.unpack(data)
        if pong:
            now = time.time()
            round_trip = now - pong.original_timestamp
            self.stats.latency_ms = (round_trip / 2) * 1000
    
    def _handle_sync(self, data: bytes):
        """Handle sync message."""
        sync = SyncMessage.unpack(data)
        # Could compare checksums here for desync detection
    
    def _handle_disconnect(self, reason: str):
        """Handle disconnection."""
        was_connected = self.connected
        self.connected = False
        self.connection_state = "disconnected"
        
        if was_connected and self.on_disconnect:
            self.on_disconnect(reason)
    
    def _send_connect(self):
        """Send connection request."""
        msg = ConnectMessage(version=1, player_name=self.player_name)
        self._send_raw(msg.pack())
    
    def _send_disconnect(self, reason: str = ""):
        """Send disconnect notification."""
        msg = DisconnectMessage(reason=reason)
        self._send_raw(msg.pack())
    
    def _send_ping(self):
        """Send ping message."""
        msg = PingMessage(timestamp=time.time())
        self._send_raw(msg.pack())
    
    def _send_raw(self, data: bytes, addr: Optional[Tuple[str, int]] = None):
        """Send raw data to remote peer."""
        target = addr or self.remote_addr
        if not target:
            return
        
        try:
            self.socket.sendto(data, target)
            self.stats.packets_sent += 1
            self.stats.bytes_sent += len(data)
        except Exception as e:
            print(f"[NETWORK] Send error: {e}")

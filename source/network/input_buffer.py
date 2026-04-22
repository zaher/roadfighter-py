"""Input buffer for network lag compensation."""

from __future__ import annotations

from collections import deque
from typing import Optional, Tuple

from .protocol import PlayerInput


class InputBuffer:
    """Buffers player inputs to handle network latency."""
    
    def __init__(self, buffer_size: int = 10, max_history: int = 120):
        """
        Initialize input buffer.
        
        Args:
            buffer_size: Number of frames to delay inputs (latency compensation)
            max_history: Maximum number of frames to keep in history
        """
        self.buffer_size = buffer_size
        self.max_history = max_history
        
        # Local input history
        self.local_inputs: deque[Tuple[int, PlayerInput]] = deque(maxlen=max_history)
        
        # Remote input buffer (received from network)
        self.remote_inputs: deque[Tuple[int, PlayerInput]] = deque(maxlen=max_history)
        
        # Predicted inputs for when real ones haven't arrived
        self.predicted_input: Optional[PlayerInput] = None
        
        # Current frame counter
        self.current_frame = 0
        
        # Statistics
        self.missed_inputs = 0
        self.total_requests = 0
    
    def add_local_input(self, frame: int, inp: PlayerInput):
        """Add local player input to history."""
        self.local_inputs.append((frame, inp))
        self.current_frame = max(self.current_frame, frame)
    
    def add_remote_input(self, frame: int, inp: PlayerInput):
        """Add received remote input."""
        self.remote_inputs.append((frame, inp))
    
    def get_remote_input(self, frame: int) -> Optional[PlayerInput]:
        """
        Get remote input for a specific frame.
        Applies delay buffer for smoother gameplay.
        """
        self.total_requests += 1
        
        # Look for input at frame - buffer_size (delayed)
        target_frame = frame - self.buffer_size
        
        # Search in received inputs
        for frm, inp in self.remote_inputs:
            if frm == target_frame:
                return inp
        
        # Input not found - use prediction
        self.missed_inputs += 1
        return self._predict_input(target_frame)
    
    def get_remote_input_nowait(self, frame: int) -> Optional[PlayerInput]:
        """Get remote input without waiting (no delay buffer)."""
        for frm, inp in self.remote_inputs:
            if frm == frame:
                return inp
        return None
    
    def _predict_input(self, frame: int) -> Optional[PlayerInput]:
        """Predict input when real input hasn't arrived."""
        # Simple prediction: repeat last known input
        if self.remote_inputs:
            last_input = self.remote_inputs[-1][1]
            # Create copy with new frame number
            return PlayerInput(
                frame_number=frame,
                left=last_input.left,
                right=last_input.right,
                up=last_input.up,
                down=last_input.down,
                fire=last_input.fire
            )
        
        # No history - return default (no input)
        if self.predicted_input is None:
            self.predicted_input = PlayerInput(
                frame_number=frame,
                left=False,
                right=False,
                up=False,
                down=False,
                fire=False
            )
        
        return self.predicted_input
    
    def get_latest_remote_frame(self) -> int:
        """Get the most recent frame number received from remote."""
        if self.remote_inputs:
            return max(frm for frm, _ in self.remote_inputs)
        return 0
    
    def get_input_delay(self) -> int:
        """Get the current delay between local and remote frames."""
        return self.current_frame - self.get_latest_remote_frame()
    
    def should_wait_for_input(self) -> bool:
        """Check if we should wait for remote input (for lockstep)."""
        delay = self.get_input_delay()
        # Wait if we're more than buffer_size frames ahead
        return delay > self.buffer_size + 5
    
    def get_stats(self) -> dict:
        """Get buffer statistics."""
        return {
            'miss_rate': self.missed_inputs / max(1, self.total_requests),
            'buffered_frames': len(self.remote_inputs),
            'input_delay': self.get_input_delay(),
            'buffer_size': self.buffer_size,
        }
    
    def clear(self):
        """Clear all buffered inputs."""
        self.local_inputs.clear()
        self.remote_inputs.clear()
        self.predicted_input = None
        self.current_frame = 0
        self.missed_inputs = 0
        self.total_requests = 0

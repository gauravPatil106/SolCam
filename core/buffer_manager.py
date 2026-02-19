"""
Buffer Manager Module
Maintains rolling pre-event buffer for recordings
"""
import time
import threading
from collections import deque
from typing import List, Tuple, Optional
import numpy as np
import config


class BufferManager:
    """
    Rolling buffer for pre-event recording
    
    Maintains a fixed-duration buffer of recent frames.
    When an event occurs, the buffer can be dumped to recording.
    """
    
    def __init__(self, buffer_seconds: int = None, fps: int = 30):
        """
        Initialize buffer manager
        
        Args:
            buffer_seconds: Duration of buffer in seconds
            fps: Expected frames per second (for buffer size calculation)
        """
        self.buffer_seconds = buffer_seconds or config.PRE_BUFFER_SECONDS
        self.fps = fps
        self.max_frames = self.buffer_seconds * self.fps
        
        # Use deque for efficient FIFO operations
        self.buffer = deque(maxlen=self.max_frames)
        self.lock = threading.Lock()
    
    def add_frame(self, frame: np.ndarray, timestamp: Optional[float] = None):
        """
        Add frame to buffer
        
        Args:
            frame: OpenCV image (BGR)
            timestamp: Frame timestamp (default: current time)
        """
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            # Store frame with timestamp
            self.buffer.append((frame.copy(), timestamp))
    
    def get_buffer(self) -> List[Tuple[np.ndarray, float]]:
        """
        Get all frames in buffer
        
        Returns:
            List of (frame, timestamp) tuples
        """
        with self.lock:
            return list(self.buffer)
    
    def clear(self):
        """Clear all frames from buffer"""
        with self.lock:
            self.buffer.clear()
    
    def get_buffer_size(self) -> int:
        """
        Get current number of frames in buffer
        
        Returns:
            Number of frames
        """
        with self.lock:
            return len(self.buffer)
    
    def get_buffer_duration(self) -> float:
        """
        Get actual duration of buffered content
        
        Returns:
            Duration in seconds
        """
        with self.lock:
            if len(self.buffer) < 2:
                return 0
            
            first_timestamp = self.buffer[0][1]
            last_timestamp = self.buffer[-1][1]
            return last_timestamp - first_timestamp
    
    def update_fps(self, fps: int):
        """
        Update FPS and recalculate buffer size
        
        Args:
            fps: New frames per second
        """
        with self.lock:
            self.fps = fps
            new_max_frames = self.buffer_seconds * self.fps
            
            # Create new deque with updated size
            old_buffer = list(self.buffer)
            self.buffer = deque(old_buffer, maxlen=new_max_frames)
            self.max_frames = new_max_frames

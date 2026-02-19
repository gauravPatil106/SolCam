"""
Recording Manager Module
Handles dual-quality video recording with automatic mode switching
"""
import cv2
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import numpy as np
import config


class RecordingManager:
    """
    Manages video recording with adaptive quality
    
    Features:
    - Dual quality modes (LOW/HIGH)
    - Automatic mode switching
    - File splitting every N minutes
    - Timestamp-based file naming
    """
    
    def __init__(self, camera_id: int):
        """
        Initialize recording manager
        
        Args:
            camera_id: Camera identifier
        """
        self.camera_id = camera_id
        self.current_mode = 'LOW'
        self.writer = None
        self.current_file_path = None
        self.recording_start_time = None
        self.frame_count = 0
        self.lock = threading.Lock()
        
        # Create recording directories
        self._create_directories()
    
    def _create_directories(self):
        """Create recording directories if they don't exist"""
        for mode in ['LOW', 'HIGH']:
            folder = config.BASE_DIR / config.RECORDING_SETTINGS[mode]['folder']
            folder.mkdir(parents=True, exist_ok=True)
    
    def start_recording(self, mode: str, frame_shape: Tuple[int, int]) -> Optional[str]:
        """
        Start recording in specified mode
        
        Args:
            mode: 'LOW' or 'HIGH'
            frame_shape: (height, width) of input frames
            
        Returns:
            Path to recording file, or None if failed
        """
        with self.lock:
            # Stop current recording if any
            self._stop_recording_internal()
            
            # Get settings for mode
            settings = config.RECORDING_SETTINGS[mode]
            resolution = settings['resolution']
            fps = settings['fps']
            codec = settings['codec']
            folder = config.BASE_DIR / settings['folder']
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"CAM{self.camera_id}_{timestamp}_{mode}.mp4"
            file_path = folder / filename
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*codec)
            writer = cv2.VideoWriter(str(file_path), fourcc, fps, resolution)
            
            if not writer.isOpened():
                print(f"Failed to create video writer: {file_path}")
                return None
            
            self.writer = writer
            self.current_file_path = str(file_path)
            self.current_mode = mode
            self.recording_start_time = time.time()
            self.frame_count = 0
            
            print(f"Started recording: {file_path}")
            return self.current_file_path
    
    def write_frame(self, frame: np.ndarray, mode: str) -> Optional[str]:
        """
        Write frame to recording
        
        Args:
            frame: OpenCV image (BGR)
            mode: Desired recording mode ('LOW' or 'HIGH')
            
        Returns:
            Current recording file path
        """
        with self.lock:
            # Check if mode changed or need to split file
            should_restart = False
            
            if self.writer is None:
                should_restart = True
            elif mode != self.current_mode:
                should_restart = True
            elif self._should_split_file():
                should_restart = True
            
            if should_restart:
                h, w = frame.shape[:2]
                self.start_recording(mode, (h, w))
            
            if self.writer is not None:
                # Resize frame to match recording resolution
                settings = config.RECORDING_SETTINGS[mode]
                resolution = settings['resolution']
                resized_frame = cv2.resize(frame, resolution)
                
                self.writer.write(resized_frame)
                self.frame_count += 1
            
            return self.current_file_path
    
    def write_buffer(self, buffer_frames: list, mode: str) -> Optional[str]:
        """
        Write buffered frames to recording
        
        Args:
            buffer_frames: List of (frame, timestamp) tuples
            mode: Recording mode for buffer
            
        Returns:
            Recording file path
        """
        if not buffer_frames:
            return self.current_file_path
        
        with self.lock:
            # Start new recording if needed
            if self.writer is None or mode != self.current_mode:
                first_frame = buffer_frames[0][0]
                h, w = first_frame.shape[:2]
                self.start_recording(mode, (h, w))
            
            # Write all buffered frames
            settings = config.RECORDING_SETTINGS[mode]
            resolution = settings['resolution']
            
            for frame, _ in buffer_frames:
                resized_frame = cv2.resize(frame, resolution)
                if self.writer is not None:
                    self.writer.write(resized_frame)
                    self.frame_count += 1
            
            return self.current_file_path
    
    def _should_split_file(self) -> bool:
        """
        Check if recording should be split
        
        Returns:
            True if should split, False otherwise
        """
        if self.recording_start_time is None:
            return False
        
        elapsed = time.time() - self.recording_start_time
        return elapsed >= config.RECORDING_SPLIT_DURATION
    
    def _stop_recording_internal(self):
        """Stop current recording (internal, assumes lock held)"""
        if self.writer is not None:
            self.writer.release()
            print(f"Stopped recording: {self.current_file_path} ({self.frame_count} frames)")
            self.writer = None
            self.current_file_path = None
            self.recording_start_time = None
            self.frame_count = 0
    
    def stop_recording(self):
        """Stop current recording"""
        with self.lock:
            self._stop_recording_internal()
    
    def get_current_file(self) -> Optional[str]:
        """
        Get current recording file path
        
        Returns:
            File path or None
        """
        with self.lock:
            return self.current_file_path
    
    def get_recording_duration(self) -> float:
        """
        Get duration of current recording
        
        Returns:
            Duration in seconds
        """
        with self.lock:
            if self.recording_start_time is None:
                return 0
            return time.time() - self.recording_start_time

"""
Decision Engine Module
Manages quality switching logic based on detections
"""
import time
import threading
from typing import Optional
import config


class DecisionEngine:
    """
    Decision engine for adaptive quality recording
    
    Logic:
    - Start in LOW quality mode
    - Switch to HIGH when important object detected
    - Stay in HIGH for N seconds after last detection
    - Return to LOW after timeout
    """
    
    # Quality modes
    LOW_QUALITY = 'LOW'
    HIGH_QUALITY = 'HIGH'
    
    def __init__(self, high_duration: int = None):
        """
        Initialize decision engine
        
        Args:
            high_duration: Seconds to stay in HIGH mode after detection
        """
        self.high_duration = high_duration or config.HIGH_QUALITY_DURATION
        self.current_mode = self.LOW_QUALITY
        self.last_detection_time = 0
        self.lock = threading.Lock()
    
    def process_detections(self, has_detection: bool) -> str:
        """
        Process detection result and determine recording quality
        
        Args:
            has_detection: True if important object detected in frame
            
        Returns:
            Current quality mode ('LOW' or 'HIGH')
        """
        with self.lock:
            current_time = time.time()
            
            if has_detection:
                # Detection occurred - switch to HIGH and reset timer
                self.last_detection_time = current_time
                self.current_mode = self.HIGH_QUALITY
            else:
                # No detection - check if we should return to LOW
                time_since_detection = current_time - self.last_detection_time
                
                if time_since_detection > self.high_duration:
                    self.current_mode = self.LOW_QUALITY
                # else: stay in HIGH mode (within timeout window)
            
            return self.current_mode
    
    def get_current_mode(self) -> str:
        """
        Get current quality mode without processing
        
        Returns:
            Current mode ('LOW' or 'HIGH')
        """
        with self.lock:
            return self.current_mode
    
    def force_mode(self, mode: str):
        """
        Force a specific quality mode (for testing)
        
        Args:
            mode: 'LOW' or 'HIGH'
        """
        with self.lock:
            if mode in [self.LOW_QUALITY, self.HIGH_QUALITY]:
                self.current_mode = mode
                if mode == self.HIGH_QUALITY:
                    self.last_detection_time = time.time()
    
    def reset(self):
        """Reset to initial state (LOW quality)"""
        with self.lock:
            self.current_mode = self.LOW_QUALITY
            self.last_detection_time = 0
    
    def get_time_remaining_in_high(self) -> float:
        """
        Get remaining time in HIGH quality mode
        
        Returns:
            Seconds remaining, or 0 if in LOW mode
        """
        with self.lock:
            if self.current_mode == self.LOW_QUALITY:
                return 0
            
            current_time = time.time()
            elapsed = current_time - self.last_detection_time
            remaining = max(0, self.high_duration - elapsed)
            return remaining

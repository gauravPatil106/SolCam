"""
Camera Manager Module
Handles camera capture with threading for non-blocking operation
"""
import cv2
import time
import threading
from typing import Optional, Tuple
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
import config
from utils.logger import get_logger
from core.onvif_client import ONVIFClient


class CameraManager(QThread):
    """
    Camera manager with threading support
    
    Extends QThread for non-blocking camera capture.
    Emits frames via PyQt signals for GUI update.
    """
    
    # Signals
    frame_ready = pyqtSignal(np.ndarray, int)  # (frame, camera_id)
    error_occurred = pyqtSignal(str, int)  # (error_message, camera_id)
    fps_updated = pyqtSignal(float, int)  # (fps, camera_id)
    
    def __init__(self, camera_id: int, source):
        """
        Initialize camera manager
        
        Args:
            camera_id: Camera identifier
            source: Camera source (int for webcam, str for RTSP)
        """
        super().__init__()
        
        self.camera_id = camera_id
        self.source = source
        self.capture = None
        self.running = False
        self.paused = False
        self.logger = get_logger()
        
        # FPS tracking
        self.fps = 0
        self.frame_count = 0
        self.fps_start_time = time.time()
        
        # Frame queue limit
        self.max_queue_size = 30
        self.frame_queue = []
        self.queue_lock = threading.Lock()
        
        self.logger.info(f"Camera {camera_id} initialized with source: {source}", component="CAMERA")
    
    def run(self):
        """Main thread loop (called by QThread.start())"""
        self.running = True
        self.logger.info(f"Starting camera {self.camera_id}", component="CAMERA")
        
        # Open camera
        if not self._open_camera():
            error_msg = f"Failed to open camera source: {self.source}"
            self.logger.error(error_msg, component="CAMERA")
            self.error_occurred.emit(error_msg, self.camera_id)
            return
        
        self.logger.info(f"Camera {self.camera_id} started successfully: {self.source}", component="CAMERA")
        print(f"Camera {self.camera_id} started: {self.source}")
        
        # Main capture loop
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue
            
            ret, frame = self.capture.read()
            
            if not ret:
                error_msg = f"Failed to read frame from camera {self.camera_id}"
                self.logger.warning(error_msg, component="CAMERA")
                self.error_occurred.emit(error_msg, self.camera_id)
                time.sleep(1)  # Wait before retry
                
                # Try to reconnect
                if not self._reconnect():
                    self.logger.error(f"Camera {self.camera_id} reconnection failed, stopping", component="CAMERA")
                    break
                continue
            
            # Emit frame signal
            self.frame_ready.emit(frame, self.camera_id)
            
            # Update FPS
            self._update_fps()
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.001)
        
        # Cleanup
        self._close_camera()
        self.logger.info(f"Camera {self.camera_id} stopped", component="CAMERA")
        print(f"Camera {self.camera_id} stopped")
    
    def _open_camera(self) -> bool:
        """
        Open camera source
        
        Returns:
            True if successful, False otherwise
        """
    def _open_camera(self) -> bool:
        """
        Open camera source
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check for ONVIF service URL
            if isinstance(self.source, str) and '/onvif/device_service' in self.source:
                self.logger.info(f"Resolving ONVIF URL: {self.source}", component="CAMERA")
                try:
                    # Parse simplified IP from URL if possible, or assume config has correct structure
                    # Ideally config should store just the RTSP URL, but if user pastes ONVIF URL:
                    # Extract IP/Port/Auth from URL if embedded? 
                    # Assuming basic format http://ip:port/onvif/device_service
                    # We might need default credentials 'admin:admin' if not provided
                    
                    # Simple regex to extract IP
                    import re
                    ip_match = re.search(r'//([^/:]+)', self.source)
                    if ip_match:
                        ip = ip_match.group(1)
                        # Try default admin/admin for now as fallback
                        client = ONVIFClient(ip, 80, "admin", "admin") 
                        # Note: Port might be different, parsing fully would be better but this is a quick fix
                        
                        media_url = client.get_media_service()
                        profiles = client.get_profiles()
                        if profiles:
                            rtsp_uri = client.get_stream_uri(profiles[0])
                            self.logger.info(f"Resolved to RTSP: {rtsp_uri}", component="CAMERA")
                            self.source = rtsp_uri # Update source to RTSP
                except Exception as e:
                    self.logger.warning(f"Failed to auto-resolve ONVIF URL: {e}", component="CAMERA")
            
            self.capture = cv2.VideoCapture(self.source)
            
            if not self.capture.isOpened():
                return False
            
            # Set buffer size to reduce latency
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Camera {self.camera_id} open error", component="CAMERA", exception=e)
            print(f"Camera open error: {e}")
            return False
    
    def _close_camera(self):
        """Close camera and release resources"""
        if self.capture is not None:
            self.capture.release()
            self.capture = None
    
    def _reconnect(self) -> bool:
        """
        Attempt to reconnect to camera
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.warning(f"Attempting to reconnect camera {self.camera_id}", component="CAMERA")
        print(f"Attempting to reconnect camera {self.camera_id}...")
        self._close_camera()
        time.sleep(2)
        success = self._open_camera()
        if success:
            self.logger.info(f"Camera {self.camera_id} reconnected successfully", component="CAMERA")
        else:
            self.logger.error(f"Camera {self.camera_id} reconnection failed", component="CAMERA")
        return success
    
    def _update_fps(self):
        """Update FPS calculation"""
        self.frame_count += 1
        
        # Calculate FPS every second
        elapsed = time.time() - self.fps_start_time
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.fps_updated.emit(self.fps, self.camera_id)
            
            # Reset counters
            self.frame_count = 0
            self.fps_start_time = time.time()
    
    def stop(self):
        """Stop camera capture"""
        self.running = False
        self.wait()  # Wait for thread to finish
    
    def pause(self):
        """Pause camera capture"""
        self.paused = True
    
    def resume(self):
        """Resume camera capture"""
        self.paused = False
    
    def get_fps(self) -> float:
        """
        Get current FPS
        
        Returns:
            Frames per second
        """
        return self.fps
    
    def get_frame_size(self) -> Optional[Tuple[int, int]]:
        """
        Get frame dimensions
        
        Returns:
            (width, height) or None if camera not open
        """
        if self.capture is None or not self.capture.isOpened():
            return None
        
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (width, height)

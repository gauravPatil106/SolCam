"""
Camera Card Widget - Individual camera feed display in grid
Shows live video with motion detection overlay
"""
import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont


class CameraCard(QWidget):
    """Widget displaying a single camera feed with motion detection overlay"""
    
    def __init__(self, camera_id: int, camera_name: str, parent=None):
        super().__init__(parent)
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.motion_detected = False
        self.current_frame = None
        
        self._init_ui()
        self._apply_style()
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Container frame
        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.Box)
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(4)
        
        # Header with camera name
        self.header = QLabel(self.camera_name)
        self.header.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.header.setFixedHeight(30)
        frame_layout.addWidget(self.header)
        
        # Video display label
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(400, 300)
        self.video_label.setScaledContents(False)
        self.video_label.setText("No Signal")
        frame_layout.addWidget(self.video_label)
        
        # Motion detected badge (initially hidden)
        self.motion_badge = QLabel("Motion Detected")
        self.motion_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.motion_badge.setFixedHeight(25)
        self.motion_badge.setVisible(False)
        frame_layout.addWidget(self.motion_badge)
        
        layout.addWidget(self.frame)
    
    def _apply_style(self):
        """Apply dark theme styling"""
        self.frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        
        self.header.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                background-color: #252525;
                padding: 5px 8px;
                border-radius: 3px;
            }
        """)
        
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #0a0a0a;
                color: #666;
                font-size: 12px;
                border: 1px solid #222;
            }
        """)
        
        self.motion_badge.setStyleSheet("""
            QLabel {
                background-color: #FFA500;
                color: #000000;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 10px;
                border-radius: 3px;
            }
        """)
    
    def update_frame(self, frame: np.ndarray, detections: list = None):
        """
        Update video frame with optional detection overlays
        
        Args:
            frame: OpenCV frame (BGR format)
            detections: List of detection dicts with 'bbox', 'class', 'confidence'
        """
        if frame is None:
            return
        
        self.current_frame = frame.copy()
        
        # Draw detection boxes if present
        if detections:
            for det in detections:
                bbox = det.get('bbox', [])
                class_name = det.get('class', 'object')
                confidence = det.get('confidence', 0.0)
                
                if len(bbox) == 4:
                    x1, y1, x2, y2 = map(int, bbox)
                    
                    # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 165, 0), 2)
                    
                    # Draw label background
                    label = f"{class_name} {confidence:.2f}"
                    (label_w, label_h), _ = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                    )
                    cv2.rectangle(
                        frame, (x1, y1 - label_h - 10), 
                        (x1 + label_w + 10, y1), (255, 165, 0), -1
                    )
                    
                    # Draw label text
                    cv2.putText(
                        frame, label, (x1 + 5, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1
                    )
        
        # Convert to QPixmap and display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Scale to fit label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)
    
    def set_motion_detected(self, detected: bool):
        """
        Show or hide motion detected badge
        
        Args:
            detected: True to show badge, False to hide
        """
        self.motion_detected = detected
        self.motion_badge.setVisible(detected)
    
    def clear_display(self):
        """Clear video display and show 'No Signal'"""
        self.video_label.clear()
        self.video_label.setText("No Signal")
        self.set_motion_detected(False)

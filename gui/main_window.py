"""
Main Window - Multi-Camera Security Dashboard
Professional surveillance dashboard with grid layout
"""
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QProgressBar, QMessageBox, QGridLayout,
    QFrame, QScrollArea, QDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont, QIcon
import numpy as np

import config
from core.camera_manager import CameraManager
from core.ai_detector import AIDetector
from core.decision_engine import DecisionEngine
from core.buffer_manager import BufferManager
from core.recording_manager import RecordingManager
from core.event_logger import EventLogger
from database.database_manager import get_database
from utils.helpers import (
    save_snapshot, play_alarm_sound, get_storage_usage, 
    cleanup_old_recordings, format_bytes
)
from gui.camera_card import CameraCard
from gui.event_log_widget import EventLogWidget
from gui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Main multi-camera surveillance dashboard"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("SECUREVISION - AI Monitoring System")
        self.resize(1600, 1000)
        
        # Core components
        self.cameras = {}  # camera_id -> CameraManager
        self.camera_cards = {}  # camera_id -> CameraCard
        self.ai_detectors = {}  # camera_id -> AIDetector
        self.decision_engines = {}  # camera_id -> DecisionEngine
        self.buffer_managers = {}  # camera_id -> BufferManager
        self.recording_managers = {}  # camera_id -> RecordingManager
        self.event_logger = EventLogger()
        self.database = get_database()
        
        # State
        self.ai_enabled = True
        self.frame_skip_counter = {}  # camera_id -> counter
        self.all_cameras_running = False
        
        # Timers
        self.storage_update_timer = QTimer()
        self.storage_update_timer.timeout.connect(self._update_storage_display)
        self.storage_update_timer.start(5000)  # Update every 5 seconds
        
        self._init_ui()
        self._apply_dark_theme()
    
    def _init_ui(self):
        """Initialize UI components"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left sidebar (compact navigation)
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Main content area
        content = self._create_content_area()
        main_layout.addWidget(content, stretch=1)
    
    def _create_sidebar(self) -> QWidget:
        """Create compact left sidebar"""
        sidebar = QFrame()
        sidebar.setFixedWidth(80)
        sidebar.setObjectName("sidebar")
        
        layout = QVBoxLayout()
        sidebar.setLayout(layout)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(15)
        
        # Logo/Title
        title = QLabel("📹\nSECURE\nVISION")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 10px; font-weight: bold; color: #00aaff; padding: 10px 0;")
        layout.addWidget(title)
        
        # Navigation buttons
        nav_buttons = [
            ("Live View", "🎥", None),
            ("Event Log", "📋", None),
            ("Playback", "⏯️", None),
            ("Analytics", "📊", None),
            ("Settings", "⚙️", self._on_open_settings)
        ]
        
        for name, icon, callback in nav_buttons:
            btn = QPushButton(f"{icon}\n{name}")
            btn.setFixedHeight(70)
            if callback:
                btn.clicked.connect(callback)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a1a1a;
                    color: #888;
                    border: none;
                    border-radius: 5px;
                    font-size: 9px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #2a2a2a;
                    color: #fff;
                }
            """)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        return sidebar
    
    def _create_content_area(self) -> QWidget:
        """Create main content area with camera grid and event log"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header with title and controls
        header = self._create_header()
        layout.addWidget(header)
        
        # Camera grid (70% height)
        grid_container = self._create_camera_grid()
        layout.addWidget(grid_container, stretch=7)
        
        # Event log (30% height)
        self.event_log = EventLogWidget()
        self.event_log.set_database_manager(self.database)
        self.event_log.export_btn.clicked.connect(self._on_export_events)
        layout.addWidget(self.event_log, stretch=3)
        
        return widget
    
    def _create_header(self) -> QWidget:
        """Create header with title and controls"""
        header = QFrame()
        header.setFixedHeight(60)
        header.setObjectName("header")
        
        layout = QHBoxLayout()
        header.setLayout(layout)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Title
        title = QLabel("Live Camera Feeds")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #fff;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Camera count
        self.camera_count_label = QLabel("Cameras: 0 Active")
        self.camera_count_label.setStyleSheet("color: #888; font-size: 12px; margin-right: 20px;")
        layout.addWidget(self.camera_count_label)
        
        # AI Alerts count
        self.alerts_label = QLabel("🔔 AI Alerts: 0")
        self.alerts_label.setStyleSheet("color: #888; font-size: 12px; margin-right: 20px;")
        layout.addWidget(self.alerts_label)
        
        # System status
        self.system_status = QLabel("● System: Secure")
        self.system_status.setStyleSheet("color: #4CAF50; font-size: 12px; margin-right: 20px;")
        layout.addWidget(self.system_status)
        
        # Storage
        self.storage_label = QLabel("+ 0%")
        self.storage_label.setStyleSheet("color: #4CAF50; font-size: 12px; margin-right: 10px;")
        layout.addWidget(self.storage_label)
        
        # Control buttons
        self.btn_start_all = QPushButton("Start All")
        self.btn_start_all.clicked.connect(self._on_start_all_cameras)
        layout.addWidget(self.btn_start_all)
        
        self.btn_stop_all = QPushButton("Stop All")
        self.btn_stop_all.clicked.connect(self._on_stop_all_cameras)
        layout.addWidget(self.btn_stop_all)
        
        return header
    
    def _create_camera_grid(self) -> QWidget:
        """Create camera grid layout"""
        container = QFrame()
        container.setObjectName("cameraGrid")
        
        layout = QGridLayout()
        container.setLayout(layout)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Check if any cameras are configured
        if not config.CAMERA_SOURCES:
            # Show helpful message when no cameras configured
            message = QLabel(
                "No Cameras Configured\n\n"
                "To add cameras, edit config.py and add entries to CAMERA_SOURCES:\n\n"
                "Examples:\n"
                "  0: \"Front Door Camera\"  (for webcam index 0)\n"
                "  1: \"Parking Lot\"  (for webcam index 1)\n"
                "  \"rtsp://user:pass@192.168.1.100/stream\": \"Warehouse\""
            )
            message.setAlignment(Qt.AlignmentFlag.AlignCenter)
            message.setStyleSheet("""
                QLabel {
                    color: #888;
                    font-size: 14px;
                    padding: 50px;
                    background-color: #1a1a1a;
                    border: 2px dashed #333;
                    border-radius: 10px;
                }
            """)
            layout.addWidget(message, 0, 0)
            return container
        
        # Create camera cards based on configured cameras
        rows, cols = config.CAMERA_GRID_LAYOUT
        camera_ids = list(config.CAMERA_SOURCES.keys())[:config.MAX_CAMERAS_DISPLAY]
        
        for idx, camera_id in enumerate(camera_ids):
            row = idx // cols
            col = idx % cols
            
            camera_name = config.CAMERA_SOURCES.get(camera_id, f"Camera {camera_id}")
            card = CameraCard(camera_id, camera_name)
            
            self.camera_cards[camera_id] = card
            layout.addWidget(card, row, col)
        
        # Fill empty grid cells if needed
        total_cells = rows * cols
        for idx in range(len(camera_ids), total_cells):
            row = idx // cols
            col = idx % cols
            placeholder = QLabel("No Camera")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("background-color: #0a0a0a; border: 1px solid #222; color: #444;")
            placeholder.setMinimumSize(400, 300)
            layout.addWidget(placeholder, row, col)
        
        return container
    
    def _apply_dark_theme(self):
        """Apply professional dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0d0d0d;
            }
            QWidget {
                background-color: #0d0d0d;
                color: #ffffff;
            }
            #sidebar {
                background-color: #1a1a1a;
                border-right: 1px solid #333;
            }
            #header {
                background-color: #1a1a1a;
                border-bottom: 1px solid #333;
            }
            #cameraGrid {
                background-color: #0d0d0d;
            }
            QPushButton {
                background-color: #2a4a6a;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a5a7a;
            }
            QPushButton:pressed {
                background-color: #1a3a5a;
            }
        """)
    
    @pyqtSlot()
    def _on_start_all_cameras(self):
        """Start all configured cameras"""
        if not config.CAMERA_SOURCES:
            QMessageBox.warning(
                self, 
                "No Cameras Configured",
                "Please add cameras to config.py first.\n\n"
                "Edit CAMERA_SOURCES in config.py:\n"
                "  0: \"Camera Name\"  (for webcam)\n"
                "  \"rtsp://...\": \"Camera Name\"  (for RTSP)"
            )
            return
        
        if self.all_cameras_running:
            QMessageBox.information(self, "Info", "Cameras already running")
            return
        
        camera_ids = list(config.CAMERA_SOURCES.keys())[:config.MAX_CAMERAS_DISPLAY]
        
        for camera_id in camera_ids:
            if camera_id not in self.cameras:
                self._start_camera(camera_id)
        
        self.all_cameras_running = True
        self._update_camera_count()
    
    @pyqtSlot()
    def _on_stop_all_cameras(self):
        """Stop all running cameras"""
        for camera_id in list(self.cameras.keys()):
            self._stop_camera(camera_id)
        
        self.all_cameras_running = False
        self._update_camera_count()
    
    def _start_camera(self, camera_id: int):
        """Start a specific camera"""
        if camera_id in self.cameras:
            return
        
        # Get camera source
        source = camera_id if isinstance(camera_id, int) else config.CAMERA_SOURCES.get(camera_id)
        
        # Create camera manager
        camera = CameraManager(camera_id, source)
        camera.frame_ready.connect(self._on_frame_received)
        camera.error_occurred.connect(self._on_camera_error)
        
        # Create AI detector
        ai_detector = AIDetector()
        
        # Create decision engine
        decision_engine = DecisionEngine()
        
        # Create buffer manager
        buffer_manager = BufferManager()
        
        # Create recording manager
        recording_manager = RecordingManager(camera_id)
        
        # Store references
        self.cameras[camera_id] = camera
        self.ai_detectors[camera_id] = ai_detector
        self.decision_engines[camera_id] = decision_engine
        self.buffer_managers[camera_id] = buffer_manager
        self.recording_managers[camera_id] = recording_manager
        self.frame_skip_counter[camera_id] = 0
        
        # Start camera
        camera.start()
        
        print(f"Started camera {camera_id}")
    
    def _stop_camera(self, camera_id: int):
        """Stop a specific camera"""
        if camera_id not in self.cameras:
            return
        
        # Stop camera
        self.cameras[camera_id].stop()
        
        # Stop recording
        self.recording_managers[camera_id].stop_recording()
        
        # Clear camera card display
        if camera_id in self.camera_cards:
            self.camera_cards[camera_id].clear_display()
        
        # Clean up references
        del self.cameras[camera_id]
        del self.ai_detectors[camera_id]
        del self.decision_engines[camera_id]
        del self.buffer_managers[camera_id]
        del self.recording_managers[camera_id]
        del self.frame_skip_counter[camera_id]
        
        print(f"Stopped camera {camera_id}")
    
    @pyqtSlot(np.ndarray, int)
    def _on_frame_received(self, frame: np.ndarray, camera_id: int):
        """Handle received frame from camera"""
        # Add to buffer
        buffer_manager = self.buffer_managers[camera_id]
        buffer_manager.add_frame(frame)
        
        # Process with AI (with frame skipping)
        detections = []
        detection_list = []
        if self.ai_enabled:
            self.frame_skip_counter[camera_id] += 1
            
            if self.frame_skip_counter[camera_id] >= config.AI_FRAME_SKIP:
                self.frame_skip_counter[camera_id] = 0
                
                ai_detector = self.ai_detectors[camera_id]
                detections = ai_detector.detect(frame)
                
                # Convert to dict format for camera card
                for obj_name, confidence, bbox in detections:
                    detection_list.append({
                        'class': obj_name,
                        'confidence': confidence,
                        'bbox': bbox
                    })
        
        # Update camera card
        if camera_id in self.camera_cards:
            self.camera_cards[camera_id].update_frame(frame, detection_list)
            self.camera_cards[camera_id].set_motion_detected(len(detections) > 0)
        
        # Decision engine
        decision_engine = self.decision_engines[camera_id]
        has_detection = len(detections) > 0
        current_mode = decision_engine.process_detections(has_detection)
        
        # Handle mode change
        recording_manager = self.recording_managers[camera_id]
        
        # If switching to HIGH mode with detection, write buffer first
        if has_detection and current_mode == 'HIGH':
            buffer_frames = buffer_manager.get_buffer()
            if buffer_frames:
                recording_manager.write_buffer(buffer_frames, 'HIGH')
        
        # Write current frame
        file_path = recording_manager.write_frame(frame, current_mode)
        
        # Log detections
        if detections:
            camera_name = config.CAMERA_SOURCES.get(camera_id, f"Camera {camera_id}")
            
            for obj_name, confidence, bbox in detections:
                self.event_logger.log_event(
                    camera_id, obj_name, confidence, current_mode, file_path or ""
                )
                
                # Add to event log widget
                self.event_log.add_event(
                    camera_name,
                    "Motion Detected",
                    f"{obj_name} detected ({confidence:.2f})"
                )
                
                # Save snapshot
                if config.ENABLE_SNAPSHOTS:
                    save_snapshot(frame, camera_id, obj_name, confidence)
                
                # Play alarm
                if config.ENABLE_SOUND_ALARM:
                    play_alarm_sound()
    
    @pyqtSlot(str, int)
    def _on_camera_error(self, error_msg: str, camera_id: int):
        """Handle camera error"""
        print(f"Camera {camera_id} error: {error_msg}")
        if camera_id in self.camera_cards:
            self.camera_cards[camera_id].clear_display()
    
    def _update_camera_count(self):
        """Update camera count display"""
        active_count = len(self.cameras)
        self.camera_count_label.setText(f"Cameras: {active_count} Active")
    
    @pyqtSlot()
    def _update_storage_display(self):
        """Update storage usage display"""
        storage = get_storage_usage()
        percent = int(storage['usage_percent'])
        
        self.storage_label.setText(f"+ {percent}%")
        
        # Color code based on usage
        if percent > 80:
            self.storage_label.setStyleSheet("color: #FF4444; font-size: 12px;")
        elif percent > 60:
            self.storage_label.setStyleSheet("color: #FFA500; font-size: 12px;")
        else:
            self.storage_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
        
        # Auto cleanup if needed
        if config.AUTO_CLEANUP_ENABLED and storage['total_gb'] > config.STORAGE_LIMIT_GB:
            cleanup_old_recordings()
    
    @pyqtSlot()
    def _on_export_events(self):
        """Export events to CSV"""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Events", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            success = self.event_logger.export_csv(Path(file_path))
            
            if success:
                QMessageBox.information(self, "Success", "Events exported successfully")
            else:
                QMessageBox.warning(self, "Error", "Failed to export events")
    
    @pyqtSlot()
    def _on_open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Settings were saved, reload cameras without restart
            self._reload_cameras()
            QMessageBox.information(
                self,
                "Settings Applied",
                "Camera settings have been applied successfully!\n\n"
                "Your cameras are now updated in the grid."
            )
    
    def _reload_cameras(self):
        """Reload camera grid with new configuration"""
        # Stop all running cameras
        for camera_id in list(self.cameras.keys()):
            self._stop_camera(camera_id)
        
        self.all_cameras_running = False
        
        # Reload config module
        import importlib
        importlib.reload(config)
        
        # Clear existing camera cards
        self.camera_cards.clear()
        
        # Rebuild camera grid
        # Find the camera grid container in the layout
        content_widget = self.centralWidget().layout().itemAt(1).widget()
        grid_container = content_widget.layout().itemAt(1).widget()
        
        # Remove old grid
        content_widget.layout().removeWidget(grid_container)
        grid_container.deleteLater()
        
        # Create new grid
        new_grid = self._create_camera_grid()
        content_widget.layout().insertWidget(1, new_grid, stretch=7)
        
        # Update camera count
        self._update_camera_count()
        
        print("Camera grid reloaded with new configuration")
    
    def closeEvent(self, event):
        """Handle window close"""
        # Stop all cameras
        for camera_id in list(self.cameras.keys()):
            self.cameras[camera_id].stop()
            self.recording_managers[camera_id].stop_recording()
        
        event.accept()

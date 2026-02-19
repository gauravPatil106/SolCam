"""
Settings Dialog - Camera Management
Add, remove, and configure cameras with IP detection
"""
import socket
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QComboBox, QGroupBox, QFormLayout, QTabWidget, QWidget,
    QSpinBox, QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import config
import json
from pathlib import Path
from core.onvif_client import ONVIFClient


class IPScanner(QThread):
    """Background thread for scanning network for cameras"""
    device_found = pyqtSignal(str, str)  # ip, device_type
    scan_complete = pyqtSignal()
    progress = pyqtSignal(int)
    
    def __init__(self, subnet="192.168.1"):
        super().__init__()
        self.subnet = subnet
        self.running = True
    
    def run(self):
        """Scan network for devices"""
        for i in range(1, 255):
            if not self.running:
                break
            
            ip = f"{self.subnet}.{i}"
            self.progress.emit(int((i / 254) * 100))
            
            # Try to connect to common camera ports
            if self._check_port(ip, 554):  # RTSP
                self.device_found.emit(ip, "RTSP Camera")
            elif self._check_port(ip, 80):  # HTTP
                self.device_found.emit(ip, "HTTP Camera")
        
        self.scan_complete.emit()
    
    def _check_port(self, ip, port, timeout=0.1):
        """Check if port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def stop(self):
        """Stop scanning"""
        self.running = False


class SettingsDialog(QDialog):
    """Settings dialog with camera management"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings - Camera Management")
        self.setMinimumSize(700, 500)
        self.setModal(True)
        
        self.cameras = self._load_cameras()
        self.scanner = None
        
        self._init_ui()
        self._apply_style()
    
    def _init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Camera Management Tab
        camera_tab = self._create_camera_tab()
        tabs.addTab(camera_tab, "📹 Cameras")
        
        # System Settings Tab
        system_tab = self._create_system_tab()
        tabs.addTab(system_tab, "⚙️ System")
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save & Apply")
        self.save_btn.clicked.connect(self._on_save)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def _create_camera_tab(self) -> QWidget:
        """Create camera management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # IP Scanner Section
        scanner_group = QGroupBox("Network Scanner")
        scanner_layout = QVBoxLayout()
        scanner_group.setLayout(scanner_layout)
        
        scan_controls = QHBoxLayout()
        
        scan_controls.addWidget(QLabel("Subnet:"))
        self.subnet_input = QLineEdit("192.168.1")
        self.subnet_input.setFixedWidth(100)
        scan_controls.addWidget(self.subnet_input)
        
        self.scan_btn = QPushButton("🔍 Scan Network")
        self.scan_btn.clicked.connect(self._on_scan_network)
        scan_controls.addWidget(self.scan_btn)
        
        scan_controls.addStretch()
        scanner_layout.addLayout(scan_controls)
        
        # Progress bar
        self.scan_progress = QProgressBar()
        self.scan_progress.setVisible(False)
        scanner_layout.addWidget(self.scan_progress)
        
        # Discovered devices
        scanner_layout.addWidget(QLabel("Discovered Devices:"))
        self.discovered_list = QListWidget()
        self.discovered_list.setMaximumHeight(100)
        self.discovered_list.itemDoubleClicked.connect(self._on_discovered_double_click)
        scanner_layout.addWidget(self.discovered_list)
        
        layout.addWidget(scanner_group)
        
        # Manual Add Section
        manual_group = QGroupBox("Add Camera Manually")
        manual_layout = QFormLayout()
        manual_group.setLayout(manual_layout)
        
        # Camera type
        self.camera_type = QComboBox()
        self.camera_type.addItems(["Webcam (USB)", "RTSP Stream", "HTTP Stream", "ONVIF Camera"])
        self.camera_type.currentTextChanged.connect(self._on_camera_type_changed)
        manual_layout.addRow("Camera Type:", self.camera_type)
        
        # Webcam index
        self.webcam_index = QSpinBox()
        self.webcam_index.setMinimum(0)
        self.webcam_index.setMaximum(10)
        self.webcam_index_row = manual_layout.rowCount()
        manual_layout.addRow("Webcam Index:", self.webcam_index)
        
        # ONVIF Fields
        self.onvif_group = QWidget()
        onvif_layout = QFormLayout()
        onvif_layout.setContentsMargins(0, 0, 0, 0)
        self.onvif_group.setLayout(onvif_layout)
        
        self.onvif_ip = QLineEdit()
        self.onvif_ip.setPlaceholderText("192.168.1.100")
        onvif_layout.addRow("IP Address:", self.onvif_ip)
        
        self.onvif_port = QSpinBox()
        self.onvif_port.setRange(1, 65535)
        self.onvif_port.setValue(80)
        onvif_layout.addRow("ONVIF Port:", self.onvif_port)
        
        self.onvif_user = QLineEdit("admin")
        onvif_layout.addRow("Username:", self.onvif_user)
        
        self.onvif_pass = QLineEdit("admin")
        self.onvif_pass.setEchoMode(QLineEdit.EchoMode.Password)
        onvif_layout.addRow("Password:", self.onvif_pass)
        
        self.detect_btn = QPushButton("🔍 Auto-Detect Stream")
        self.detect_btn.clicked.connect(self._on_detect_onvif)
        onvif_layout.addRow("", self.detect_btn)
        
        manual_layout.addRow(self.onvif_group)
        
        # RTSP URL
        self.rtsp_url = QLineEdit()
        self.rtsp_url.setPlaceholderText("rtsp://username:password@192.168.1.100:554/stream1")
        self.rtsp_url.setVisible(False)
        self.rtsp_url_label = QLabel("RTSP URL:")
        self.rtsp_url_label.setVisible(False)
        manual_layout.addRow(self.rtsp_url_label, self.rtsp_url)
        
        # Camera name
        self.camera_name = QLineEdit()
        self.camera_name.setPlaceholderText("e.g., Front Door, Parking Lot")
        manual_layout.addRow("Camera Name:", self.camera_name)
        
        # Test Connection & Add buttons
        btn_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("🔌 Test Connection")
        self.test_btn.clicked.connect(self._on_test_connection)
        self.test_btn.setStyleSheet("background-color: #4a4a4a;")
        btn_layout.addWidget(self.test_btn)
        
        btn_layout.addStretch()
        
        self.add_camera_btn = QPushButton("➕ Add Camera")
        self.add_camera_btn.clicked.connect(self._on_add_camera)
        btn_layout.addWidget(self.add_camera_btn)
        
        manual_layout.addRow("", btn_layout)
        
        layout.addWidget(manual_group)
        
        # Initial visibility
        self.onvif_group.setVisible(False)
        
        # Configured Cameras Section
        layout.addWidget(QLabel("Configured Cameras:"))
        
        self.camera_list = QListWidget()
        self._refresh_camera_list()
        layout.addWidget(self.camera_list)
        
        # Remove button
        remove_btn = QPushButton("🗑️ Remove Selected")
        remove_btn.clicked.connect(self._on_remove_camera)
        layout.addWidget(remove_btn)
        
        return widget

    def _on_test_connection(self):
        """Test connection to the specified camera"""
        camera_type = self.camera_type.currentText()
        
        if "Webcam" in camera_type:
            idx = self.webcam_index.value()
            source = idx
            type_str = f"Webcam {idx}"
        elif "RTSP" in camera_type:
            source = self.rtsp_url.text().strip()
            if not source:
                QMessageBox.warning(self, "Error", "Please enter RTSP URL")
                return
            type_str = "RTSP Stream"
        else:
            return

        self.test_btn.setText("⏳ Testing...")
        self.test_btn.setEnabled(False)
        QApplication.processEvents()
        
        # Test in background to avoid freezing
        import cv2
        try:
            cap = cv2.VideoCapture(source)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    QMessageBox.information(self, "Success", f"Successfully connected to {type_str}!")
                else:
                    QMessageBox.warning(self, "Failed", f"Connected to {type_str} but failed to read frame.\nCheck stream format.")
                cap.release()
            else:
                QMessageBox.warning(self, "Failed", 
                                   f"Could not connect to {type_str}.\n\n"
                                   "Possible causes:\n"
                                   "1. Wrong URL or IP\n"
                                   "2. Wrong Username/Password (401 Unauthorized)\n"
                                   "3. Camera offline\n"
                                   "4. Wrong RTSP format")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection error:\n{e}")
        finally:
            self.test_btn.setText("🔌 Test Connection")
            self.test_btn.setEnabled(True)

    
    def _create_system_tab(self) -> QWidget:
        """Create system settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        form = QFormLayout()
        
        # AI Confidence
        self.confidence_spin = QSpinBox()
        self.confidence_spin.setMinimum(30)
        self.confidence_spin.setMaximum(90)
        self.confidence_spin.setValue(int(config.AI_CONFIDENCE_THRESHOLD * 100))
        self.confidence_spin.setSuffix("%")
        form.addRow("AI Confidence Threshold:", self.confidence_spin)
        
        # Frame Skip
        self.frame_skip_spin = QSpinBox()
        self.frame_skip_spin.setMinimum(1)
        self.frame_skip_spin.setMaximum(10)
        self.frame_skip_spin.setValue(config.AI_FRAME_SKIP)
        form.addRow("AI Frame Skip:", self.frame_skip_spin)
        
        # Storage Limit
        self.storage_limit_spin = QSpinBox()
        self.storage_limit_spin.setMinimum(1)
        self.storage_limit_spin.setMaximum(100)
        self.storage_limit_spin.setValue(config.STORAGE_LIMIT_GB)
        self.storage_limit_spin.setSuffix(" GB")
        form.addRow("Storage Limit:", self.storage_limit_spin)
        
        layout.addLayout(form)
        layout.addStretch()
        
        return widget
    
    def _apply_style(self):
        """Apply dark theme"""
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #333;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QSpinBox, QComboBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444;
                padding: 5px;
                border-radius: 3px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #00aaff;
            }
            QPushButton {
                background-color: #2a4a6a;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a5a7a;
            }
            QListWidget {
                background-color: #0a0a0a;
                border: 1px solid #333;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #333;
                background-color: #1a1a1a;
            }
            QTabBar::tab {
                background-color: #2a2a2a;
                color: #888;
                padding: 8px 15px;
                border: 1px solid #333;
            }
            QTabBar::tab:selected {
                background-color: #1a1a1a;
                color: #00aaff;
                border-bottom: 2px solid #00aaff;
            }
        """)
    
    def _load_cameras(self) -> dict:
        """Load cameras from config"""
        return dict(config.CAMERA_SOURCES)
    
    def _refresh_camera_list(self):
        """Refresh the configured cameras list"""
        self.camera_list.clear()
        for camera_id, camera_name in self.cameras.items():
            item_text = f"{camera_name} ({camera_id})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, camera_id)
            self.camera_list.addItem(item)
    
    def _on_camera_type_changed(self, camera_type: str):
        """Handle camera type change"""
        is_webcam = "Webcam" in camera_type
        is_rtsp = "RTSP" in camera_type or "HTTP" in camera_type
        is_onvif = "ONVIF" in camera_type
        
        # Show/hide appropriate fields
        self.webcam_index.setVisible(is_webcam)
        self.rtsp_url.setVisible(is_rtsp)
        self.rtsp_url_label.setVisible(is_rtsp)
        self.onvif_group.setVisible(is_onvif)
        
        # If ONVIF, we'll eventually fill RTSP URL
        if is_onvif:
            self.rtsp_url.setVisible(True)
            self.rtsp_url_label.setVisible(True)
            self.rtsp_url.setPlaceholderText("Stream URL will appear here after detection...")
    
    def _on_scan_network(self):
        """Start network scan"""
        if self.scanner and self.scanner.isRunning():
            self.scanner.stop()
            self.scanner.wait()
            self.scan_btn.setText("🔍 Scan Network")
            self.scan_progress.setVisible(False)
            return
        
        self.discovered_list.clear()
        self.scan_progress.setVisible(True)
        self.scan_progress.setValue(0)
        self.scan_btn.setText("⏹️ Stop Scan")
        
        subnet = self.subnet_input.text()
        self.scanner = IPScanner(subnet)
        self.scanner.device_found.connect(self._on_device_found)
        self.scanner.scan_complete.connect(self._on_scan_complete)
        self.scanner.progress.connect(self.scan_progress.setValue)
        self.scanner.start()
    
    def _on_device_found(self, ip: str, device_type: str):
        """Handle discovered device"""
        item = QListWidgetItem(f"{ip} - {device_type}")
        item.setData(Qt.ItemDataRole.UserRole, ip)
        self.discovered_list.addItem(item)
    
    def _on_scan_complete(self):
        """Handle scan completion"""
        self.scan_btn.setText("🔍 Scan Network")
        self.scan_progress.setVisible(False)
        QMessageBox.information(self, "Scan Complete", 
                               f"Found {self.discovered_list.count()} devices")
    
    def _on_detect_onvif(self):
        """Auto-detect ONVIF stream"""
        ip = self.onvif_ip.text().strip()
        port = self.onvif_port.value()
        user = self.onvif_user.text().strip()
        password = self.onvif_pass.text().strip()
        
        if not ip:
            QMessageBox.warning(self, "Error", "Please enter IP address")
            return
            
        self.detect_btn.setText("⏳ Detecting...")
        self.detect_btn.setEnabled(False)
        QApplication.processEvents()
        
        try:
            client = ONVIFClient(ip, port, user, password)
            
            # 1. Get Media Service
            media_url = client.get_media_service()
            
            # 2. Get Profiles
            profiles = client.get_profiles()
            if not profiles:
                raise Exception("No media profiles found on device")
                
            # 3. Get Stream URI
            uri = client.get_stream_uri(profiles[0])
            
            self.rtsp_url.setText(uri)
            QMessageBox.information(self, "Success", 
                                  f"Found Stream URL!\n\n{uri}\n\n"
                                  "You can now test the connection or add the camera.")
                                  
        except Exception as e:
            QMessageBox.critical(self, "Detection Failed", 
                               f"Could not get stream URL:\n{str(e)}\n\n"
                               "Check IP, Port, and Credentials.")
        finally:
            self.detect_btn.setText("🔍 Auto-Detect Stream")
            self.detect_btn.setEnabled(True)

    def _on_discovered_double_click(self, item):
        """Auto-fill from discovered device"""
        ip = item.data(Qt.ItemDataRole.UserRole)
        self.camera_type.setCurrentText("ONVIF Camera")
        self.onvif_ip.setText(ip)
        self.rtsp_url.clear()
        self.camera_name.setText(f"Camera {ip}")
    
    def _on_add_camera(self):
        """Add a new camera"""
        camera_type = self.camera_type.currentText()
        name = self.camera_name.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a camera name")
            return
        
        if "Webcam" in camera_type:
            camera_id = self.webcam_index.value()
        elif "RTSP" in camera_type or "HTTP" in camera_type or "ONVIF" in camera_type:
            camera_id = self.rtsp_url.text().strip()
            if not camera_id:
                QMessageBox.warning(self, "Error", "Please enter Stream URL (or use Auto-Detect for ONVIF)")
                return
        else:
            QMessageBox.warning(self, "Error", "Unsupported camera type")
            return
        
        # Check if already exists
        if camera_id in self.cameras:
            QMessageBox.warning(self, "Error", "Camera already exists")
            return
        
        # Add camera
        self.cameras[camera_id] = name
        self._refresh_camera_list()
        
        # Clear inputs
        self.camera_name.clear()
        self.rtsp_url.clear()
        self.onvif_ip.clear()
        
        QMessageBox.information(self, "Success", f"Added camera: {name}")
    
    def _on_remove_camera(self):
        """Remove selected camera"""
        current_item = self.camera_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a camera to remove")
            return
        
        camera_id = current_item.data(Qt.ItemDataRole.UserRole)
        camera_name = self.cameras[camera_id]
        
        reply = QMessageBox.question(
            self, "Confirm Remove",
            f"Remove camera '{camera_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.cameras[camera_id]
            self._refresh_camera_list()
    
    def _on_save(self):
        """Save settings to config file"""
        try:
            # Update config.py
            config_path = Path(__file__).parent.parent / "config.py"
            
            with open(config_path, 'r') as f:
                lines = f.readlines()
            
            # Find and replace CAMERA_SOURCES
            in_camera_sources = False
            new_lines = []
            
            for line in lines:
                if 'CAMERA_SOURCES = {' in line:
                    in_camera_sources = True
                    new_lines.append('CAMERA_SOURCES = {\n')
                    for cam_id, cam_name in self.cameras.items():
                        if isinstance(cam_id, int):
                            new_lines.append(f'    {cam_id}: "{cam_name}",\n')
                        else:
                            new_lines.append(f'    "{cam_id}": "{cam_name}",\n')
                    new_lines.append('}\n')
                elif in_camera_sources and '}' in line:
                    in_camera_sources = False
                    continue
                elif not in_camera_sources:
                    new_lines.append(line)
            
            # Write back
            with open(config_path, 'w') as f:
                f.writelines(new_lines)
            
            # Reload config module
            import importlib
            importlib.reload(config)
            
            QMessageBox.information(self, "Success", 
                                   "Settings saved! Please restart the application for changes to take effect.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{e}")
    
    def get_cameras(self) -> dict:
        """Get configured cameras"""
        return self.cameras

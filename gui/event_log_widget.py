"""
Event Log Widget - Table display for surveillance events
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QLabel, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from datetime import datetime


class EventLogWidget(QWidget):
    """Widget displaying event log table"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = None
        self._init_ui()
        self._apply_style()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_events)
        self.refresh_timer.start(2000)  # Refresh every 2 seconds
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Event Log")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #fff;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        # Export button
        self.export_btn = QPushButton("Export CSV")
        self.export_btn.setFixedWidth(100)
        header_layout.addWidget(self.export_btn)
        
        layout.addLayout(header_layout)
        
        # Event table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Time", "Camera", "Event", "Details"])
        
        # Configure table
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table)
    
    def _apply_style(self):
        """Apply dark theme styling"""
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                gridline-color: #333;
                border: 1px solid #333;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #2a4a6a;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #333;
                font-weight: bold;
            }
        """)
        
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a4a6a;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3a5a7a;
            }
            QPushButton:pressed {
                background-color: #1a3a5a;
            }
        """)
    
    def set_database_manager(self, db_manager):
        """Set database manager for fetching events"""
        self.db_manager = db_manager
        self.refresh_events()
    
    def refresh_events(self):
        """Refresh event log from database"""
        if not self.db_manager:
            return
        
        try:
            # Get recent events (last 50)
            events = self.db_manager.get_recent_events(limit=50)
            
            # Clear table
            self.table.setRowCount(0)
            
            # Populate table
            for event in events:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Format timestamp
                timestamp = event.get('timestamp', '')
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%I:%M %p")
                except:
                    time_str = timestamp
                
                # Time
                time_item = QTableWidgetItem(time_str)
                time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, time_item)
                
                # Camera
                camera_name = event.get('camera_name', f"Camera {event.get('camera_id', 'N/A')}")
                camera_item = QTableWidgetItem(camera_name)
                camera_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 1, camera_item)
                
                # Event type
                event_type = event.get('event_type', 'Unknown')
                event_item = QTableWidgetItem(event_type)
                event_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Color code based on event type
                if 'fire' in event_type.lower() or 'intruder' in event_type.lower():
                    event_item.setForeground(QColor('#FF4444'))
                elif 'vehicle' in event_type.lower() or 'motion' in event_type.lower():
                    event_item.setForeground(QColor('#FFA500'))
                else:
                    event_item.setForeground(QColor('#4CAF50'))
                
                self.table.setItem(row, 2, event_item)
                
                # Details
                details = event.get('details', '')
                details_item = QTableWidgetItem(details)
                self.table.setItem(row, 3, details_item)
                
        except Exception as e:
            print(f"Error refreshing events: {e}")
    
    def add_event(self, camera_name: str, event_type: str, details: str):
        """
        Add a new event to the table (for real-time updates)
        
        Args:
            camera_name: Name of the camera
            event_type: Type of event
            details: Event details
        """
        row = 0
        self.table.insertRow(row)
        
        # Time
        time_str = datetime.now().strftime("%I:%M %p")
        time_item = QTableWidgetItem(time_str)
        time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 0, time_item)
        
        # Camera
        camera_item = QTableWidgetItem(camera_name)
        camera_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 1, camera_item)
        
        # Event
        event_item = QTableWidgetItem(event_type)
        event_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Color code
        if 'fire' in event_type.lower() or 'intruder' in event_type.lower():
            event_item.setForeground(QColor('#FF4444'))
        elif 'vehicle' in event_type.lower() or 'motion' in event_type.lower():
            event_item.setForeground(QColor('#FFA500'))
        else:
            event_item.setForeground(QColor('#4CAF50'))
        
        self.table.setItem(row, 2, event_item)
        
        # Details
        details_item = QTableWidgetItem(details)
        self.table.setItem(row, 3, details_item)
        
        # Limit table to 50 rows
        if self.table.rowCount() > 50:
            self.table.removeRow(50)

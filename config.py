"""
Configuration settings for AI-Based Intelligent Video Surveillance System
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Camera Configuration
# Add your cameras here (webcam index or RTSP URL)
CAMERA_SOURCES = {
    "http://192.168.0.254/onvif/device_service": "cctv",
}

# AI Detection Configuration
AI_CONFIDENCE_THRESHOLD = 0.5  # Default confidence threshold (0.0 - 1.0)
IMPORTANT_CLASSES = ['person', 'car', 'truck', 'motorcycle']  # Objects to detect
AI_FRAME_SKIP = 3  # Process every Nth frame (1 = every frame, 3 = every 3rd frame)
SIMULATE_DETECTION = False  # Set to True for testing without actual AI

# Recording Configuration
RECORDING_SETTINGS = {
    'LOW': {
        'resolution': (640, 480),
        'fps': 20,
        'codec': 'mp4v',  # Fallback codec
        'folder': 'recordings/low'
    },
    'HIGH': {
        'resolution': (1280, 720),
        'fps': 30,
        'codec': 'mp4v',
        'folder': 'recordings/high'
    }
}

# Try to use H.264 codec if available
try:
    import cv2
    # Test if H.264 is available
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    RECORDING_SETTINGS['LOW']['codec'] = 'avc1'
    RECORDING_SETTINGS['HIGH']['codec'] = 'avc1'
except:
    pass

# Decision Engine Configuration
HIGH_QUALITY_DURATION = 5  # Seconds to stay in HIGH mode after last detection
RECORDING_SPLIT_DURATION = 300  # Split recordings every 5 minutes (300 seconds)

# Buffer Configuration
PRE_BUFFER_SECONDS = 5  # Seconds of pre-event buffer

# Storage Configuration
STORAGE_LIMIT_GB = 5  # Auto-delete old files when storage exceeds this limit
AUTO_CLEANUP_ENABLED = True

# Database Configuration
DATABASE_PATH = BASE_DIR / 'surveillance.db'

# Logging Configuration
LOG_DIR = BASE_DIR / 'logs'
CSV_LOG_PATH = LOG_DIR / 'events.csv'

# Model Configuration
MODEL_DIR = BASE_DIR / 'models'
YOLO_MODEL_PATH = MODEL_DIR / 'yolov8n.pt'

# GUI Configuration
WINDOW_TITLE = "AI-Based Intelligent Video Surveillance System"
WINDOW_SIZE = (1400, 900)
THEME_DARK = True

# Security Configuration
LOGIN_CREDENTIALS = {
    'admin': 'admin'  # username: password
}
SESSION_TIMEOUT_MINUTES = 10

# Alert Configuration
ENABLE_SOUND_ALARM = True
ALARM_SOUND_PATH = BASE_DIR / 'assets' / 'alarm.wav'
ENABLE_EMAIL_ALERTS = False  # Set to True to enable email alerts
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'your_email@gmail.com',
    'sender_password': 'your_app_password',
    'recipient_email': 'recipient@gmail.com'
}

# Snapshot Configuration
ENABLE_SNAPSHOTS = True
SNAPSHOT_DIR = BASE_DIR / 'snapshots'

# Multi-Camera Display Configuration
CAMERA_GRID_LAYOUT = (2, 3)  # rows x columns (2 rows, 3 columns = 6 cameras)
MAX_CAMERAS_DISPLAY = 6
CAMERA_CARD_MIN_SIZE = (400, 300)
MOTION_DETECTED_COLOR = '#FFA500'  # Orange for motion detected badge

# Create necessary directories
def create_directories():
    """Create all necessary directories if they don't exist"""
    directories = [
        BASE_DIR / 'recordings' / 'low',
        BASE_DIR / 'recordings' / 'high',
        LOG_DIR,
        MODEL_DIR,
        SNAPSHOT_DIR,
        BASE_DIR / 'assets'
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# Auto-create directories on import
create_directories()

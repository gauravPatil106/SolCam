"""
Helper Utilities Module
Additional features: snapshots, alerts, storage management
"""
import os
import smtplib
import winsound
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import cv2
import numpy as np
import config


def save_snapshot(frame: np.ndarray, camera_id: int, 
                 object_name: str, confidence: float) -> Optional[str]:
    """
    Save snapshot when detection occurs
    
    Args:
        frame: OpenCV image
        camera_id: Camera identifier
        object_name: Detected object
        confidence: Detection confidence
        
    Returns:
        Path to saved snapshot, or None if failed
    """
    try:
        if not config.ENABLE_SNAPSHOTS:
            return None
        
        # Create filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"CAM{camera_id}_{timestamp}_{object_name}_{confidence:.2f}.jpg"
        filepath = config.SNAPSHOT_DIR / filename
        
        # Save image
        cv2.imwrite(str(filepath), frame)
        return str(filepath)
        
    except Exception as e:
        print(f"Snapshot save error: {e}")
        return None


def send_email_alert(camera_id: int, object_name: str, 
                    confidence: float, snapshot_path: Optional[str] = None) -> bool:
    """
    Send email alert for detection (SMTP placeholder)
    
    Args:
        camera_id: Camera identifier
        object_name: Detected object
        confidence: Detection confidence
        snapshot_path: Path to snapshot image (optional)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not config.ENABLE_EMAIL_ALERTS:
            return False
        
        # Email configuration
        smtp_server = config.EMAIL_CONFIG['smtp_server']
        smtp_port = config.EMAIL_CONFIG['smtp_port']
        sender_email = config.EMAIL_CONFIG['sender_email']
        sender_password = config.EMAIL_CONFIG['sender_password']
        recipient_email = config.EMAIL_CONFIG['recipient_email']
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Surveillance Alert: {object_name} detected"
        
        # Email body
        body = f"""
        Detection Alert
        
        Camera ID: {camera_id}
        Object: {object_name}
        Confidence: {confidence:.2%}
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Snapshot: {snapshot_path or 'Not available'}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print(f"Email alert sent for {object_name} detection")
        return True
        
    except Exception as e:
        print(f"Email alert error: {e}")
        return False


def play_alarm_sound() -> bool:
    """
    Play alarm sound on detection
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not config.ENABLE_SOUND_ALARM:
            return False
        
        # Check if alarm file exists
        if not config.ALARM_SOUND_PATH.exists():
            # Use system beep as fallback
            winsound.Beep(1000, 200)  # 1000 Hz for 200ms
            return True
        
        # Play WAV file
        winsound.PlaySound(str(config.ALARM_SOUND_PATH), 
                          winsound.SND_FILENAME | winsound.SND_ASYNC)
        return True
        
    except Exception as e:
        print(f"Alarm sound error: {e}")
        return False


def get_directory_size(path: Path) -> int:
    """
    Calculate total size of directory
    
    Args:
        path: Directory path
        
    Returns:
        Size in bytes
    """
    total_size = 0
    
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        print(f"Directory size calculation error: {e}")
    
    return total_size


def get_storage_usage() -> dict:
    """
    Get storage usage for recordings
    
    Returns:
        Dictionary with storage info
    """
    recordings_dir = config.BASE_DIR / 'recordings'
    
    low_size = get_directory_size(recordings_dir / 'low')
    high_size = get_directory_size(recordings_dir / 'high')
    total_size = low_size + high_size
    
    # Convert to GB
    low_gb = low_size / (1024 ** 3)
    high_gb = high_size / (1024 ** 3)
    total_gb = total_size / (1024 ** 3)
    
    return {
        'low_bytes': low_size,
        'high_bytes': high_size,
        'total_bytes': total_size,
        'low_gb': low_gb,
        'high_gb': high_gb,
        'total_gb': total_gb,
        'limit_gb': config.STORAGE_LIMIT_GB,
        'usage_percent': (total_gb / config.STORAGE_LIMIT_GB) * 100 if config.STORAGE_LIMIT_GB > 0 else 0
    }


def cleanup_old_recordings() -> int:
    """
    Delete old recordings when storage exceeds limit
    
    Returns:
        Number of files deleted
    """
    if not config.AUTO_CLEANUP_ENABLED:
        return 0
    
    storage = get_storage_usage()
    
    if storage['total_gb'] <= config.STORAGE_LIMIT_GB:
        return 0  # No cleanup needed
    
    print(f"Storage limit exceeded: {storage['total_gb']:.2f} GB / {config.STORAGE_LIMIT_GB} GB")
    print("Cleaning up old recordings...")
    
    deleted_count = 0
    recordings_dir = config.BASE_DIR / 'recordings'
    
    # Get all recording files with timestamps
    files = []
    for mode in ['low', 'high']:
        mode_dir = recordings_dir / mode
        if mode_dir.exists():
            for file in mode_dir.glob('*.mp4'):
                files.append((file, file.stat().st_mtime))
    
    # Sort by modification time (oldest first)
    files.sort(key=lambda x: x[1])
    
    # Delete oldest files until under limit
    for filepath, _ in files:
        try:
            file_size = filepath.stat().st_size
            filepath.unlink()
            deleted_count += 1
            
            # Recalculate storage
            storage = get_storage_usage()
            if storage['total_gb'] <= config.STORAGE_LIMIT_GB * 0.9:  # 90% threshold
                break
                
        except Exception as e:
            print(f"Error deleting file {filepath}: {e}")
    
    print(f"Deleted {deleted_count} old recordings")
    return deleted_count


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes to human-readable string
    
    Args:
        bytes_value: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "1h 23m 45s")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

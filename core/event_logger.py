"""
Event Logger Module
Logs detection events to CSV and SQLite database
"""
import csv
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
import config
from database.database_manager import get_database


class EventLogger:
    """
    Dual logging system for detection events
    
    Logs to:
    - CSV file (for easy export)
    - SQLite database (for queries and GUI display)
    """
    
    def __init__(self, csv_path: Optional[Path] = None):
        """
        Initialize event logger
        
        Args:
            csv_path: Path to CSV log file (default: from config)
        """
        self.csv_path = csv_path or config.CSV_LOG_PATH
        self.db = get_database()
        self.lock = threading.Lock()
        
        # Create CSV file with headers if it doesn't exist
        self._initialize_csv()
    
    def _initialize_csv(self):
        """Create CSV file with headers if it doesn't exist"""
        if not self.csv_path.exists():
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Camera ID', 'Object', 
                               'Confidence', 'Recording Mode', 'File Path'])
    
    def log_event(self, camera_id: int, object_name: str, 
                 confidence: float, recording_mode: str, 
                 file_path: str) -> bool:
        """
        Log detection event to both CSV and database
        
        Args:
            camera_id: Camera identifier
            object_name: Detected object class
            confidence: Detection confidence (0.0 - 1.0)
            recording_mode: 'LOW' or 'HIGH'
            file_path: Path to recording file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.lock:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Log to CSV
                with open(self.csv_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, camera_id, object_name, 
                                   f"{confidence:.2f}", recording_mode, file_path])
                
                # Log to database
                self.db.insert_event(camera_id, object_name, confidence, 
                                   recording_mode, file_path)
                
                return True
                
        except Exception as e:
            print(f"Event logging error: {e}")
            return False
    
    def export_csv(self, output_path: Path, camera_id: Optional[int] = None,
                  object_filter: Optional[str] = None) -> bool:
        """
        Export filtered events to CSV
        
        Args:
            output_path: Path for exported CSV
            camera_id: Filter by camera (optional)
            object_filter: Filter by object type (optional)
            
        Returns:
            True if successful
        """
        try:
            # Get events from database
            events = self.db.get_recent_events(limit=10000, 
                                              camera_id=camera_id,
                                              object_filter=object_filter)
            
            # Write to CSV
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Camera ID', 'Object', 
                               'Confidence', 'Recording Mode', 'File Path'])
                
                for event in events:
                    writer.writerow([
                        event['timestamp'],
                        event['camera_id'],
                        event['object'],
                        f"{event['confidence']:.2f}",
                        event['recording_mode'],
                        event['file_path']
                    ])
            
            print(f"Exported {len(events)} events to {output_path}")
            return True
            
        except Exception as e:
            print(f"Export error: {e}")
            return False

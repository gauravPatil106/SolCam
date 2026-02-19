"""
Database Manager for Event Logging
Handles SQLite operations for storing detection events
"""
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import config


class DatabaseManager:
    """Thread-safe SQLite database manager for event logging"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file (default: from config)
        """
        self.db_path = db_path or config.DATABASE_PATH
        self.lock = threading.Lock()
        self._create_tables()
    
    def _create_tables(self):
        """Create events table if it doesn't exist"""
        with self.lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    camera_id INTEGER NOT NULL,
                    object TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    recording_mode TEXT NOT NULL,
                    file_path TEXT NOT NULL
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON events(timestamp DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_camera_id 
                ON events(camera_id)
            ''')
            
            conn.commit()
            conn.close()
    
    def insert_event(self, camera_id: int, object_name: str, 
                    confidence: float, recording_mode: str, 
                    file_path: str) -> bool:
        """
        Insert a detection event into the database
        
        Args:
            camera_id: Camera identifier
            object_name: Detected object class name
            confidence: Detection confidence score
            recording_mode: 'LOW' or 'HIGH'
            file_path: Path to recording file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute('''
                    INSERT INTO events (timestamp, camera_id, object, confidence, 
                                      recording_mode, file_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (timestamp, camera_id, object_name, confidence, 
                     recording_mode, file_path))
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            print(f"Database insert error: {e}")
            return False
    
    def get_recent_events(self, limit: int = 100, 
                         camera_id: Optional[int] = None,
                         object_filter: Optional[str] = None) -> List[Dict]:
        """
        Retrieve recent events from database
        
        Args:
            limit: Maximum number of events to retrieve
            camera_id: Filter by camera ID (optional)
            object_filter: Filter by object type (optional)
            
        Returns:
            List of event dictionaries
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                conn.row_factory = sqlite3.Row  # Enable column access by name
                cursor = conn.cursor()
                
                query = 'SELECT * FROM events WHERE 1=1'
                params = []
                
                if camera_id is not None:
                    query += ' AND camera_id = ?'
                    params.append(camera_id)
                
                if object_filter and object_filter.lower() != 'all':
                    query += ' AND object = ?'
                    params.append(object_filter)
                
                query += ' ORDER BY timestamp DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                events = [dict(row) for row in rows]
                
                conn.close()
                return events
                
        except Exception as e:
            print(f"Database query error: {e}")
            return []
    
    def get_event_count(self, camera_id: Optional[int] = None) -> int:
        """
        Get total number of events
        
        Args:
            camera_id: Filter by camera ID (optional)
            
        Returns:
            Total event count
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                if camera_id is not None:
                    cursor.execute('SELECT COUNT(*) FROM events WHERE camera_id = ?', 
                                 (camera_id,))
                else:
                    cursor.execute('SELECT COUNT(*) FROM events')
                
                count = cursor.fetchone()[0]
                conn.close()
                return count
                
        except Exception as e:
            print(f"Database count error: {e}")
            return 0
    
    def clear_old_events(self, days: int = 30) -> int:
        """
        Delete events older than specified days
        
        Args:
            days: Delete events older than this many days
            
        Returns:
            Number of deleted events
        """
        try:
            with self.lock:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM events 
                    WHERE datetime(timestamp) < datetime('now', '-' || ? || ' days')
                ''', (days,))
                
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                return deleted
                
        except Exception as e:
            print(f"Database cleanup error: {e}")
            return 0
    
    def close(self):
        """Close database connection (cleanup)"""
        # SQLite connections are opened/closed per operation
        # This method is here for interface consistency
        pass


# Singleton instance
_db_instance = None

def get_database() -> DatabaseManager:
    """Get singleton database manager instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance

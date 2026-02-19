"""
Logging System - Comprehensive error tracking and debugging
Logs all errors to file with timestamps and stack traces
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
import traceback


class SolCamLogger:
    """Centralized logging system for SolCam"""
    
    def __init__(self, log_dir: Path = None):
        """
        Initialize logging system
        
        Args:
            log_dir: Directory to store log files (default: logs/)
        """
        if log_dir is None:
            log_dir = Path(__file__).parent.parent / 'logs'
        
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"solcam_{timestamp}.log"
        
        # Setup logger
        self.logger = logging.getLogger('SolCam')
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # File handler (detailed logs)
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler (important messages only)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Log startup
        self.logger.info("="*80)
        self.logger.info(f"SolCam Logging System Started")
        self.logger.info(f"Log file: {self.log_file}")
        self.logger.info("="*80)
    
    def debug(self, message: str, component: str = None):
        """Log debug message"""
        if component:
            self.logger.debug(f"[{component}] {message}")
        else:
            self.logger.debug(message)
    
    def info(self, message: str, component: str = None):
        """Log info message"""
        if component:
            self.logger.info(f"[{component}] {message}")
        else:
            self.logger.info(message)
    
    def warning(self, message: str, component: str = None):
        """Log warning message"""
        if component:
            self.logger.warning(f"[{component}] {message}")
        else:
            self.logger.warning(message)
    
    def error(self, message: str, component: str = None, exception: Exception = None):
        """Log error message with optional exception details"""
        if component:
            msg = f"[{component}] {message}"
        else:
            msg = message
        
        self.logger.error(msg)
        
        if exception:
            self.logger.error(f"Exception type: {type(exception).__name__}")
            self.logger.error(f"Exception message: {str(exception)}")
            self.logger.error("Stack trace:")
            self.logger.error(traceback.format_exc())
    
    def critical(self, message: str, component: str = None, exception: Exception = None):
        """Log critical error"""
        if component:
            msg = f"[{component}] {message}"
        else:
            msg = message
        
        self.logger.critical(msg)
        
        if exception:
            self.logger.critical(f"Exception type: {type(exception).__name__}")
            self.logger.critical(f"Exception message: {str(exception)}")
            self.logger.critical("Stack trace:")
            self.logger.critical(traceback.format_exc())
    
    def log_camera_event(self, camera_id, event_type: str, details: str = ""):
        """Log camera-specific event"""
        self.info(f"Camera {camera_id} | {event_type} | {details}", component="CAMERA")
    
    def log_ai_event(self, camera_id, detections: list):
        """Log AI detection event"""
        self.debug(f"Camera {camera_id} | Detections: {len(detections)}", component="AI")
        for detection in detections:
            self.debug(f"  - {detection}", component="AI")
    
    def log_recording_event(self, camera_id, mode: str, file_path: str = ""):
        """Log recording event"""
        self.debug(f"Camera {camera_id} | Mode: {mode} | File: {file_path}", component="RECORDING")
    
    def get_log_file_path(self) -> Path:
        """Get current log file path"""
        return self.log_file
    
    def get_recent_errors(self, count: int = 50) -> list:
        """Get recent error messages from log file"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            errors = [line for line in lines if 'ERROR' in line or 'CRITICAL' in line]
            return errors[-count:]
        except Exception as e:
            return [f"Failed to read log file: {e}"]


# Global logger instance
_logger_instance = None


def get_logger() -> SolCamLogger:
    """Get global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = SolCamLogger()
    return _logger_instance


def setup_exception_handler():
    """Setup global exception handler to catch uncaught exceptions"""
    def exception_handler(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow Ctrl+C to work normally
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger = get_logger()
        logger.critical(
            "Uncaught exception occurred!",
            component="SYSTEM",
            exception=exc_value
        )
        
        # Also print to console
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_handler


# Setup exception handler on import
setup_exception_handler()

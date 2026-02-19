"""
Main Entry Point
Application launcher with login system and session management
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

import config
from gui.main_window import MainWindow
from utils.logger import get_logger, setup_exception_handler


class LoginDialog(QDialog):
    """Login dialog with session timeout"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("SECUREVISION - Login")
        self.setFixedSize(500, 350)
        self.setModal(True)
        
        self._init_ui()
        self._apply_style()
    
    def _init_ui(self):
        """Initialize UI components"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title
        title = QLabel("SECUREVISION")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("AI Monitoring System")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(30)
        
        # Username
        layout.addWidget(QLabel("Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        layout.addWidget(self.username_input)
        
        # Password
        layout.addWidget(QLabel("Password:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)
        
        layout.addSpacing(10)
        
        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self._on_login)
        layout.addWidget(self.login_button)
        
        # Default credentials hint
        hint = QLabel("Default: admin / admin")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(hint)
        
        # Connect Enter key to login
        self.username_input.returnPressed.connect(self._on_login)
        self.password_input.returnPressed.connect(self._on_login)
    
    def _apply_style(self):
        """Apply styling to dialog"""
        if config.THEME_DARK:
            self.setStyleSheet("""
                QDialog {
                    background-color: #2b2b2b;
                }
                QLabel {
                    color: #ffffff;
                }
                QLineEdit {
                    background-color: #3a3a3a;
                    color: #ffffff;
                    border: 1px solid #555555;
                    padding: 8px;
                    border-radius: 4px;
                }
                QLineEdit:focus {
                    border: 1px solid #00aaff;
                }
                QPushButton {
                    background-color: #00aaff;
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #0088cc;
                }
                QPushButton:pressed {
                    background-color: #006699;
                }
            """)
    
    def _on_login(self):
        """Handle login attempt"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        # Validate credentials
        if username in config.LOGIN_CREDENTIALS:
            if config.LOGIN_CREDENTIALS[username] == password:
                self.accept()  # Close dialog with success
                return
        
        # Invalid credentials
        QMessageBox.warning(self, "Login Failed", "Invalid username or password")
        self.password_input.clear()
        self.password_input.setFocus()


class SessionManager:
    """Manages user session with timeout"""
    
    def __init__(self, timeout_minutes: int):
        """
        Initialize session manager
        
        Args:
            timeout_minutes: Session timeout in minutes
        """
        self.timeout_minutes = timeout_minutes
        self.login_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_timeout)
        self.timer.start(60000)  # Check every minute
    
    def start_session(self):
        """Start a new session"""
        self.login_time = datetime.now()
        print(f"Session started at {self.login_time}")
    
    def _check_timeout(self):
        """Check if session has timed out"""
        if self.login_time is None:
            return
        
        elapsed = datetime.now() - self.login_time
        if elapsed > timedelta(minutes=self.timeout_minutes):
            print("Session timeout - closing application")
            QApplication.quit()
    
    def extend_session(self):
        """Extend session (reset timer)"""
        self.login_time = datetime.now()


def main():
    """Main entry point"""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName(config.WINDOW_TITLE)
    
    # Show login dialog
    login_dialog = LoginDialog()
    if login_dialog.exec() != QDialog.DialogCode.Accepted:
        print("Login cancelled")
        sys.exit(0)
    
    print("Login successful")
    
    # Create session manager
    session_manager = SessionManager(config.SESSION_TIMEOUT_MINUTES)
    session_manager.start_session()
    
    # Create and show main window
    try:
        main_window = MainWindow()
        main_window.show()
        
        print("Application started successfully")
        print(f"Session timeout: {config.SESSION_TIMEOUT_MINUTES} minutes")
        
        # Run application
        sys.exit(app.exec())
        
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Failed to start application:\n{e}")
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

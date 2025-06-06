"""
Inactivity Monitor for ConsultEase Student Auto-Logout
Monitors user activity and automatically logs out students after 2 minutes of inactivity.
Provides a 30-second warning before auto-logout.
"""

import logging
from typing import Optional, Callable
from PyQt5.QtCore import QObject, QTimer, QEvent, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class InactivityWarningDialog(QDialog):
    """
    Warning dialog shown 30 seconds before auto-logout.
    """
    stay_logged_in = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Session Timeout Warning")
        self.setModal(True)
        self.setFixedSize(400, 200)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the warning dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Warning icon and message
        warning_label = QLabel("⚠️ Session Timeout Warning")
        warning_label.setFont(QFont("Arial", 16, QFont.Bold))
        warning_label.setStyleSheet("color: #e74c3c; text-align: center;")
        layout.addWidget(warning_label)
        
        # Message text
        message_label = QLabel(
            "Your session will expire in 30 seconds due to inactivity.\n"
            "Click 'Stay Logged In' to continue your session."
        )
        message_label.setFont(QFont("Arial", 12))
        message_label.setStyleSheet("color: #2c3e50; text-align: center;")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        stay_button = QPushButton("Stay Logged In")
        stay_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        stay_button.clicked.connect(self.handle_stay_logged_in)
        
        logout_button = QPushButton("Logout Now")
        logout_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        logout_button.clicked.connect(self.reject)
        
        button_layout.addWidget(stay_button)
        button_layout.addWidget(logout_button)
        layout.addLayout(button_layout)
        
    def handle_stay_logged_in(self):
        """Handle the 'Stay Logged In' button click."""
        self.stay_logged_in.emit()
        self.accept()


class InactivityMonitor(QObject):
    """
    Monitors user inactivity and handles automatic logout for student users.
    
    Features:
    - 2-minute (120 seconds) total timeout
    - 30-second warning at 90 seconds
    - Activity detection (mouse, keyboard, scrolling)
    - Student-only (not for admin users)
    - Clean integration with existing logout mechanisms
    """
    
    # Signals
    warning_timeout = pyqtSignal()  # Emitted at 90 seconds (warning time)
    auto_logout = pyqtSignal()     # Emitted at 120 seconds (auto-logout time)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Timeout settings (in milliseconds)
        self.TOTAL_TIMEOUT = 120000    # 2 minutes
        self.WARNING_TIMEOUT = 90000   # 1.5 minutes (30 seconds before logout)
        
        # Timers
        self.warning_timer = QTimer(self)
        self.warning_timer.setSingleShot(True)
        self.warning_timer.timeout.connect(self._show_warning)
        
        self.logout_timer = QTimer(self)
        self.logout_timer.setSingleShot(True)
        self.logout_timer.timeout.connect(self._auto_logout)
        
        # State
        self.is_active = False
        self.warning_dialog: Optional[InactivityWarningDialog] = None
        self.logout_callback: Optional[Callable] = None
        
        # Event filter for activity detection
        self.app = QApplication.instance()
        
        logger.info("InactivityMonitor initialized with 2-minute timeout")
        
    def set_logout_callback(self, callback: Callable):
        """Set the callback function to call when auto-logout occurs."""
        self.logout_callback = callback
        
    def start_monitoring(self):
        """Start monitoring user activity."""
        if self.is_active:
            return
            
        self.is_active = True
        
        # Install event filter to detect user activity
        if self.app:
            self.app.installEventFilter(self)
            
        # Start timers
        self.warning_timer.start(self.WARNING_TIMEOUT)
        self.logout_timer.start(self.TOTAL_TIMEOUT)
        
        logger.info("Started inactivity monitoring")
        
    def stop_monitoring(self):
        """Stop monitoring user activity."""
        if not self.is_active:
            return
            
        self.is_active = False
        
        # Remove event filter
        if self.app:
            self.app.removeEventFilter(self)
            
        # Stop timers
        self.warning_timer.stop()
        self.logout_timer.stop()
        
        # Close warning dialog if open
        if self.warning_dialog:
            try:
                if self.warning_dialog.isVisible():
                    self.warning_dialog.close()
                self.warning_dialog.deleteLater()
            except:
                pass
            self.warning_dialog = None
            
        logger.info("Stopped inactivity monitoring")
        
    def reset_timers(self):
        """Reset the inactivity timers due to user activity."""
        if not self.is_active:
            return
            
        # Close warning dialog if open
        if self.warning_dialog:
            try:
                if self.warning_dialog.isVisible():
                    self.warning_dialog.close()
                self.warning_dialog.deleteLater()
            except:
                pass
            self.warning_dialog = None
            
        # Restart timers
        self.warning_timer.stop()
        self.logout_timer.stop()
        self.warning_timer.start(self.WARNING_TIMEOUT)
        self.logout_timer.start(self.TOTAL_TIMEOUT)
        
        logger.debug("Reset inactivity timers due to user activity")
        
    def eventFilter(self, obj, event):
        """Filter events to detect user activity."""
        if not self.is_active:
            return False
            
        # Events that indicate user activity
        activity_events = [
            QEvent.MouseMove,
            QEvent.MouseButtonPress,
            QEvent.MouseButtonRelease,
            QEvent.KeyPress,
            QEvent.KeyRelease,
            QEvent.Wheel,
            QEvent.TouchBegin,
            QEvent.TouchUpdate,
            QEvent.TabletMove,
            QEvent.TabletPress
        ]
        
        if event.type() in activity_events:
            self.reset_timers()
            
        return False  # Don't consume the event
        
    def _show_warning(self):
        """Show the warning dialog at 90 seconds."""
        logger.info("Showing inactivity warning dialog")
        
        # Don't show multiple warnings
        if self.warning_dialog and self.warning_dialog.isVisible():
            return
            
        try:
            # Close any existing dialog first
            if self.warning_dialog:
                self.warning_dialog.close()
                self.warning_dialog.deleteLater()
                self.warning_dialog = None
            
            # Get the main window as parent for proper memory management
            main_window = None
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, 'objectName') and 'dashboard' in widget.objectName().lower():
                    main_window = widget
                    break
            
            # Create and show warning dialog with proper parent
            self.warning_dialog = InactivityWarningDialog(main_window)
            
            # Connect signal with proper error handling
            try:
                self.warning_dialog.stay_logged_in.connect(self._handle_stay_logged_in)
            except Exception as e:
                logger.error(f"Error connecting stay_logged_in signal: {e}")
                return
            
            # Position dialog in center of screen
            screen = QApplication.desktop().screenGeometry()
            dialog_size = self.warning_dialog.size()
            x = (screen.width() - dialog_size.width()) // 2
            y = (screen.height() - dialog_size.height()) // 2
            self.warning_dialog.move(x, y)
            
            # Show dialog non-blocking
            self.warning_dialog.show()
            self.warning_dialog.raise_()
            self.warning_dialog.activateWindow()
            
            logger.info("Inactivity warning dialog shown successfully")
            
        except Exception as e:
            logger.error(f"Error showing warning dialog: {e}")
            # Clean up on error
            if self.warning_dialog:
                try:
                    self.warning_dialog.close()
                    self.warning_dialog.deleteLater()
                except:
                    pass
                self.warning_dialog = None
        
    def _handle_stay_logged_in(self):
        """Handle the 'Stay Logged In' button click safely."""
        try:
            logger.info("User chose to stay logged in")
            
            # Close the warning dialog safely
            if self.warning_dialog and self.warning_dialog.isVisible():
                self.warning_dialog.close()
                self.warning_dialog.deleteLater()
                self.warning_dialog = None
            
            # Reset the timers to restart the inactivity monitoring
            if self.is_active:
                self.warning_timer.stop()
                self.logout_timer.stop()
                self.warning_timer.start(self.WARNING_TIMEOUT)
                self.logout_timer.start(self.TOTAL_TIMEOUT)
                logger.info("Inactivity timers reset - monitoring continues")
            
        except Exception as e:
            logger.error(f"Error handling stay logged in: {e}")
            # Ensure dialog is cleaned up even on error
            if self.warning_dialog:
                try:
                    self.warning_dialog.close()
                    self.warning_dialog.deleteLater()
                except:
                    pass
                self.warning_dialog = None

    def _auto_logout(self):
        """Perform automatic logout at 120 seconds."""
        logger.info("Performing automatic logout due to inactivity")
        
        # Close warning dialog if still open
        if self.warning_dialog and self.warning_dialog.isVisible():
            try:
                self.warning_dialog.close()
                self.warning_dialog.deleteLater()
            except:
                pass
            self.warning_dialog = None
            
        # Stop monitoring
        self.stop_monitoring()
        
        # Call logout callback if set
        if self.logout_callback:
            try:
                self.logout_callback()
            except Exception as e:
                logger.error(f"Error calling logout callback: {e}")
        
        # Emit signal for additional handling
        self.auto_logout.emit()
        
    def is_monitoring(self) -> bool:
        """Check if monitoring is currently active."""
        return self.is_active
        
    def get_remaining_time(self) -> int:
        """Get remaining time in milliseconds until logout."""
        if not self.is_active:
            return 0
            
        return self.logout_timer.remainingTime()
        
    def get_time_until_warning(self) -> int:
        """Get remaining time in milliseconds until warning."""
        if not self.is_active:
            return 0
            
        return self.warning_timer.remainingTime()


# Global instance
_inactivity_monitor = None


def get_inactivity_monitor() -> InactivityMonitor:
    """Get the global inactivity monitor instance."""
    global _inactivity_monitor
    if _inactivity_monitor is None:
        _inactivity_monitor = InactivityMonitor()
    return _inactivity_monitor 
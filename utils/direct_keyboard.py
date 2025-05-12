"""
Direct keyboard integration for ConsultEase.
This module provides direct keyboard integration that works on all platforms.
"""
import os
import sys
import time
import logging
import subprocess
import threading
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit, QPlainTextEdit

logger = logging.getLogger(__name__)

class DirectKeyboard(QObject):
    """
    Direct keyboard integration for on-screen keyboards.
    This class provides direct keyboard integration that works on all platforms.
    """
    # Signal emitted when keyboard visibility changes
    keyboard_visibility_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        """Initialize the direct keyboard integration."""
        super(DirectKeyboard, self).__init__(parent)
        
        # Initialize state
        self.keyboard_visible = False
        self.last_show_attempt = 0
        self.show_attempts = 0
        
        # Set up timer for periodic checks
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._check_keyboard)
        self.check_timer.start(5000)  # Check every 5 seconds
        
        # Log initialization
        logger.info("Direct keyboard integration initialized")
    
    def _check_keyboard(self):
        """Periodically check if the keyboard is running and restart if needed."""
        # Only run on Linux
        if not sys.platform.startswith('linux'):
            return
            
        try:
            # Check if squeekboard is running
            result = subprocess.run(['pgrep', '-f', 'squeekboard'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
            
            # If not running and should be visible, restart it
            if result.returncode != 0 and self.keyboard_visible:
                logger.info("Keyboard process not found but should be visible, restarting...")
                self.show_keyboard()
        except Exception as e:
            logger.debug(f"Error checking keyboard status: {e}")
    
    def show_keyboard(self):
        """Show the on-screen keyboard using all available methods."""
        # Limit show attempts to avoid excessive calls
        current_time = time.time()
        if current_time - self.last_show_attempt < 0.5:
            self.show_attempts += 1
            if self.show_attempts > 5:
                # Too many attempts in a short time, wait a bit
                return
        else:
            self.last_show_attempt = current_time
            self.show_attempts = 1
        
        logger.info("Showing keyboard")
        self.keyboard_visible = True
        
        # Only run on Linux
        if not sys.platform.startswith('linux'):
            return
        
        # Method 1: DBus method (most reliable for squeekboard)
        try:
            cmd = [
                "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
            ]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.keyboard_visibility_changed.emit(True)
        except Exception as e:
            logger.debug(f"Error showing keyboard via DBus: {e}")
        
        # Method 2: Direct launch of squeekboard
        try:
            # Kill any existing instances first
            subprocess.run(['pkill', '-f', 'squeekboard'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            
            # Start squeekboard with environment variables
            env = dict(os.environ)
            env['SQUEEKBOARD_FORCE'] = '1'
            env['GDK_BACKEND'] = 'wayland,x11'
            env['QT_QPA_PLATFORM'] = 'wayland;xcb'
            
            subprocess.Popen(['squeekboard'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL,
                           env=env,
                           start_new_session=True)
            
            # Try DBus again after a short delay
            QTimer.singleShot(500, lambda: self._try_dbus_show())
        except Exception as e:
            logger.debug(f"Error launching squeekboard directly: {e}")
        
        # Method 3: Try alternative keyboards
        try:
            # Check if squeekboard is running
            result = subprocess.run(['pgrep', '-f', 'squeekboard'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
            
            # If not running, try alternatives
            if result.returncode != 0:
                # Try onboard
                try:
                    subprocess.Popen(['onboard', '--size=small', '--layout=Phone'], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                except Exception:
                    # Try matchbox-keyboard
                    try:
                        subprocess.Popen(['matchbox-keyboard'], 
                                       stdout=subprocess.DEVNULL, 
                                       stderr=subprocess.DEVNULL)
                    except Exception:
                        logger.warning("Failed to start any on-screen keyboard")
        except Exception as e:
            logger.debug(f"Error checking keyboard status: {e}")
    
    def _try_dbus_show(self):
        """Try to show the keyboard using DBus after a delay."""
        try:
            cmd = [
                "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
            ]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    
    def hide_keyboard(self):
        """Hide the on-screen keyboard."""
        if not self.keyboard_visible:
            return
            
        logger.info("Hiding keyboard")
        self.keyboard_visible = False
        
        # Only run on Linux
        if not sys.platform.startswith('linux'):
            return
        
        # Method 1: DBus method
        try:
            cmd = [
                "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:false"
            ]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.keyboard_visibility_changed.emit(False)
        except Exception as e:
            logger.debug(f"Error hiding keyboard via DBus: {e}")

# Global direct keyboard instance
_direct_keyboard = None

def get_direct_keyboard():
    """Get the global direct keyboard instance."""
    global _direct_keyboard
    if _direct_keyboard is None:
        _direct_keyboard = DirectKeyboard()
    return _direct_keyboard

def setup_input_hooks():
    """Set up hooks for all input fields to show keyboard."""
    # Get the direct keyboard
    keyboard = get_direct_keyboard()
    
    # Get the application instance
    app = QApplication.instance()
    if not app:
        logger.error("No QApplication instance found")
        return
    
    # Original focus in/out event handlers
    original_line_focus_in = QLineEdit.focusInEvent
    
    # Override focus in event for QLineEdit
    def line_edit_focus_in(self, event):
        # Call original handler
        original_line_focus_in(self, event)
        # Show keyboard
        keyboard.show_keyboard()
    
    # Apply the override
    QLineEdit.focusInEvent = line_edit_focus_in
    
    # Do the same for QTextEdit
    original_text_focus_in = QTextEdit.focusInEvent
    
    def text_edit_focus_in(self, event):
        original_text_focus_in(self, event)
        keyboard.show_keyboard()
    
    QTextEdit.focusInEvent = text_edit_focus_in
    
    # And for QPlainTextEdit
    original_plain_focus_in = QPlainTextEdit.focusInEvent
    
    def plain_text_focus_in(self, event):
        original_plain_focus_in(self, event)
        keyboard.show_keyboard()
    
    QPlainTextEdit.focusInEvent = plain_text_focus_in
    
    logger.info("Input hooks set up successfully")

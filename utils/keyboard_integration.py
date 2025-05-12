"""
Direct keyboard integration module for ConsultEase.
This module provides direct integration with squeekboard and other on-screen keyboards.
It uses multiple methods to ensure the keyboard appears when needed.
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

class KeyboardIntegration(QObject):
    """
    Direct keyboard integration for on-screen keyboards.
    This class provides multiple methods to ensure the keyboard appears when needed.
    """
    # Signal emitted when keyboard visibility changes
    keyboard_visibility_changed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        """Initialize the keyboard integration."""
        super(KeyboardIntegration, self).__init__(parent)
        
        # Initialize state
        self.keyboard_visible = False
        self.keyboard_type = self._detect_keyboard()
        self.dbus_available = self._check_dbus_available()
        self.last_show_attempt = 0
        self.show_attempts = 0
        
        # Start monitor thread if squeekboard is available
        if self.keyboard_type == 'squeekboard' and self.dbus_available:
            self._start_monitor_thread()
            
        # Set up environment variables
        self._setup_environment()
        
        # Log initialization
        logger.info(f"Keyboard integration initialized. Type: {self.keyboard_type}, DBus: {self.dbus_available}")
        
        # Ensure keyboard service is running
        self._ensure_keyboard_service()
    
    def _detect_keyboard(self):
        """Detect which on-screen keyboard is available."""
        # Check environment variable override
        env_keyboard = os.environ.get('CONSULTEASE_KEYBOARD', None)
        if env_keyboard:
            return env_keyboard
            
        # On non-Linux platforms, return None
        if not sys.platform.startswith('linux'):
            return None
            
        # Check for squeekboard first (preferred)
        try:
            result = subprocess.run(['which', 'squeekboard'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
            if result.returncode == 0:
                return 'squeekboard'
        except Exception:
            pass
            
        # Check for other keyboards
        keyboards = ['onboard', 'matchbox-keyboard']
        for keyboard in keyboards:
            try:
                result = subprocess.run(['which', keyboard], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE)
                if result.returncode == 0:
                    return keyboard
            except Exception:
                pass
                
        return None
    
    def _check_dbus_available(self):
        """Check if DBus is available for communication."""
        if not sys.platform.startswith('linux'):
            return False
            
        try:
            result = subprocess.run(['which', 'dbus-send'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False
    
    def _setup_environment(self):
        """Set up environment variables for keyboard integration."""
        if sys.platform.startswith('linux'):
            os.environ["GDK_BACKEND"] = "wayland,x11"
            os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
            os.environ["SQUEEKBOARD_FORCE"] = "1"
            os.environ["MOZ_ENABLE_WAYLAND"] = "1"
            os.environ["QT_IM_MODULE"] = "wayland"
            os.environ["CLUTTER_IM_MODULE"] = "wayland"
    
    def _ensure_keyboard_service(self):
        """Ensure the keyboard service is running."""
        if not sys.platform.startswith('linux') or self.keyboard_type != 'squeekboard':
            return
            
        try:
            # Check if squeekboard service is running
            check_cmd = "systemctl --user is-active squeekboard.service"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            
            if "inactive" in result.stdout or "failed" in result.stdout:
                logger.info("Squeekboard service not running, attempting to start it...")
                
                # Try to start the service
                start_cmd = "systemctl --user start squeekboard.service"
                subprocess.run(start_cmd, shell=True)
                
                # Check if it's now running
                result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
                if "active" in result.stdout:
                    logger.info("Squeekboard service started successfully")
                else:
                    logger.warning("Failed to start squeekboard service, trying direct launch")
                    # Try starting squeekboard directly
                    subprocess.Popen(['squeekboard'], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        except Exception as e:
            logger.error(f"Error ensuring keyboard service: {e}")
    
    def _start_monitor_thread(self):
        """Start a thread to monitor keyboard visibility."""
        def monitor_thread():
            while True:
                try:
                    # Check if squeekboard is visible
                    current_visible = self._is_keyboard_visible()
                    
                    # If our internal state doesn't match reality, update it
                    if current_visible != self.keyboard_visible:
                        logger.debug(f"Keyboard visibility changed: {current_visible}")
                        self.keyboard_visible = current_visible
                        self.keyboard_visibility_changed.emit(current_visible)
                except Exception as e:
                    logger.debug(f"Error in keyboard monitor thread: {e}")
                
                # Sleep to avoid excessive CPU usage
                time.sleep(1)
        
        # Start the monitor thread
        monitor = threading.Thread(target=monitor_thread, daemon=True)
        monitor.start()
        logger.debug("Started keyboard monitor thread")
    
    def _is_keyboard_visible(self):
        """Check if the keyboard is currently visible."""
        if not self.dbus_available or self.keyboard_type != 'squeekboard':
            return self.keyboard_visible
            
        try:
            # Use dbus-send to query keyboard visibility
            cmd = [
                "dbus-send", "--print-reply", "--type=method_call", 
                "--dest=sm.puri.OSK0", "/sm/puri/OSK0", 
                "sm.puri.OSK0.GetVisible"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Parse the result
            if "boolean true" in result.stdout:
                return True
            elif "boolean false" in result.stdout:
                return False
        except Exception:
            pass
            
        return self.keyboard_visible
    
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
        
        # Method 1: DBus method (most reliable for squeekboard)
        if self.keyboard_type == 'squeekboard' and self.dbus_available:
            try:
                cmd = [
                    "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                    "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
                ]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.keyboard_visible = True
                self.keyboard_visibility_changed.emit(True)
            except Exception as e:
                logger.debug(f"Error showing keyboard via DBus: {e}")
        
        # Method 2: Direct launch
        if self.keyboard_type == 'squeekboard':
            try:
                subprocess.Popen(['squeekboard'], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL,
                               env=dict(os.environ, SQUEEKBOARD_FORCE="1"),
                               start_new_session=True)
            except Exception as e:
                logger.debug(f"Error launching squeekboard directly: {e}")
        
        # Method 3: Shell script
        if sys.platform.startswith('linux'):
            try:
                home_dir = os.path.expanduser("~")
                script_path = os.path.join(home_dir, "keyboard-show.sh")
                if os.path.exists(script_path):
                    subprocess.Popen([script_path], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
            except Exception as e:
                logger.debug(f"Error running keyboard script: {e}")
    
    def hide_keyboard(self):
        """Hide the on-screen keyboard."""
        if not self.keyboard_visible:
            return
            
        logger.info("Hiding keyboard")
        
        # Method 1: DBus method
        if self.keyboard_type == 'squeekboard' and self.dbus_available:
            try:
                cmd = [
                    "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                    "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:false"
                ]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.keyboard_visible = False
                self.keyboard_visibility_changed.emit(False)
            except Exception as e:
                logger.debug(f"Error hiding keyboard via DBus: {e}")
        
        # Method 2: Shell script
        if sys.platform.startswith('linux'):
            try:
                home_dir = os.path.expanduser("~")
                script_path = os.path.join(home_dir, "keyboard-hide.sh")
                if os.path.exists(script_path):
                    subprocess.Popen([script_path], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
            except Exception as e:
                logger.debug(f"Error running keyboard script: {e}")

# Global keyboard integration instance
_keyboard_integration = None

def get_keyboard_integration():
    """Get the global keyboard integration instance."""
    global _keyboard_integration
    if _keyboard_integration is None:
        _keyboard_integration = KeyboardIntegration()
    return _keyboard_integration

def setup_input_hooks():
    """Set up hooks for all input fields to show keyboard."""
    # Get the keyboard integration
    keyboard = get_keyboard_integration()
    
    # Get the application instance
    app = QApplication.instance()
    if not app:
        logger.error("No QApplication instance found")
        return
    
    # Original focus in/out event handlers
    original_focus_in = QLineEdit.focusInEvent
    original_focus_out = QLineEdit.focusOutEvent
    
    # Override focus in event for QLineEdit
    def line_edit_focus_in(self, event):
        # Call original handler
        original_focus_in(self, event)
        # Show keyboard
        keyboard.show_keyboard()
    
    # Override focus out event for QLineEdit
    def line_edit_focus_out(self, event):
        # Call original handler
        original_focus_out(self, event)
        # Don't hide keyboard as it might be focusing on another input
    
    # Apply the overrides
    QLineEdit.focusInEvent = line_edit_focus_in
    QLineEdit.focusOutEvent = line_edit_focus_out
    
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

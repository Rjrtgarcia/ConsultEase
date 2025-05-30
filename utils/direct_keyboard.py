"""
Direct keyboard integration for ConsultEase.
Provides a direct interface to the on-screen keyboard (squeekboard) via DBus and subprocess.
This module is used as a fallback when the keyboard_manager fails.
"""
import os
import time
import logging
import subprocess
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)

class DirectKeyboard(QObject):
    """
    Direct keyboard integration for ConsultEase.
    Provides a direct interface to the on-screen keyboard (squeekboard) via DBus and subprocess.
    """
    # Signal emitted when keyboard visibility changes
    keyboard_visibility_changed = pyqtSignal(bool)

    # Singleton instance
    _instance = None

    @classmethod
    def instance(cls):
        """Get the singleton instance of the direct keyboard."""
        if cls._instance is None:
            cls._instance = DirectKeyboard()
        return cls._instance

    def __init__(self):
        """Initialize the direct keyboard."""
        super().__init__()

        # Prevent multiple initialization of the singleton
        if DirectKeyboard._instance is not None:
            return

        # Set up keyboard properties
        self.keyboard_visible = False
        self.dbus_available = self._check_dbus_available()
        self.keyboard_type = os.environ.get('CONSULTEASE_KEYBOARD', 'squeekboard')

        # Set up auto-hide timer
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.timeout.connect(self.hide_keyboard)
        self.auto_hide_timer.setSingleShot(True)

        # Log initialization
        logger.info(f"Direct keyboard initialized with {self.keyboard_type} keyboard")

    def _check_dbus_available(self):
        """Check if DBus is available."""
        try:
            result = subprocess.run(['which', 'dbus-send'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False

    def show_keyboard(self):
        """Show the on-screen keyboard."""
        if self.keyboard_visible:
            return

        logger.info(f"Showing keyboard: {self.keyboard_type}")

        if self.keyboard_type == 'squeekboard':
            self._show_squeekboard()
        elif self.keyboard_type == 'onboard':
            self._show_onboard()
        else:
            logger.warning(f"Unknown keyboard type: {self.keyboard_type}")
            return

        self.keyboard_visible = True
        self.keyboard_visibility_changed.emit(True)

    def hide_keyboard(self):
        """Hide the on-screen keyboard."""
        if not self.keyboard_visible:
            return

        logger.info(f"Hiding keyboard: {self.keyboard_type}")

        if self.keyboard_type == 'squeekboard':
            self._hide_squeekboard()
        elif self.keyboard_type == 'onboard':
            self._hide_onboard()
        else:
            logger.warning(f"Unknown keyboard type: {self.keyboard_type}")
            return

        self.keyboard_visible = False
        self.keyboard_visibility_changed.emit(False)

    def toggle_keyboard(self):
        """Toggle the on-screen keyboard visibility."""
        if self.keyboard_visible:
            self.hide_keyboard()
        else:
            self.show_keyboard()

    def force_show_keyboard(self):
        """Force show the keyboard, even if it's already visible."""
        logger.info(f"Force showing keyboard: {self.keyboard_type}")
        
        # Set to not visible so show_keyboard() will work
        self.keyboard_visible = False
        
        # Show the keyboard
        self.show_keyboard()
        
        # Try the keyboard script as a fallback
        self._try_keyboard_script()

    def _show_squeekboard(self):
        """Show squeekboard keyboard."""
        logger.info("Attempting to show squeekboard keyboard")
        
        # First ensure squeekboard is running
        if not self._is_squeekboard_running():
            logger.info("Squeekboard not running, starting it...")
            try:
                # Kill any existing zombie processes first
                subprocess.run(['pkill', '-f', 'squeekboard'],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
                
                # Set up environment variables
                env = dict(os.environ)
                env['SQUEEKBOARD_FORCE'] = '1'
                env['GDK_BACKEND'] = 'wayland,x11'
                env['QT_QPA_PLATFORM'] = 'wayland;xcb'
                
                # Start squeekboard with appropriate options
                subprocess.Popen(['squeekboard'],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               env=env,
                               start_new_session=True)
                
                # Give it a moment to start
                time.sleep(0.5)
                logger.info("Started squeekboard process")
            except Exception as e:
                logger.error(f"Error starting squeekboard: {e}")
                # Try to use the keyboard-show.sh script as fallback
                self._try_keyboard_script()
                return

        # Now show the keyboard via DBus
        if self.dbus_available:
            try:
                # Try multiple times with different DBus commands to ensure it works
                success = False
                
                # Method 1: Standard DBus call
                try:
                    cmd = [
                        "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                        "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
                    ]
                    result = subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if result.returncode == 0:
                        success = True
                        logger.info("Showed squeekboard via standard DBus call")
                except Exception as e:
                    logger.warning(f"Standard DBus call failed: {e}")
                
                # Method 2: Try with session bus explicitly
                if not success:
                    try:
                        cmd = [
                            "dbus-send", "--session", "--type=method_call", "--dest=sm.puri.OSK0",
                            "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
                        ]
                        result = subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if result.returncode == 0:
                            success = True
                            logger.info("Showed squeekboard via session DBus call")
                    except Exception as e:
                        logger.warning(f"Session DBus call failed: {e}")
                
                # Method 3: Try with print-reply to see any errors
                if not success:
                    try:
                        cmd = [
                            "dbus-send", "--print-reply", "--type=method_call", "--dest=sm.puri.OSK0",
                            "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
                        ]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        logger.info(f"DBus print-reply result: {result.stdout}, errors: {result.stderr}")
                        success = True
                    except Exception as e:
                        logger.warning(f"Print-reply DBus call failed: {e}")
                
                if not success:
                    # Try the keyboard script as a last resort
                    self._try_keyboard_script()
            except Exception as e:
                logger.error(f"All DBus methods failed: {e}")
                # Try the keyboard script as a last resort
                self._try_keyboard_script()
        else:
            logger.warning("DBus not available, trying alternative methods")
            # Try the keyboard script as a fallback
            self._try_keyboard_script()

    def _hide_squeekboard(self):
        """Hide squeekboard keyboard."""
        if self.dbus_available:
            try:
                cmd = [
                    "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                    "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:false"
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Hid squeekboard via DBus")
            except Exception as e:
                logger.error(f"Error hiding squeekboard via DBus: {e}")
                # Try the keyboard script as a fallback
                self._try_keyboard_hide_script()
        else:
            logger.warning("DBus not available, trying alternative methods")
            # Try the keyboard script as a fallback
            self._try_keyboard_hide_script()

    def _is_squeekboard_running(self):
        """Check if squeekboard is running."""
        try:
            result = subprocess.run(['pgrep', '-f', 'squeekboard'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False

    def _show_onboard(self):
        """Show onboard keyboard."""
        try:
            # Check if onboard is already running
            if not self._is_onboard_running():
                # Start onboard with appropriate options
                subprocess.Popen(
                    ['onboard', '--size=small', '--layout=Phone', '--enable-background-transparency'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                logger.info("Started onboard")
        except Exception as e:
            logger.error(f"Error showing onboard: {e}")

    def _hide_onboard(self):
        """Hide onboard keyboard."""
        try:
            # Just kill the process
            subprocess.run(['pkill', '-f', 'onboard'],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
            logger.info("Killed onboard process")
        except Exception as e:
            logger.error(f"Error hiding onboard: {e}")

    def _is_onboard_running(self):
        """Check if onboard is running."""
        try:
            result = subprocess.run(['pgrep', '-f', 'onboard'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False

    def _try_keyboard_script(self):
        """Try to use the keyboard-show.sh script as a fallback method."""
        try:
            # Check if the keyboard script exists
            home_dir = os.path.expanduser("~")
            script_path = os.path.join(home_dir, "keyboard-show.sh")
            
            if os.path.exists(script_path):
                logger.info(f"Using keyboard script at {script_path}")
                subprocess.Popen([script_path],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                return True
            else:
                logger.warning(f"Keyboard script not found at {script_path}")
                return False
        except Exception as e:
            logger.error(f"Error using keyboard script: {e}")
            return False

    def _try_keyboard_hide_script(self):
        """Try to use the keyboard-hide.sh script as a fallback method."""
        try:
            # Check if the keyboard script exists
            home_dir = os.path.expanduser("~")
            script_path = os.path.join(home_dir, "keyboard-hide.sh")
            
            if os.path.exists(script_path):
                logger.info(f"Using keyboard hide script at {script_path}")
                subprocess.Popen([script_path],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                return True
            else:
                logger.warning(f"Keyboard hide script not found at {script_path}")
                return False
        except Exception as e:
            logger.error(f"Error using keyboard hide script: {e}")
            return False

# Convenience function to get the direct keyboard instance
def get_direct_keyboard():
    """Get the direct keyboard instance."""
    return DirectKeyboard.instance()

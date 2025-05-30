from PyQt5.QtWidgets import (QMainWindow, QDesktopWidget, QShortcut, QPushButton,
                             QStatusBar, QApplication, QLineEdit, QTextEdit,
                             QPlainTextEdit, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QEvent
from PyQt5.QtGui import QKeySequence, QIcon
import logging
import sys
import os
import subprocess

# Add parent directory to path to help with imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Import utilities
from central_system.utils.icons import IconProvider, Icons  # Import IconProvider and Icons

logger = logging.getLogger(__name__)

class BaseWindow(QMainWindow):
    """
    Base window class for ConsultEase.
    All windows should inherit from this class.
    """
    # Signal for changing windows
    change_window = pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Basic window setup
        self.setWindowTitle("ConsultEase")
        self.setGeometry(100, 100, 1024, 768) # Default size

        # Set application icon (use helper from icons module)
        app_icon = IconProvider.get_icon(Icons.APP_ICON if hasattr(Icons, 'APP_ICON') else "app", QSize(64, 64))
        if app_icon and not app_icon.isNull():
            self.setWindowIcon(app_icon)
        else:
            logger.warning("Could not load application icon.")

        # Initialize UI (must be called after basic setup)
        self.init_ui()

        # Add F11 shortcut to toggle fullscreen
        self.fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key_F11), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)

        # Store fullscreen state preference (will be set by ConsultEaseApp)
        self.fullscreen = False

    def init_ui(self):
        """
        Initialize the UI components.
        This method should be overridden by subclasses.
        """
        # Set window properties
        self.setMinimumSize(800, 480)  # Minimum size for Raspberry Pi 7" touchscreen
        self.apply_touch_friendly_style()

        # Add keyboard toggle button to the status bar
        self.statusBar().setStyleSheet("QStatusBar { border-top: 1px solid #cccccc; }")

        # Create keyboard toggle button with icon if available
        self.keyboard_toggle_button = QPushButton("⌨ Keyboard")
        self.keyboard_toggle_button.setFixedSize(140, 40)
        self.keyboard_toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #f4d35e;  /* Gold accent color for visibility */
                color: #0d3b66;  /* Dark blue text for contrast */
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 12pt;
                border: 2px solid #0d3b66;  /* Border for better visibility */
            }
            QPushButton:hover {
                background-color: #f7e07e;  /* Lighter gold on hover */
            }
            QPushButton:pressed {
                background-color: #e6c54a;  /* Darker gold when pressed */
            }
        """)

        # Try to set an icon if available
        try:
            keyboard_icon = IconProvider.get_icon("keyboard")
            if keyboard_icon and not keyboard_icon.isNull():
                self.keyboard_toggle_button.setIcon(keyboard_icon)
        except:
            # If icon not available, just use text
            pass

        self.keyboard_toggle_button.clicked.connect(self._toggle_keyboard)
        self.statusBar().addPermanentWidget(self.keyboard_toggle_button)

        # Center window on screen
        self.center()

    def apply_touch_friendly_style(self):
        """
        Apply touch-friendly styles to the application
        """
        self.setStyleSheet('''
            /* General styles */
            QWidget {
                font-size: 14pt;
            }

            QMainWindow {
                background-color: #f0f0f0;
            }

            /* Touch-friendly buttons */
            QPushButton {
                min-height: 50px;
                padding: 10px 20px;
                font-size: 14pt;
                border-radius: 5px;
                background-color: #4a86e8;
                color: white;
            }

            QPushButton:hover {
                background-color: #5a96f8;
            }

            QPushButton:pressed {
                background-color: #3a76d8;
            }

            /* Touch-friendly input fields */
            QLineEdit, QTextEdit, QComboBox {
                min-height: 40px;
                padding: 5px 10px;
                font-size: 14pt;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }

            QLineEdit:focus, QTextEdit:focus {
                border: 2px solid #4a86e8;
            }

            /* Table headers and cells */
            QTableWidget {
                font-size: 12pt;
            }

            QTableWidget::item {
                padding: 8px;
            }

            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 8px;
                font-size: 12pt;
                font-weight: bold;
            }

            /* Tabs for better touch */
            QTabBar::tab {
                min-width: 120px;
                min-height: 40px;
                padding: 8px 16px;
                font-size: 14pt;
            }

            /* Dialog buttons */
            QDialogButtonBox > QPushButton {
                min-width: 100px;
                min-height: 40px;
            }
        ''')
        logger.info("Applied touch-optimized UI settings")

    def center(self):
        """
        Center the window on the screen.
        """
        frame_geometry = self.frameGeometry()
        screen_center = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(screen_center)
        self.move(frame_geometry.topLeft())

    def keyPressEvent(self, event):
        """
        Handle key press events.
        """
        # Handle ESC key to go back to main menu
        if event.key() == Qt.Key_Escape:
            self.change_window.emit('login', None)
        # F5 key to toggle on-screen keyboard manually
        elif event.key() == Qt.Key_F5:
            self._toggle_keyboard()
        # Let F11 handle fullscreen toggle via QShortcut
        elif event.key() == Qt.Key_F11:
            pass # Handled by self.fullscreen_shortcut
        else:
            super().keyPressEvent(event)

    def _toggle_keyboard(self):
        """
        Toggle the on-screen keyboard visibility using the improved keyboard manager.
        This replaces the complex 123-line method with a clean, maintainable approach.
        """
        try:
            # Import the keyboard manager
            from central_system.utils.keyboard_manager import get_keyboard_manager

            # Get the keyboard manager instance
            keyboard_manager = get_keyboard_manager()

            # Toggle the keyboard
            success = keyboard_manager.toggle_keyboard()

            # Update button text based on current state
            if hasattr(self, 'keyboard_toggle_button'):
                if keyboard_manager.keyboard_visible:
                    self.keyboard_toggle_button.setText("⌨ Hide Keyboard")
                else:
                    self.keyboard_toggle_button.setText("⌨ Show Keyboard")

            if success:
                logger.info(f"Keyboard toggled successfully using {keyboard_manager.get_active_strategy_name()}")
            else:
                logger.warning("Failed to toggle keyboard")

        except Exception as e:
            logger.error(f"Error toggling keyboard: {e}")
            # Fallback to showing a message
            if hasattr(self, 'keyboard_toggle_button'):
                self.keyboard_toggle_button.setText("⌨ Keyboard Error")



    def toggle_fullscreen(self):
        """
        Toggle between fullscreen and normal window state.
        """
        if self.isFullScreen():
            logger.info("Exiting fullscreen mode")
            self.showNormal()
            # Re-center after exiting fullscreen
            self.center()
        else:
            logger.info("Entering fullscreen mode")
            self.showFullScreen()

    def showEvent(self, event):
        """
        Override showEvent to apply fullscreen if needed and initialize keyboard.
        This ensures the keyboard is properly set up when any window is shown.
        """
        # This ensures the window respects the initial fullscreen setting
        # The `fullscreen` flag is set by ConsultEaseApp
        if hasattr(self, 'fullscreen') and self.fullscreen:
            if not self.isFullScreen(): # Avoid toggling if already fullscreen
                self.showFullScreen()

        # Initialize keyboard for this window
        self._initialize_keyboard()

        super().showEvent(event)

    def _initialize_keyboard(self):
        """
        Initialize the keyboard for this window.
        This ensures that the keyboard appears when input fields are focused.
        """
        # Get the keyboard handler from the application
        app = QApplication.instance()
        if not app:
            logger.warning("Could not get application instance for keyboard initialization")
            return

        # Try to get keyboard handler from the application
        keyboard_handler = None
        if hasattr(app, 'keyboard_handler'):
            keyboard_handler = app.keyboard_handler
            logger.info("Found keyboard handler in application")

        # Try to get direct keyboard integration
        direct_keyboard = None
        if hasattr(app, 'direct_keyboard'):
            direct_keyboard = app.direct_keyboard
            logger.info("Found direct keyboard integration in application")

        # Set keyboard properties on all input fields
        self._set_keyboard_properties(self)

        # Install event filter to catch dynamically created widgets if not already installed
        if not hasattr(self, '_keyboard_event_filter_installed'):
            self.installEventFilter(self)
            self._keyboard_event_filter_installed = True
            logger.info(f"Installed keyboard event filter for {self.__class__.__name__}")

        # If we have a keyboard handler, ensure it's properly initialized
        if keyboard_handler:
            # Update button text based on keyboard visibility
            if hasattr(keyboard_handler, 'keyboard_visible') and keyboard_handler.keyboard_visible:
                if hasattr(self, 'keyboard_toggle_button'):
                    self.keyboard_toggle_button.setText("⌨ Hide Keyboard")
            else:
                if hasattr(self, 'keyboard_toggle_button'):
                    self.keyboard_toggle_button.setText("⌨ Show Keyboard")

            # Force show keyboard if there's a focused input field
            focused_widget = app.focusWidget()
            if focused_widget and isinstance(focused_widget, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox)):
                logger.info(f"Input field already focused, showing keyboard: {focused_widget.__class__.__name__}")
                QTimer.singleShot(100, keyboard_handler.show_keyboard)
                QTimer.singleShot(500, keyboard_handler.show_keyboard)  # Try again after a delay

        # Log keyboard initialization
        logger.info(f"Keyboard initialized for window: {self.__class__.__name__}")

    def eventFilter(self, obj, event):
        """
        Event filter to catch child widget creation and focus events.
        This ensures that dynamically created input fields also trigger the keyboard.
        """
        # Check for child added events
        if event.type() == QEvent.ChildAdded:
            # Get the child widget
            child = event.child()

            # Check if it's an input field
            if isinstance(child, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox)):
                # Initialize keyboard for this new widget
                QTimer.singleShot(100, lambda: self._initialize_input_field(child))

        # Always return False to allow the event to be processed by other filters
        return False

    def _initialize_input_field(self, widget):
        """
        Initialize keyboard handling for a single input field.
        """
        # Set property to indicate keyboard should appear on focus
        widget.setProperty("keyboardOnFocus", True)

        # Set object name if not already set
        if not widget.objectName():
            widget.setObjectName(f"{widget.__class__.__name__}_{id(widget)}")

        # Log the input field
        logger.debug(f"Initializing dynamic input field: {widget.objectName()} in {self.__class__.__name__}")

        # Connect focus events if not already connected
        if not hasattr(widget, '_keyboard_focus_connected'):
            # Store original focusInEvent method
            original_focus_in = widget.focusInEvent

            # Create new focusInEvent method that shows keyboard
            def create_focus_handler(original_handler, input_widget):
                def new_focus_in(event):
                    # Call original method
                    original_handler(event)

                    # Log the focus event
                    logger.debug(f"Focus gained on dynamic {input_widget.objectName()} in {self.__class__.__name__}")

                    # Show keyboard with multiple methods for redundancy
                    app = QApplication.instance()

                    # Method 1: Use keyboard handler
                    if app and hasattr(app, 'keyboard_handler'):
                        logger.debug(f"Showing keyboard via keyboard_handler for dynamic {input_widget.objectName()}")
                        app.keyboard_handler.show_keyboard()
                        QTimer.singleShot(100, app.keyboard_handler.show_keyboard)

                    # Method 2: Use direct keyboard integration
                    if app and hasattr(app, 'direct_keyboard'):
                        logger.debug(f"Showing keyboard via direct_keyboard for dynamic {input_widget.objectName()}")
                        app.direct_keyboard.show_keyboard()

                return new_focus_in

            # Replace focusInEvent method with a closure
            widget.focusInEvent = create_focus_handler(original_focus_in, widget)

            # Mark as connected
            widget._keyboard_focus_connected = True
            logger.debug(f"Connected focus events for dynamic {widget.objectName()}")

    def _set_keyboard_properties(self, widget):
        """
        Recursively set keyboard properties on all input fields.
        This ensures that the keyboard appears when any input field is focused.

        Args:
            widget: The widget to process (recursively processes all children)
        """
        # Find all input fields in the widget
        input_fields = widget.findChildren(QLineEdit) + \
                      widget.findChildren(QTextEdit) + \
                      widget.findChildren(QPlainTextEdit) + \
                      widget.findChildren(QComboBox)

        logger.info(f"Found {len(input_fields)} input fields in {widget.__class__.__name__}")

        # Process each input field
        for child in input_fields:
            # Set property to show keyboard on focus
            child.setProperty("keyboardOnFocus", True)

            # Set object name if not already set (helps with debugging)
            if not child.objectName():
                child.setObjectName(f"{child.__class__.__name__}_{id(child)}")

            logger.debug(f"Set keyboardOnFocus property on {child.objectName()}")

            # Connect focus events if not already connected
            if not hasattr(child, '_keyboard_focus_connected'):
                # Store original focusInEvent method
                original_focus_in = child.focusInEvent

                # Create new focusInEvent method that shows keyboard
                def create_focus_handler(original_handler, input_widget):
                    def new_focus_in(event):
                        # Call original method
                        original_handler(event)

                        # Log the focus event
                        logger.debug(f"Focus gained on {input_widget.objectName()} in {self.__class__.__name__}")

                        # Show keyboard with multiple methods for redundancy
                        app = QApplication.instance()

                        # Method 1: Use keyboard handler
                        if app and hasattr(app, 'keyboard_handler'):
                            logger.debug(f"Showing keyboard via keyboard_handler for {input_widget.objectName()}")
                            app.keyboard_handler.show_keyboard()
                            # Try again after a delay to ensure it appears
                            QTimer.singleShot(100, app.keyboard_handler.show_keyboard)

                        # Method 2: Use direct keyboard integration
                        if app and hasattr(app, 'direct_keyboard'):
                            logger.debug(f"Showing keyboard via direct_keyboard for {input_widget.objectName()}")
                            app.direct_keyboard.show_keyboard()

                        # Method 3: Try keyboard script directly
                        try:
                            home_dir = os.path.expanduser("~")
                            script_path = os.path.join(home_dir, "keyboard-show.sh")
                            if os.path.exists(script_path):
                                logger.debug(f"Showing keyboard via script for {input_widget.objectName()}")
                                QTimer.singleShot(200, lambda: subprocess.Popen([script_path],
                                                                            stdout=subprocess.DEVNULL,
                                                                            stderr=subprocess.DEVNULL))
                        except Exception as e:
                            logger.error(f"Error with keyboard script: {e}")

                    return new_focus_in

                # Replace focusInEvent method with a closure that captures the original handler and widget
                child.focusInEvent = create_focus_handler(original_focus_in, child)

                # Mark as connected
                child._keyboard_focus_connected = True
                logger.debug(f"Connected focus events for {child.objectName()}")
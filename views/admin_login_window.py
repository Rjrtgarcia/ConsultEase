from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QLineEdit, QFrame, QMessageBox, QFormLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon

import os
import logging
from .base_window import BaseWindow
from .admin_account_creation_dialog import AdminAccountCreationDialog

logger = logging.getLogger(__name__)

class AdminLoginWindow(BaseWindow):
    """
    Admin login window for secure access to the admin interface.
    """
    # Signal to notify when an admin is authenticated
    admin_authenticated = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.admin_controller = None  # Will be set by main application
        self.init_ui()

    def set_admin_controller(self, admin_controller):
        """Set the admin controller for first-time setup detection."""
        self.admin_controller = admin_controller

    def init_ui(self):
        """
        Initialize the UI components.
        """
        # Set window properties
        self.setWindowTitle('ConsultEase - Admin Login')

        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Dark header background
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #232323; color: white;")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel('Admin Login')
        title_label.setStyleSheet('font-size: 36pt; font-weight: bold; color: white;')
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        # Add header to main layout
        main_layout.addWidget(header_frame, 0)

        # Content area - white background
        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: #f5f5f5;")
        content_frame_layout = QVBoxLayout(content_frame)
        content_frame_layout.setContentsMargins(50, 50, 50, 50)

        # Create form layout for inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(20)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Username input
        username_label = QLabel('Username:')
        username_label.setStyleSheet('font-size: 16pt; font-weight: bold;')
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Enter username')
        self.username_input.setMinimumHeight(50)  # Make touch-friendly
        self.username_input.setProperty("keyboardOnFocus", True)  # Custom property to help keyboard handler
        self.username_input.setStyleSheet('''
            QLineEdit {
                border: 2px solid #ccc;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14pt;
            }
            QLineEdit:focus {
                border: 2px solid #4a86e8;
            }
        ''')
        form_layout.addRow(username_label, self.username_input)

        # Password input
        password_label = QLabel('Password:')
        password_label.setStyleSheet('font-size: 16pt; font-weight: bold;')
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Enter password')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(50)  # Make touch-friendly
        self.password_input.setProperty("keyboardOnFocus", True)  # Custom property to help keyboard handler
        self.password_input.setStyleSheet('''
            QLineEdit {
                border: 2px solid #ccc;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14pt;
            }
            QLineEdit:focus {
                border: 2px solid #4a86e8;
            }
        ''')
        form_layout.addRow(password_label, self.password_input)

        # Add form layout to content layout
        content_frame_layout.addLayout(form_layout)

        # Add error message label (hidden by default)
        self.error_label = QLabel('')
        self.error_label.setStyleSheet('color: #f44336; font-weight: bold; font-size: 14pt;')
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setVisible(False)
        content_frame_layout.addWidget(self.error_label)

        # Add spacer
        content_frame_layout.addStretch()

        # Add content to main layout
        main_layout.addWidget(content_frame, 1)

        # Footer with buttons
        footer_frame = QFrame()
        footer_frame.setStyleSheet("background-color: #232323;")
        footer_frame.setMinimumHeight(80)
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(50, 10, 50, 10)

        # Back button
        self.back_button = QPushButton('Back')
        self.back_button.setStyleSheet('''
            QPushButton {
                background-color: #808080;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14pt;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #909090;
            }
        ''')
        self.back_button.clicked.connect(self.back_to_login)

        # Login button
        self.login_button = QPushButton('Login')
        self.login_button.setStyleSheet('''
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14pt;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        ''')
        self.login_button.clicked.connect(self.login)

        footer_layout.addWidget(self.back_button)
        footer_layout.addStretch()
        footer_layout.addWidget(self.login_button)

        # Add footer to main layout
        main_layout.addWidget(footer_frame, 0)

        # Set central widget
        self.setCentralWidget(central_widget)

        # Set up keyboard shortcuts
        self.password_input.returnPressed.connect(self.login)
        self.username_input.returnPressed.connect(self.focus_password)

        # Configure tab order for better keyboard navigation
        self.setTabOrder(self.username_input, self.password_input)
        self.setTabOrder(self.password_input, self.login_button)
        self.setTabOrder(self.login_button, self.back_button)

    def focus_password(self):
        """
        Focus on the password input field.
        """
        self.password_input.setFocus()

    def show_login_error(self, message):
        """
        Show an error message on the login form.

        Args:
            message (str): The error message to display.
        """
        self.error_label.setText(message)
        self.error_label.setVisible(True)

        # Clear the password field for security
        self.password_input.clear()

    def login(self):
        """
        Handle login button click.
        """
        # Hide any previous error message
        self.error_label.setVisible(False)

        # Get username and password
        username = self.username_input.text().strip()
        password = self.password_input.text()

        # Validate inputs
        if not username:
            self.show_login_error('Please enter a username')
            self.username_input.setFocus()
            return

        if not password:
            self.show_login_error('Please enter a password')
            self.password_input.setFocus()
            return

        # Emit the signal with the credentials as a tuple
        self.admin_authenticated.emit((username, password))

    def back_to_login(self):
        """
        Go back to the login screen.
        """
        self.change_window.emit('login', None)

    def showEvent(self, event):
        """
        Override showEvent to trigger the keyboard and check for first-time setup.
        """
        super().showEvent(event)

        # Import necessary modules at the beginning
        import logging
        import subprocess
        import sys
        from PyQt5.QtWidgets import QApplication

        # Clear any previous inputs
        self.username_input.clear()
        self.password_input.clear()
        self.error_label.setVisible(False)

        # Check for first-time setup (using QTimer from top-level imports)
        QTimer.singleShot(100, self.check_first_time_setup)

        logger = logging.getLogger(__name__)
        logger.info("AdminLoginWindow shown, triggering keyboard")

        # Get the keyboard handler from the main application
        keyboard_handler = None
        try:
            # Try to get the keyboard handler from the main application
            main_app = QApplication.instance()
            if hasattr(main_app, 'keyboard_handler'):
                keyboard_handler = main_app.keyboard_handler
                logger.info("Found keyboard handler in main application")
        except Exception as e:
            logger.error(f"Error getting keyboard handler: {str(e)}")

        # Make sure the input fields have the keyboard property set
        self.username_input.setProperty("keyboardOnFocus", True)
        self.password_input.setProperty("keyboardOnFocus", True)

        # Focus the username input to trigger the keyboard
        self.username_input.setFocus()

        # Try to force show the keyboard using the handler
        if keyboard_handler:
            logger.info("Using keyboard handler to force show keyboard")
            # Try multiple times with delays to ensure it appears
            keyboard_handler.force_show_keyboard()

            # Schedule another attempt after a short delay
            QTimer.singleShot(500, keyboard_handler.force_show_keyboard)
        else:
            # Fallback to direct DBus call
            logger.info("No keyboard handler found, using direct DBus call")
            try:
                if sys.platform.startswith('linux'):
                    # Try to use dbus-send to force the keyboard with multiple attempts
                    cmd = [
                        "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                        "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
                    ]
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logger.info("Sent dbus command to show squeekboard")

                    # Try again after a delay
                    QTimer.singleShot(500, lambda: subprocess.Popen(cmd,
                                                                  stdout=subprocess.DEVNULL,
                                                                  stderr=subprocess.DEVNULL))
            except Exception as e:
                logger.error(f"Error showing keyboard: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

    def check_first_time_setup(self):
        """
        Check if this is a first-time setup and show account creation dialog if needed.
        """
        try:
            logger.info("🔍 Checking for first-time setup...")

            if not self.admin_controller:
                logger.warning("⚠️  No admin controller available for first-time setup check")
                return

            # Check admin accounts exist
            accounts_exist = self.admin_controller.check_admin_accounts_exist()
            logger.info(f"📊 Admin accounts exist: {accounts_exist}")

            # Check if first-time setup is needed
            is_first_time = self.admin_controller.is_first_time_setup()
            logger.info(f"🎯 Is first-time setup: {is_first_time}")

            if is_first_time:
                logger.info("✅ First-time setup detected - no admin accounts found")
                logger.info("🎭 Showing first-time setup dialog...")
                self.show_first_time_setup_dialog()
            else:
                logger.info("📋 Admin accounts exist - first-time setup not needed")

        except Exception as e:
            logger.error(f"❌ Error checking first-time setup: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Continue with normal login if check fails

    def show_first_time_setup_dialog(self):
        """
        Show the first-time setup dialog for creating an admin account.
        """
        try:
            logger.info("🎭 Creating AdminAccountCreationDialog...")
            dialog = AdminAccountCreationDialog(self)
            logger.info("✅ AdminAccountCreationDialog created successfully")

            logger.info("🔗 Connecting account_created signal...")
            dialog.account_created.connect(self.handle_account_created)
            logger.info("✅ Signal connected successfully")

            logger.info("📱 Showing first-time setup dialog...")
            # Show the dialog
            result = dialog.exec_()
            logger.info(f"📋 Dialog result: {result}")

            if result == dialog.Rejected:
                logger.info("❌ User cancelled first-time setup")
                # User cancelled - show message and allow manual login attempt
                QMessageBox.information(
                    self,
                    "Setup Cancelled",
                    "First-time setup was cancelled.\n\n"
                    "You can still try to login if an admin account exists, "
                    "or restart the application to run setup again."
                )
            else:
                logger.info("✅ First-time setup dialog completed")

        except Exception as e:
            logger.error(f"❌ Error showing first-time setup dialog: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(
                self,
                "Setup Error",
                f"Failed to show account creation dialog: {str(e)}\n\n"
                "Please try logging in manually or restart the application."
            )

    def handle_account_created(self, admin_info):
        """
        Handle successful account creation from the first-time setup dialog.

        Args:
            admin_info (dict): Information about the created admin account
        """
        try:
            logger.info(f"Admin account created successfully: {admin_info['username']}")

            # Refresh the admin controller cache
            if self.admin_controller:
                self.admin_controller.check_admin_accounts_exist(force_refresh=True)

            # Automatically authenticate the newly created admin
            # Emit the authentication signal to proceed to dashboard
            self.admin_authenticated.emit((admin_info['username'], None))  # Password not needed for auto-login

        except Exception as e:
            logger.error(f"Error handling account creation: {e}")
            QMessageBox.critical(
                self,
                "Login Error",
                f"Account was created but automatic login failed: {str(e)}\n\n"
                "Please try logging in manually with your new credentials."
            )
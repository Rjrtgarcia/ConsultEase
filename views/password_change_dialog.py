"""
Password change dialog for ConsultEase admin interface.
Handles forced password changes and regular password updates.
"""
import logging
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QProgressBar, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QIcon

from ..utils.ui_components import ModernButton
from ..utils.theme import ConsultEaseTheme

logger = logging.getLogger(__name__)


class PasswordChangeDialog(QDialog):
    """
    Dialog for changing admin passwords with validation and security features.
    """
    password_changed = pyqtSignal(bool)  # Emits True if password was changed successfully

    def __init__(self, admin_info, forced_change=False, parent=None):
        super().__init__(parent)
        self.admin_info = admin_info
        self.forced_change = forced_change
        self.init_ui()

    def init_ui(self):
        """Initialize the password change dialog UI."""
        self.setWindowTitle("Change Password - ConsultEase")
        self.setModal(True)
        self.setFixedSize(500, 600)

        # Apply theme
        self.setStyleSheet(ConsultEaseTheme.get_dialog_stylesheet())

        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        self.create_header(layout)

        # Password form
        self.create_password_form(layout)

        # Password requirements
        self.create_requirements_section(layout)

        # Buttons
        self.create_buttons(layout)

        # Set focus to current password field
        self.current_password_input.setFocus()

    def create_header(self, layout):
        """Create the dialog header."""
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)

        # Title
        title_label = QLabel("Change Password")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #1976d2; margin-bottom: 10px;")

        # Subtitle based on forced change
        if self.forced_change:
            subtitle_text = "Your password has expired and must be changed before continuing."
            subtitle_color = "#f44336"
        else:
            subtitle_text = f"Change password for admin: {self.admin_info.get('username', 'Unknown')}"
            subtitle_color = "#666666"

        subtitle_label = QLabel(subtitle_text)
        subtitle_label.setFont(QFont("Arial", 11))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet(f"color: {subtitle_color}; margin-bottom: 20px;")
        subtitle_label.setWordWrap(True)

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)

        layout.addWidget(header_frame)

    def create_password_form(self, layout):
        """Create the password input form."""
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        form_layout = QVBoxLayout(form_frame)

        # Current password
        current_label = QLabel("Current Password:")
        current_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.current_password_input = QLineEdit()
        self.current_password_input.setEchoMode(QLineEdit.Password)
        self.current_password_input.setPlaceholderText("Enter your current password")
        self.current_password_input.textChanged.connect(self.validate_form)

        # New password
        new_label = QLabel("New Password:")
        new_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setPlaceholderText("Enter your new password")
        self.new_password_input.textChanged.connect(self.validate_form)

        # Confirm password
        confirm_label = QLabel("Confirm New Password:")
        confirm_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setPlaceholderText("Confirm your new password")
        self.confirm_password_input.textChanged.connect(self.validate_form)

        # Add to layout
        form_layout.addWidget(current_label)
        form_layout.addWidget(self.current_password_input)
        form_layout.addSpacing(10)
        form_layout.addWidget(new_label)
        form_layout.addWidget(self.new_password_input)
        form_layout.addSpacing(10)
        form_layout.addWidget(confirm_label)
        form_layout.addWidget(self.confirm_password_input)

        layout.addWidget(form_frame)

    def create_requirements_section(self, layout):
        """Create password requirements section."""
        req_frame = QFrame()
        req_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        req_layout = QVBoxLayout(req_frame)

        req_title = QLabel("Password Requirements:")
        req_title.setFont(QFont("Arial", 10, QFont.Bold))
        req_title.setStyleSheet("color: #856404;")

        requirements_text = """
• At least 8 characters long
• Contains uppercase letters (A-Z)
• Contains lowercase letters (a-z)
• Contains numbers (0-9)
• Contains special characters (!@#$%^&*)
• Does not rely heavily on common patterns
        """

        req_details = QLabel(requirements_text.strip())
        req_details.setFont(QFont("Arial", 9))
        req_details.setStyleSheet("color: #856404; margin-left: 10px;")

        req_layout.addWidget(req_title)
        req_layout.addWidget(req_details)

        layout.addWidget(req_frame)

    def create_buttons(self, layout):
        """Create dialog buttons."""
        button_layout = QHBoxLayout()

        # Cancel button (only if not forced change)
        if not self.forced_change:
            self.cancel_button = ModernButton("Cancel")
            self.cancel_button.clicked.connect(self.reject)
            button_layout.addWidget(self.cancel_button)

        button_layout.addStretch()

        # Change password button
        self.change_button = ModernButton("Change Password", primary=True)
        self.change_button.clicked.connect(self.change_password)
        self.change_button.setEnabled(False)  # Initially disabled
        button_layout.addWidget(self.change_button)

        layout.addLayout(button_layout)

    def validate_form(self):
        """Validate the form and enable/disable the change button."""
        current_password = self.current_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()

        # Check if all fields are filled
        all_filled = all([current_password, new_password, confirm_password])

        # Check if passwords match
        passwords_match = new_password == confirm_password

        # Check password strength
        password_valid = self.validate_password_strength(new_password)

        # Enable button only if all conditions are met
        self.change_button.setEnabled(all_filled and passwords_match and password_valid)

    def validate_password_strength(self, password):
        """Validate password strength according to requirements."""
        if len(password) < 8:
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        return all([has_upper, has_lower, has_digit, has_special])

    def change_password(self):
        """Handle password change request."""
        current_password = self.current_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()

        # Final validation
        if new_password != confirm_password:
            QMessageBox.warning(self, "Error", "New passwords do not match.")
            return

        if not self.validate_password_strength(new_password):
            QMessageBox.warning(self, "Error", "New password does not meet strength requirements.")
            return

        # Disable button and show progress
        self.change_button.setEnabled(False)
        self.change_button.setText("Changing Password...")

        try:
            # Import admin controller
            from ..controllers.admin_controller import AdminController
            admin_controller = AdminController()

            # Attempt password change
            success, errors = admin_controller.change_password(
                self.admin_info['id'],
                current_password,
                new_password
            )

            if success:
                QMessageBox.information(
                    self,
                    "Success",
                    "Password changed successfully!"
                )
                self.password_changed.emit(True)
                self.accept()
            else:
                error_message = "\n".join(errors) if errors else "Password change failed."
                QMessageBox.warning(self, "Error", error_message)

        except Exception as e:
            logger.error(f"Error changing password: {e}")
            QMessageBox.critical(
                self,
                "Error",
                "An unexpected error occurred while changing the password."
            )
        finally:
            # Re-enable button
            self.change_button.setEnabled(True)
            self.change_button.setText("Change Password")

    def closeEvent(self, event):
        """Handle dialog close event."""
        if self.forced_change:
            # Don't allow closing if password change is forced
            reply = QMessageBox.question(
                self,
                "Password Change Required",
                "You must change your password before continuing. Are you sure you want to exit the application?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Exit the entire application
                from PyQt5.QtWidgets import QApplication
                QApplication.quit()
            else:
                event.ignore()
        else:
            event.accept()

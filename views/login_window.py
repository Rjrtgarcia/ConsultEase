from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QMessageBox, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QIcon
import os

from .base_window import BaseWindow
from central_system.utils.theme import ConsultEaseTheme

class LoginWindow(BaseWindow):
    """
    Login window for student RFID authentication.
    """
    # Signal to notify when a student is authenticated
    student_authenticated = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Set up logging
        import logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing LoginWindow")

        self.init_ui()

        # Initialize state variables
        self.rfid_reading = False
        self.scanning_timer = QTimer(self)
        self.scanning_timer.timeout.connect(self.update_scanning_animation)
        self.scanning_animation_frame = 0

        # The left panel is no longer needed since we moved the simulate button
        # to the scanning frame

    def init_ui(self):
        """
        Initialize the login UI components.
        """
        # Set up main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create content widget with proper margin
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(50, 30, 50, 30)
        content_layout.setSpacing(20)

        # Dark header background
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {ConsultEaseTheme.PRIMARY_COLOR}; color: {ConsultEaseTheme.TEXT_LIGHT};")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("ConsultEase")
        title_label.setStyleSheet(f"font-size: {ConsultEaseTheme.FONT_SIZE_XXLARGE}pt; font-weight: bold; color: {ConsultEaseTheme.TEXT_LIGHT};")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        # Instruction label
        instruction_label = QLabel("Please scan your RFID card to authenticate")
        instruction_label.setStyleSheet(f"font-size: {ConsultEaseTheme.FONT_SIZE_LARGE}pt; color: {ConsultEaseTheme.TEXT_LIGHT};")
        instruction_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(instruction_label)

        # Add header to main layout
        main_layout.addWidget(header_frame, 0)

        # Content area - white background
        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: #f5f5f5;")
        content_frame_layout = QVBoxLayout(content_frame)
        content_frame_layout.setContentsMargins(50, 50, 50, 50)

        # RFID scanning indicator
        self.scanning_frame = QFrame()
        self.scanning_frame.setStyleSheet(f'''
            QFrame {{
                background-color: {ConsultEaseTheme.BG_SECONDARY};
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_LARGE}px;
                border: 2px solid #ccc;
            }}
        ''')
        scanning_layout = QVBoxLayout(self.scanning_frame)
        scanning_layout.setContentsMargins(30, 30, 30, 30)
        scanning_layout.setSpacing(20)

        self.scanning_status_label = QLabel("Ready to Scan")
        self.scanning_status_label.setStyleSheet(f"font-size: {ConsultEaseTheme.FONT_SIZE_XLARGE}pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")
        self.scanning_status_label.setAlignment(Qt.AlignCenter)
        scanning_layout.addWidget(self.scanning_status_label)

        self.rfid_icon_label = QLabel()
        # Ideally, we would have an RFID icon image here
        self.rfid_icon_label.setText("🔄")
        self.rfid_icon_label.setStyleSheet(f"font-size: 48pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")
        self.rfid_icon_label.setAlignment(Qt.AlignCenter)
        scanning_layout.addWidget(self.rfid_icon_label)

        # Add manual RFID input field
        manual_input_layout = QHBoxLayout()

        self.rfid_input = QLineEdit()
        self.rfid_input.setPlaceholderText("Enter RFID manually")
        self.rfid_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid #ccc;
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_NORMAL}px;
                padding: {ConsultEaseTheme.PADDING_NORMAL}px;
                font-size: {ConsultEaseTheme.FONT_SIZE_NORMAL}pt;
                background-color: {ConsultEaseTheme.BG_PRIMARY};
                min-height: {ConsultEaseTheme.TOUCH_MIN_HEIGHT}px;
            }}
            QLineEdit:focus {{
                border: 1px solid {ConsultEaseTheme.PRIMARY_COLOR};
            }}
        """)
        self.rfid_input.returnPressed.connect(self.handle_manual_rfid_entry)
        manual_input_layout.addWidget(self.rfid_input, 3)

        submit_button = QPushButton("Submit")
        submit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {ConsultEaseTheme.PRIMARY_COLOR};
                color: {ConsultEaseTheme.TEXT_LIGHT};
                border: none;
                padding: {ConsultEaseTheme.PADDING_NORMAL}px {ConsultEaseTheme.PADDING_LARGE}px;
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_NORMAL}px;
                font-weight: bold;
                min-height: {ConsultEaseTheme.TOUCH_MIN_HEIGHT}px;
            }}
            QPushButton:hover {{
                background-color: #1a4b7c;
            }}
        """)
        submit_button.clicked.connect(self.handle_manual_rfid_entry)
        manual_input_layout.addWidget(submit_button, 1)

        scanning_layout.addLayout(manual_input_layout)

        # Add the simulate button inside the scanning frame
        self.simulate_button = QPushButton("Simulate RFID Scan")
        self.simulate_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {ConsultEaseTheme.SECONDARY_COLOR};
                color: {ConsultEaseTheme.TEXT_PRIMARY};
                border: none;
                padding: {ConsultEaseTheme.PADDING_NORMAL}px {ConsultEaseTheme.PADDING_LARGE}px;
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_NORMAL}px;
                font-weight: bold;
                margin-top: 15px;
                min-height: {ConsultEaseTheme.TOUCH_MIN_HEIGHT}px;
            }}
            QPushButton:hover {{
                background-color: #2980b9;
                color: {ConsultEaseTheme.TEXT_LIGHT};
            }}
        """)
        self.simulate_button.clicked.connect(self.simulate_rfid_scan)
        scanning_layout.addWidget(self.simulate_button)

        content_frame_layout.addWidget(self.scanning_frame, 1)

        # Add content to main layout
        main_layout.addWidget(content_frame, 1)

        # Footer with admin login button
        footer_frame = QFrame()
        footer_frame.setStyleSheet(f"background-color: {ConsultEaseTheme.PRIMARY_COLOR};")
        footer_frame.setFixedHeight(70)
        footer_layout = QHBoxLayout(footer_frame)

        # Admin login button
        admin_button = QPushButton("Admin Login")
        admin_button.setStyleSheet(f'''
            QPushButton {{
                background-color: {ConsultEaseTheme.BG_DARK};
                color: {ConsultEaseTheme.TEXT_LIGHT};
                border: none;
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_NORMAL}px;
                padding: {ConsultEaseTheme.PADDING_NORMAL}px {ConsultEaseTheme.PADDING_LARGE}px;
                max-width: 200px;
                min-height: {ConsultEaseTheme.TOUCH_MIN_HEIGHT}px;
            }}
            QPushButton:hover {{
                background-color: #3a4b5c;
            }}
        ''')
        admin_button.clicked.connect(self.admin_login)

        footer_layout.addStretch()
        footer_layout.addWidget(admin_button)
        footer_layout.addStretch()

        main_layout.addWidget(footer_frame, 0)

        # Set the main layout to a widget and make it the central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def showEvent(self, event):
        """Override showEvent"""
        super().showEvent(event)

        # Refresh RFID service to ensure it has the latest student data
        try:
            from ..services import get_rfid_service
            rfid_service = get_rfid_service()
            rfid_service.refresh_student_data()
            self.logger.info("Refreshed RFID service student data when login window shown")
        except Exception as e:
            self.logger.error(f"Error refreshing RFID service: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

        # Start RFID scanning when the window is shown
        self.logger.info("LoginWindow shown, starting RFID scanning")
        self.start_rfid_scanning()

        # Force the keyboard to show up for manual RFID entry
        try:
            # Focus the RFID input field to trigger the keyboard
            self.rfid_input.setFocus()

            # Make sure the input field has the keyboard property set
            self.rfid_input.setProperty("keyboardOnFocus", True)

            # Try all available keyboard methods
            from PyQt5.QtWidgets import QApplication
            main_app = QApplication.instance()

            # Method 1: Use direct keyboard integration
            direct_keyboard = None
            try:
                if hasattr(main_app, 'direct_keyboard') and main_app.direct_keyboard:
                    direct_keyboard = main_app.direct_keyboard
                    self.logger.info("Found direct keyboard integration in main application")

                    # Show keyboard with multiple attempts
                    direct_keyboard.show_keyboard()
                    QTimer.singleShot(500, direct_keyboard.show_keyboard)
                    QTimer.singleShot(1000, direct_keyboard.show_keyboard)

                    # Set environment variable to prefer squeekboard
                    os.environ["CONSULTEASE_KEYBOARD"] = "squeekboard"
                    self.logger.info("Set CONSULTEASE_KEYBOARD=squeekboard environment variable")
            except Exception as e:
                self.logger.error(f"Error using direct keyboard integration: {str(e)}")

            # Method 2: Use keyboard handler
            keyboard_handler = None
            try:
                if hasattr(main_app, 'keyboard_handler') and main_app.keyboard_handler:
                    keyboard_handler = main_app.keyboard_handler
                    self.logger.info("Found keyboard handler in main application")

                    # Try multiple times with delays to ensure it appears
                    keyboard_handler.force_show_keyboard()
                    QTimer.singleShot(500, keyboard_handler.force_show_keyboard)
                    QTimer.singleShot(1000, keyboard_handler.force_show_keyboard)

                    # Set environment variable to prefer squeekboard
                    os.environ["CONSULTEASE_KEYBOARD"] = "squeekboard"
                    self.logger.info("Set CONSULTEASE_KEYBOARD=squeekboard environment variable")
            except Exception as e:
                self.logger.error(f"Error using keyboard handler: {str(e)}")

            # Method 3: Direct DBus and command-line approaches
            if not direct_keyboard and not keyboard_handler:
                self.logger.info("No keyboard handlers found, using direct methods")

                # Try direct DBus call
                import subprocess
                import sys
                import os

                if sys.platform.startswith('linux'):
                    try:
                        # Try to start squeekboard first
                        try:
                            # Check if squeekboard is available
                            squeekboard_check = subprocess.run(['which', 'squeekboard'],
                                                        stdout=subprocess.PIPE,
                                                        stderr=subprocess.PIPE)

                            if squeekboard_check.returncode == 0:
                                # Kill any existing instances
                                subprocess.run(['pkill', '-f', 'squeekboard'],
                                             stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL)

                                # Start squeekboard with appropriate options
                                env = dict(os.environ)
                                env['SQUEEKBOARD_FORCE'] = '1'
                                env['GDK_BACKEND'] = 'wayland,x11'
                                env['QT_QPA_PLATFORM'] = 'wayland;xcb'

                                subprocess.Popen(['squeekboard'],
                                               stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL,
                                               env=env,
                                               start_new_session=True)

                                # Try DBus method to show squeekboard
                                cmd = [
                                    "dbus-send", "--type=method_call", "--dest=sm.puri.OSK0",
                                    "/sm/puri/OSK0", "sm.puri.OSK0.SetVisible", "boolean:true"
                                ]
                                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                self.logger.info("Started squeekboard directly")

                                # Try again after delays
                                QTimer.singleShot(500, lambda: subprocess.Popen(cmd,
                                                                              stdout=subprocess.DEVNULL,
                                                                              stderr=subprocess.DEVNULL))
                            else:
                                # Fallback to onboard
                                # Check if onboard is available
                                onboard_check = subprocess.run(['which', 'onboard'],
                                                            stdout=subprocess.PIPE,
                                                            stderr=subprocess.PIPE)

                                if onboard_check.returncode == 0:
                                    # Kill any existing instances
                                    subprocess.run(['pkill', '-f', 'onboard'],
                                                 stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.DEVNULL)

                                    # Start onboard with appropriate options
                                    subprocess.Popen(
                                        ['onboard', '--size=small', '--layout=Phone', '--enable-background-transparency'],
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL,
                                        start_new_session=True
                                    )
                                    self.logger.info("Started onboard as fallback")
                        except Exception as e:
                            self.logger.error(f"Error starting squeekboard: {e}")

                        # Try using the keyboard-show.sh script if it exists
                        home_dir = os.path.expanduser("~")
                        script_path = os.path.join(home_dir, "keyboard-show.sh")
                        if os.path.exists(script_path):
                            self.logger.info("Using keyboard-show.sh script")
                            QTimer.singleShot(1500, lambda: subprocess.Popen([script_path],
                                                                          stdout=subprocess.DEVNULL,
                                                                          stderr=subprocess.DEVNULL))
                    except Exception as e:
                        self.logger.error(f"Error with direct keyboard methods: {str(e)}")

            # Focus the input field again after a delay
            QTimer.singleShot(300, lambda: self.rfid_input.setFocus())

        except Exception as e:
            self.logger.error(f"Error showing keyboard: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)

    def start_rfid_scanning(self):
        """
        Start the RFID scanning animation and process.
        """
        # Refresh RFID service to ensure it has the latest student data
        try:
            from ..services import get_rfid_service
            rfid_service = get_rfid_service()
            rfid_service.refresh_student_data()
            self.logger.info("Refreshed RFID service student data when starting RFID scanning")
        except Exception as e:
            self.logger.error(f"Error refreshing RFID service: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

        self.rfid_reading = True
        self.scanning_status_label.setText("Scanning...")
        self.scanning_status_label.setStyleSheet(f"font-size: {ConsultEaseTheme.FONT_SIZE_XLARGE}pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")
        self.scanning_frame.setStyleSheet(f'''
            QFrame {{
                background-color: {ConsultEaseTheme.BG_SECONDARY};
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_LARGE}px;
                border: 2px solid {ConsultEaseTheme.SECONDARY_COLOR};
            }}
        ''')
        self.scanning_timer.start(500)  # Update animation every 500ms

    def stop_rfid_scanning(self):
        """
        Stop the RFID scanning animation.
        """
        self.rfid_reading = False
        self.scanning_timer.stop()
        self.scanning_status_label.setText("Ready to Scan")
        self.scanning_status_label.setStyleSheet(f"font-size: {ConsultEaseTheme.FONT_SIZE_XLARGE}pt; color: {ConsultEaseTheme.SECONDARY_COLOR};")
        self.scanning_frame.setStyleSheet(f'''
            QFrame {{
                background-color: {ConsultEaseTheme.BG_SECONDARY};
                border-radius: {ConsultEaseTheme.BORDER_RADIUS_LARGE}px;
                border: 2px solid #ccc;
            }}
        ''')
        self.rfid_icon_label.setText("🔄")

    def update_scanning_animation(self):
        """
        Update the scanning animation frames.
        """
        animations = ["🔄", "🔁", "🔃", "🔂"]
        self.scanning_animation_frame = (self.scanning_animation_frame + 1) % len(animations)
        self.rfid_icon_label.setText(animations[self.scanning_animation_frame])

    def handle_rfid_read(self, rfid_uid, student=None):
        """
        Handle RFID read event.

        Args:
            rfid_uid (str): The RFID UID that was read
            student (object, optional): Student object if already validated
        """
        self.logger.info(f"LoginWindow.handle_rfid_read called with rfid_uid: {rfid_uid}, student: {student}")

        # Stop scanning animation
        self.stop_rfid_scanning()

        # If student is not provided, try to look it up directly
        if not student and rfid_uid:
            try:
                # First refresh the RFID service to ensure it has the latest student data
                try:
                    from ..services import get_rfid_service
                    rfid_service = get_rfid_service()
                    rfid_service.refresh_student_data()
                    self.logger.info("Refreshed RFID service student data before looking up student")
                except Exception as e:
                    self.logger.error(f"Error refreshing RFID service: {str(e)}")

                from ..models import Student, get_db
                db = get_db()

                # Try exact match first
                self.logger.info(f"Looking up student with RFID UID: {rfid_uid}")
                student = db.query(Student).filter(Student.rfid_uid == rfid_uid).first()

                # If no exact match, try case-insensitive match
                if not student:
                    self.logger.info(f"No exact match found, trying case-insensitive match for RFID: {rfid_uid}")
                    # For PostgreSQL
                    try:
                        student = db.query(Student).filter(Student.rfid_uid.ilike(rfid_uid)).first()
                    except:
                        # For SQLite
                        student = db.query(Student).filter(Student.rfid_uid.lower() == rfid_uid.lower()).first()

                if student:
                    self.logger.info(f"LoginWindow: Found student directly: {student.name} with RFID: {rfid_uid}")
                else:
                    # Log all students in the database for debugging
                    all_students = db.query(Student).all()
                    self.logger.warning(f"No student found for RFID {rfid_uid}")
                    self.logger.info(f"Available students in database: {len(all_students)}")
                    for s in all_students:
                        self.logger.info(f"  - ID: {s.id}, Name: {s.name}, RFID: {s.rfid_uid}")
            except Exception as e:
                self.logger.error(f"LoginWindow: Error looking up student: {str(e)}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")

        if student:
            # Authentication successful
            self.logger.info(f"Authentication successful for student: {student.name} with ID: {student.id}")

            # Convert student object to safe dictionary format to avoid DetachedInstanceError
            try:
                student_data = {
                    'id': student.id,
                    'name': student.name,
                    'department': student.department,
                    'rfid_uid': student.rfid_uid,
                    'created_at': student.created_at.isoformat() if student.created_at else None,
                    'updated_at': student.updated_at.isoformat() if student.updated_at else None
                }
                self.logger.info(f"Converted student to safe data format: {student_data}")
            except Exception as e:
                self.logger.error(f"Error converting student to safe format: {e}")
                # Fallback to basic data
                student_data = {
                    'id': getattr(student, 'id', None),
                    'name': getattr(student, 'name', 'Unknown'),
                    'department': getattr(student, 'department', 'Unknown'),
                    'rfid_uid': getattr(student, 'rfid_uid', ''),
                    'created_at': None,
                    'updated_at': None
                }

            self.show_success(f"Welcome, {student_data['name']}!")

            # Log the emission of the signal
            self.logger.info(f"LoginWindow: Emitting student_authenticated signal for {student_data['name']}")

            # Emit the signal to navigate to the dashboard with safe student data
            self.student_authenticated.emit(student_data)

            # Also emit a change_window signal as a backup
            self.logger.info(f"LoginWindow: Emitting change_window signal for dashboard")
            self.change_window.emit("dashboard", student_data)

            # Force a delay to ensure the signals are processed
            QTimer.singleShot(500, lambda: self._force_dashboard_navigation(student_data))
        else:
            # Authentication failed
            self.logger.warning(f"Authentication failed for RFID: {rfid_uid}")
            self.show_error("RFID card not recognized. Please try again or contact an administrator.")

    def _force_dashboard_navigation(self, student_data):
        """
        Force navigation to dashboard as a fallback.

        Args:
            student_data (dict): Student data dictionary
        """
        self.logger.info("Forcing dashboard navigation as fallback")
        self.change_window.emit("dashboard", student_data)

    def show_success(self, message):
        """
        Show success message and visual feedback.
        """
        self.scanning_status_label.setText("Authenticated")
        self.scanning_status_label.setStyleSheet("font-size: 20pt; color: #4caf50;")
        self.scanning_frame.setStyleSheet('''
            QFrame {
                background-color: #e8f5e9;
                border-radius: 10px;
                border: 2px solid #4caf50;
            }
        ''')
        self.rfid_icon_label.setText("✅")

        # Show message in a popup
        QMessageBox.information(self, "Authentication Success", message)

    def show_error(self, message):
        """
        Show error message and visual feedback.
        """
        self.scanning_status_label.setText("Error")
        self.scanning_status_label.setStyleSheet("font-size: 20pt; color: #f44336;")
        self.scanning_frame.setStyleSheet('''
            QFrame {
                background-color: #ffebee;
                border-radius: 10px;
                border: 2px solid #f44336;
            }
        ''')
        self.rfid_icon_label.setText("❌")

        # Show error in a popup
        QMessageBox.warning(self, "Authentication Error", message)

        # Reset after a delay
        QTimer.singleShot(3000, self.stop_rfid_scanning)

    def admin_login(self):
        """
        Handle admin login button click.
        """
        self.change_window.emit("admin_login", None)

    def simulate_rfid_scan(self):
        """
        Simulate an RFID scan for development purposes.
        """
        # Start the scanning animation
        self.start_rfid_scanning()

        # Get the RFID service and simulate a card read
        try:
            # Try to get a real student RFID from the database
            from ..models import Student, get_db
            db = get_db()
            student = db.query(Student).first()

            if student and student.rfid_uid:
                self.logger.info(f"Simulating RFID scan with real student: {student.name}, RFID: {student.rfid_uid}")
                rfid_uid = student.rfid_uid
            else:
                self.logger.info("No students found in database, using default RFID")
                rfid_uid = "TESTCARD123"  # Use the test card we added

            from ..services import get_rfid_service
            rfid_service = get_rfid_service()

            # Refresh the RFID service to ensure it has the latest student data
            rfid_service.refresh_student_data()
            self.logger.info("Refreshed RFID service student data before simulating scan")

            # Simulate a card read - this will trigger the normal authentication flow
            # through the registered callbacks
            self.logger.info(f"Simulating RFID scan with UID: {rfid_uid}")
            rfid_service.simulate_card_read(rfid_uid)
        except Exception as e:
            self.logger.error(f"Error simulating RFID scan: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

            # If there's an error, stop the scanning animation and show an error
            QTimer.singleShot(1000, lambda: self.handle_rfid_read("TESTCARD123", None))

    def handle_manual_rfid_entry(self):
        """
        Handle manual RFID entry from the input field.
        """
        rfid_uid = self.rfid_input.text().strip()
        if rfid_uid:
            self.logger.info(f"Manual RFID entry: {rfid_uid}")
            self.rfid_input.clear()
            self.start_rfid_scanning()

            # Get the RFID service and simulate a card read with the entered UID
            try:
                from ..services import get_rfid_service
                rfid_service = get_rfid_service()

                # Refresh the RFID service to ensure it has the latest student data
                rfid_service.refresh_student_data()
                self.logger.info("Refreshed RFID service student data before manual RFID entry")

                # Use the entered RFID UID - this will trigger the normal authentication flow
                # through the registered callbacks
                self.logger.info(f"Simulating RFID scan with manually entered UID: {rfid_uid}")
                rfid_service.simulate_card_read(rfid_uid)
            except Exception as e:
                self.logger.error(f"Error processing manual RFID entry: {str(e)}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")

                # If there's an error, directly handle the RFID read
                self.logger.info(f"Directly handling RFID read due to error: {rfid_uid}")
                QTimer.singleShot(1000, lambda: self.handle_rfid_read(rfid_uid, None))

# Create a script to ensure the keyboard works on Raspberry Pi
def create_keyboard_setup_script():
    """
    Create a script to set up the virtual keyboard on the Raspberry Pi.
    This should be called when deploying the application.
    """
    script_content = """#!/bin/bash
# Enhanced setup script for ConsultEase virtual keyboard
echo "Setting up ConsultEase virtual keyboard..."

# Ensure squeekboard is installed (preferred)
if ! command -v squeekboard &> /dev/null; then
    echo "Squeekboard not found, attempting to install..."
    sudo apt update
    sudo apt install -y squeekboard
fi

# Ensure dbus-x11 is installed for dbus-send command (required for squeekboard)
if ! command -v dbus-send &> /dev/null; then
    echo "dbus-send not found, installing dbus-x11 package..."
    sudo apt update
    sudo apt install -y dbus-x11
fi

# Ensure onboard is installed as fallback
if ! command -v onboard &> /dev/null; then
    echo "Onboard not found, installing as fallback..."
    sudo apt update
    sudo apt install -y onboard
fi

# Configure squeekboard
echo "Configuring squeekboard..."

# Make sure squeekboard service is enabled
if command -v systemctl &> /dev/null; then
    echo "Enabling squeekboard service..."
    systemctl --user enable squeekboard.service 2>/dev/null
fi

# Configure onboard as fallback
if command -v onboard &> /dev/null; then
    echo "Configuring onboard as fallback..."
    mkdir -p ~/.config/autostart
    cat > ~/.config/autostart/onboard-autostart.desktop << EOF
[Desktop Entry]
Type=Application
Name=Onboard
Exec=onboard --size=small --layout=Phone --enable-background-transparency --theme=Nightshade
Comment=Flexible on-screen keyboard
EOF

    # Create onboard configuration directory
    mkdir -p ~/.config/onboard

    # Create onboard configuration file with touch-friendly settings
    cat > ~/.config/onboard/onboard.conf << EOF
[main]
layout=Phone
theme=Nightshade
key-size=small
enable-background-transparency=true
show-status-icon=true
start-minimized=false
show-tooltips=false
auto-show=true
auto-show-delay=500
auto-hide=true
auto-hide-delay=1000
xembed-onboard=true
enable-touch-input=true
touch-feedback-enabled=true
touch-feedback-size=small
EOF
fi

# Start squeekboard
echo "Starting squeekboard..."
pkill -f squeekboard
if command -v squeekboard &> /dev/null; then
    # Start squeekboard with environment variables
    SQUEEKBOARD_FORCE=1 GDK_BACKEND=wayland,x11 QT_QPA_PLATFORM=wayland squeekboard &
    sleep 0.5

    # Show squeekboard
    if command -v dbus-send &> /dev/null; then
        dbus-send --type=method_call --dest=sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0.SetVisible boolean:true
    fi
fi

# Set environment variables for proper keyboard operation
echo "Setting up environment variables..."
mkdir -p ~/.config/environment.d/
cat > ~/.config/environment.d/consultease.conf << EOF
# ConsultEase keyboard environment variables
GDK_BACKEND=wayland,x11
QT_QPA_PLATFORM=wayland;xcb
SQUEEKBOARD_FORCE=1
CONSULTEASE_KEYBOARD=squeekboard
CONSULTEASE_KEYBOARD_DEBUG=true
MOZ_ENABLE_WAYLAND=1
QT_IM_MODULE=wayland
CLUTTER_IM_MODULE=wayland
# Onboard variables as fallback
ONBOARD_ENABLE_TOUCH=1
ONBOARD_XEMBED=1
EOF

# Also add to .bashrc for immediate effect
if ! grep -q "CONSULTEASE_KEYBOARD" ~/.bashrc; then
    echo "Adding environment variables to .bashrc..."
    cat >> ~/.bashrc << EOF

# ConsultEase keyboard environment variables
export GDK_BACKEND=wayland,x11
export QT_QPA_PLATFORM=wayland;xcb
export SQUEEKBOARD_FORCE=1
export CONSULTEASE_KEYBOARD=squeekboard
export CONSULTEASE_KEYBOARD_DEBUG=true
export MOZ_ENABLE_WAYLAND=1
export QT_IM_MODULE=wayland
export CLUTTER_IM_MODULE=wayland
# Onboard variables as fallback
export ONBOARD_ENABLE_TOUCH=1
export ONBOARD_XEMBED=1
EOF
fi

# Create keyboard management scripts
echo "Creating keyboard management scripts..."

# Create keyboard toggle script
cat > ~/keyboard-toggle.sh << EOF
#!/bin/bash
# Toggle on-screen keyboard visibility

# Check for squeekboard first
if command -v dbus-send &> /dev/null; then
    if dbus-send --print-reply --type=method_call --dest=sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0.GetVisible | grep -q "boolean true"; then
        dbus-send --type=method_call --dest=sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0.SetVisible boolean:false
        echo "Squeekboard hidden"
    else
        dbus-send --type=method_call --dest=sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0.SetVisible boolean:true
        echo "Squeekboard shown"
    fi
# Check for onboard as fallback
elif command -v onboard &> /dev/null; then
    if pgrep -f onboard > /dev/null; then
        pkill -f onboard
        echo "Onboard keyboard hidden"
    else
        onboard --size=small --layout=Phone --enable-background-transparency &
        echo "Onboard keyboard shown"
    fi
# Try matchbox as last resort
elif command -v matchbox-keyboard &> /dev/null; then
    if pgrep -f matchbox-keyboard > /dev/null; then
        pkill -f matchbox-keyboard
        echo "Matchbox keyboard hidden"
    else
        matchbox-keyboard &
        echo "Matchbox keyboard shown"
    fi
else
    echo "No supported on-screen keyboard found"
fi
EOF
chmod +x ~/keyboard-toggle.sh

# Create keyboard show script
cat > ~/keyboard-show.sh << EOF
#!/bin/bash
# Force show keyboard

# Try squeekboard first
if command -v dbus-send &> /dev/null; then
    # Make sure squeekboard is running
    if command -v squeekboard &> /dev/null; then
        # Check if squeekboard is running
        if ! pgrep -f squeekboard > /dev/null; then
            # Start squeekboard with environment variables
            SQUEEKBOARD_FORCE=1 GDK_BACKEND=wayland,x11 QT_QPA_PLATFORM=wayland squeekboard &
            sleep 0.5
        fi
    fi

    # Show squeekboard
    dbus-send --type=method_call --dest=sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0.SetVisible boolean:true
    echo "Squeekboard shown"
    exit 0
fi

# Try onboard as fallback
if command -v onboard &> /dev/null; then
    # Kill any existing instances
    pkill -f onboard
    # Start onboard with appropriate options
    onboard --size=small --layout=Phone --enable-background-transparency --theme=Nightshade &
    echo "Onboard keyboard shown"
    exit 0
fi

# Try matchbox as last resort
if command -v matchbox-keyboard &> /dev/null; then
    matchbox-keyboard &
    echo "Matchbox keyboard shown"
    exit 0
fi

echo "No supported on-screen keyboard found"
EOF
chmod +x ~/keyboard-show.sh

# Create keyboard hide script
cat > ~/keyboard-hide.sh << EOF
#!/bin/bash
# Force hide keyboard

# Try squeekboard first
if command -v dbus-send &> /dev/null; then
    dbus-send --type=method_call --dest=sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0.SetVisible boolean:false
    echo "Squeekboard hidden"
    exit 0
fi

# Try onboard as fallback
if command -v onboard &> /dev/null; then
    pkill -f onboard
    echo "Onboard keyboard hidden"
    exit 0
fi

# Try matchbox as last resort
if command -v matchbox-keyboard &> /dev/null; then
    pkill -f matchbox-keyboard
    echo "Matchbox keyboard hidden"
    exit 0
fi

echo "No supported on-screen keyboard found"
EOF
chmod +x ~/keyboard-hide.sh

# Create keyboard status script
cat > ~/keyboard-status.sh << EOF
#!/bin/bash
# Check keyboard status

# Check for onboard
if command -v onboard &> /dev/null; then
    echo "Onboard status:"
    if pgrep -f onboard > /dev/null; then
        echo "Onboard is RUNNING"
    else
        echo "Onboard is NOT RUNNING"
    fi
fi

# Check for squeekboard
if command -v systemctl &> /dev/null && command -v dbus-send &> /dev/null; then
    echo -e "\\nSqueekboard service status:"
    systemctl --user status squeekboard.service 2>/dev/null || echo "Squeekboard service not found"

    echo -e "\\nSqueekboard visibility:"
    if dbus-send --print-reply --type=method_call --dest=sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0.GetVisible 2>/dev/null | grep -q "boolean true"; then
        echo "Squeekboard is VISIBLE"
    else
        echo "Squeekboard is HIDDEN or not available"
    fi
fi

# Check for matchbox
if command -v matchbox-keyboard &> /dev/null; then
    echo -e "\\nMatchbox keyboard status:"
    if pgrep -f matchbox-keyboard > /dev/null; then
        echo "Matchbox keyboard is RUNNING"
    else
        echo "Matchbox keyboard is NOT RUNNING"
    fi
fi
EOF
chmod +x ~/keyboard-status.sh

# Create keyboard restart script
cat > ~/keyboard-restart.sh << EOF
#!/bin/bash
# Restart keyboard

# Try squeekboard first
if command -v systemctl &> /dev/null; then
    echo "Restarting squeekboard service..."
    systemctl --user stop squeekboard.service 2>/dev/null
    pkill -f squeekboard
    sleep 1
    systemctl --user start squeekboard.service 2>/dev/null

    # Check if service is running
    if systemctl --user is-active squeekboard.service 2>/dev/null; then
        echo "Squeekboard service restarted successfully"
    else
        echo "Warning: Squeekboard service failed to restart. Starting manually..."
        # Try starting squeekboard directly
        if command -v squeekboard &> /dev/null; then
            nohup squeekboard > /dev/null 2>&1 &
        fi
    fi

    # Force show the keyboard
    if command -v dbus-send &> /dev/null; then
        dbus-send --type=method_call --dest=sm.puri.OSK0 /sm/puri/OSK0 sm.puri.OSK0.SetVisible boolean:true
        echo "Squeekboard shown"
    fi
    exit 0
fi

# Try onboard as fallback
if command -v onboard &> /dev/null; then
    echo "Restarting onboard..."
    pkill -f onboard
    sleep 1
    onboard --size=small --layout=Phone --enable-background-transparency --theme=Nightshade &
    echo "Onboard restarted"
    exit 0
fi

# Try matchbox as last resort
if command -v matchbox-keyboard &> /dev/null; then
    echo "Restarting matchbox-keyboard..."
    pkill -f matchbox-keyboard
    sleep 1
    matchbox-keyboard &
    echo "Matchbox keyboard restarted"
    exit 0
fi

echo "No supported on-screen keyboard found"
EOF
chmod +x ~/keyboard-restart.sh

# Create desktop shortcut for keyboard toggle
mkdir -p ~/.local/share/applications/
cat > ~/.local/share/applications/keyboard-toggle.desktop << EOF
[Desktop Entry]
Name=Toggle Keyboard
Comment=Toggle on-screen keyboard visibility
Exec=/bin/bash ~/keyboard-toggle.sh
Icon=input-keyboard
Terminal=false
Type=Application
Categories=Utility;
EOF

echo "Setup complete! For changes to fully take effect, please reboot your system."
echo ""
echo "Keyboard management scripts created:"
echo "  ~/keyboard-toggle.sh - Toggle keyboard visibility"
echo "  ~/keyboard-show.sh - Force show keyboard"
echo "  ~/keyboard-hide.sh - Force hide keyboard"
echo "  ~/keyboard-status.sh - Check keyboard status"
echo "  ~/keyboard-restart.sh - Restart keyboard service"
echo ""
echo "If the keyboard doesn't appear automatically, try:"
echo "1. Run ~/keyboard-show.sh to manually show it"
echo "2. Run ~/keyboard-restart.sh to restart the keyboard service"
echo "3. Press F5 in the application to toggle the keyboard"
"""

    # Create scripts directory if it doesn't exist
    script_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts")
    os.makedirs(script_dir, exist_ok=True)

    # Write the script
    script_path = os.path.join(script_dir, "setup_keyboard.sh")
    with open(script_path, "w") as f:
        f.write(script_content)

    # Make the script executable on Unix
    if os.name == "posix":
        import stat
        st = os.stat(script_path)
        os.chmod(script_path, st.st_mode | stat.S_IEXEC)

    return script_path
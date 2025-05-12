import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer

# Add parent directory to path to help with imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('consultease.log')
    ]
)
logger = logging.getLogger(__name__)

# Import models and controllers
from central_system.models import init_db
from central_system.controllers import (
    RFIDController,
    FacultyController,
    ConsultationController,
    AdminController
)

# Import views
from central_system.views import (
    LoginWindow,
    DashboardWindow,
    AdminLoginWindow,
    AdminDashboardWindow
)

# Import the keyboard setup script generator
from central_system.views.login_window import create_keyboard_setup_script

# Import utilities
from central_system.utils import (
    install_keyboard_handler,
    apply_stylesheet,
    WindowTransitionManager
)
# Import keyboard integration
from central_system.utils.direct_keyboard import get_direct_keyboard, setup_input_hooks
# Import icons module separately to avoid early QPixmap creation
from central_system.utils import icons

class ConsultEaseApp:
    """
    Main application class for ConsultEase.
    """

    def __init__(self, fullscreen=False):
        """
        Initialize the ConsultEase application.
        """
        logger.info("Initializing ConsultEase application")

        # Create QApplication instance
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("ConsultEase")

        # Set up icons and modern UI (after QApplication is created)
        icons.initialize()
        logger.info("Initialized icons")

        # Apply modern stylesheet (dark theme by default)
        theme = self._get_theme_preference()
        apply_stylesheet(self.app, theme)
        logger.info(f"Applied {theme} theme stylesheet")

        # Create keyboard setup script for Raspberry Pi
        try:
            script_path = create_keyboard_setup_script()
            logger.info(f"Created keyboard setup script at {script_path}")
        except Exception as e:
            logger.error(f"Failed to create keyboard setup script: {e}")

        # Install keyboard handler for touch input
        try:
            self.keyboard_handler = install_keyboard_handler(self.app)
            logger.info("Installed virtual keyboard handler")
        except Exception as e:
            logger.error(f"Failed to install virtual keyboard handler: {e}")
            self.keyboard_handler = None

        # Initialize direct keyboard integration
        try:
            self.direct_keyboard = get_direct_keyboard()
            setup_input_hooks()
            logger.info("Initialized direct keyboard integration")
        except Exception as e:
            logger.error(f"Failed to initialize direct keyboard integration: {e}")
            self.direct_keyboard = None

        # Initialize database
        init_db()

        # Initialize controllers
        self.rfid_controller = RFIDController()
        self.faculty_controller = FacultyController()
        self.consultation_controller = ConsultationController()
        self.admin_controller = AdminController()

        # Ensure default admin exists
        self.admin_controller.ensure_default_admin()

        # Initialize windows
        self.login_window = None
        self.dashboard_window = None
        self.admin_login_window = None
        self.admin_dashboard_window = None

        # Start controllers
        logger.info("Starting RFID controller")
        self.rfid_controller.start()
        self.rfid_controller.register_callback(self.handle_rfid_scan)

        logger.info("Starting faculty controller")
        self.faculty_controller.start()

        logger.info("Starting consultation controller")
        self.consultation_controller.start()

        # Make sure at least one faculty is available for testing
        self._ensure_dr_john_smith_available()

        # Current student
        self.current_student = None

        # Initialize transition manager
        self.transition_manager = WindowTransitionManager(duration=300)
        logger.info("Initialized window transition manager")

        # Verify RFID controller is properly initialized
        try:
            from .services import get_rfid_service
            rfid_service = get_rfid_service()
            logger.info(f"RFID service initialized: {rfid_service}, simulation mode: {rfid_service.simulation_mode}")

            # Log registered callbacks
            logger.info(f"RFID service callbacks: {len(rfid_service.callbacks)}")
            for i, callback in enumerate(rfid_service.callbacks):
                callback_name = getattr(callback, '__name__', str(callback))
                logger.info(f"  Callback {i}: {callback_name}")
        except Exception as e:
            logger.error(f"Error verifying RFID service: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        # Connect cleanup method
        self.app.aboutToQuit.connect(self.cleanup)

        # Show login window
        self.show_login_window()

        # Store fullscreen preference for use in window creation
        self.fullscreen = fullscreen

    def _get_theme_preference(self):
        """
        Get the user's theme preference.

        Returns:
            str: Theme name ('light' or 'dark')
        """
        # Default to light theme as per the technical context document
        theme = "light"

        # Check for environment variable
        if "CONSULTEASE_THEME" in os.environ:
            env_theme = os.environ["CONSULTEASE_THEME"].lower()
            if env_theme in ["light", "dark"]:
                theme = env_theme

        # Log the theme being used
        logger.info(f"Using {theme} theme based on preference")

        return theme

    def _ensure_dr_john_smith_available(self):
        """
        Make sure Dr. John Smith is available for testing.
        """
        try:
            # Use the faculty controller to ensure at least one faculty is available
            available_faculty = self.faculty_controller.ensure_available_faculty()

            if available_faculty:
                logger.info(f"Ensured faculty availability: {available_faculty.name} (ID: {available_faculty.id}) is now available")
            else:
                logger.warning("Could not ensure faculty availability")
        except Exception as e:
            logger.error(f"Error ensuring faculty availability: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def run(self):
        """
        Run the application.
        """
        logger.info("Starting ConsultEase application")
        return self.app.exec_()

    def cleanup(self):
        """
        Clean up resources before exiting.
        """
        logger.info("Cleaning up ConsultEase application")

        # Stop controllers
        self.rfid_controller.stop()
        self.faculty_controller.stop()
        self.consultation_controller.stop()

    def show_login_window(self):
        """
        Show the login window.
        """
        if self.login_window is None:
            self.login_window = LoginWindow()
            self.login_window.student_authenticated.connect(self.handle_student_authenticated)
            self.login_window.change_window.connect(self.handle_window_change)

        # Determine which window is currently visible
        current_window = None
        if self.dashboard_window and self.dashboard_window.isVisible():
            current_window = self.dashboard_window
        elif self.admin_login_window and self.admin_login_window.isVisible():
            current_window = self.admin_login_window
        elif self.admin_dashboard_window and self.admin_dashboard_window.isVisible():
            current_window = self.admin_dashboard_window

        # Hide other windows that aren't transitioning
        if self.dashboard_window and self.dashboard_window != current_window:
            self.dashboard_window.hide()
        if self.admin_login_window and self.admin_login_window != current_window:
            self.admin_login_window.hide()
        if self.admin_dashboard_window and self.admin_dashboard_window != current_window:
            self.admin_dashboard_window.hide()

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(f"Transitioning from {current_window.__class__.__name__} to LoginWindow")
            # Ensure login window is ready for fullscreen
            self.login_window.showFullScreen()
            # Apply transition
            self.transition_manager.fade_out_in(current_window, self.login_window)
        else:
            # No transition needed, just show the window
            logger.info("Showing login window without transition")
            self.login_window.show()
            self.login_window.showFullScreen()  # Force fullscreen again to ensure it takes effect

    def show_dashboard_window(self, student=None):
        """
        Show the dashboard window.
        """
        self.current_student = student

        if self.dashboard_window is None:
            self.dashboard_window = DashboardWindow(student)
            self.dashboard_window.change_window.connect(self.handle_window_change)
            self.dashboard_window.consultation_requested.connect(self.handle_consultation_request)
        else:
            # Update student info if needed
            self.dashboard_window.student = student

        # Populate faculty grid
        faculties = self.faculty_controller.get_all_faculty()
        self.dashboard_window.populate_faculty_grid(faculties)

        # Determine which window is currently visible
        current_window = None
        if self.login_window and self.login_window.isVisible():
            current_window = self.login_window
        elif self.admin_login_window and self.admin_login_window.isVisible():
            current_window = self.admin_login_window
        elif self.admin_dashboard_window and self.admin_dashboard_window.isVisible():
            current_window = self.admin_dashboard_window

        # Hide other windows that aren't transitioning
        if self.login_window and self.login_window != current_window:
            self.login_window.hide()
        if self.admin_login_window and self.admin_login_window != current_window:
            self.admin_login_window.hide()
        if self.admin_dashboard_window and self.admin_dashboard_window != current_window:
            self.admin_dashboard_window.hide()

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(f"Transitioning from {current_window.__class__.__name__} to DashboardWindow")
            # Ensure dashboard window is ready for fullscreen
            self.dashboard_window.showFullScreen()
            # Apply transition
            self.transition_manager.fade_out_in(current_window, self.dashboard_window)
        else:
            # No transition needed, just show the window
            logger.info("Showing dashboard window without transition")
            self.dashboard_window.show()
            self.dashboard_window.showFullScreen()  # Force fullscreen to ensure it takes effect

        # Log that we've shown the dashboard
        logger.info(f"Showing dashboard for student: {student.name if student else 'Unknown'}")

    def show_admin_login_window(self):
        """
        Show the admin login window.
        """
        if self.admin_login_window is None:
            self.admin_login_window = AdminLoginWindow()
            self.admin_login_window.admin_authenticated.connect(self.handle_admin_authenticated)
            self.admin_login_window.change_window.connect(self.handle_window_change)

        # Determine which window is currently visible
        current_window = None
        if self.login_window and self.login_window.isVisible():
            current_window = self.login_window
        elif self.dashboard_window and self.dashboard_window.isVisible():
            current_window = self.dashboard_window
        elif self.admin_dashboard_window and self.admin_dashboard_window.isVisible():
            current_window = self.admin_dashboard_window

        # Hide other windows that aren't transitioning
        if self.login_window and self.login_window != current_window:
            self.login_window.hide()
        if self.dashboard_window and self.dashboard_window != current_window:
            self.dashboard_window.hide()
        if self.admin_dashboard_window and self.admin_dashboard_window != current_window:
            self.admin_dashboard_window.hide()

        # Define a callback for after the transition completes
        def after_transition():
            # Force the keyboard to show using both methods
            if self.keyboard_handler:
                logger.info("Forcing keyboard to show using keyboard handler")
                self.keyboard_handler.force_show_keyboard()

            # Also use direct keyboard integration
            if hasattr(self, 'direct_keyboard') and self.direct_keyboard:
                logger.info("Forcing keyboard to show using direct keyboard integration")
                self.direct_keyboard.show_keyboard()

                # Try again after a delay
                QTimer.singleShot(500, lambda: self.direct_keyboard.show_keyboard())
                QTimer.singleShot(1000, lambda: self.direct_keyboard.show_keyboard())

            # Focus the username input to trigger the keyboard
            QTimer.singleShot(300, lambda: self.admin_login_window.username_input.setFocus())

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(f"Transitioning from {current_window.__class__.__name__} to AdminLoginWindow")
            # Ensure admin login window is ready for fullscreen
            self.admin_login_window.showFullScreen()
            # Apply transition with callback
            self.transition_manager.fade_out_in(current_window, self.admin_login_window, after_transition)
        else:
            # No transition needed, just show the window
            logger.info("Showing admin login window without transition")
            self.admin_login_window.show()
            self.admin_login_window.showFullScreen()  # Force fullscreen
            # Call the callback directly
            after_transition()

    def show_admin_dashboard_window(self, admin=None):
        """
        Show the admin dashboard window.
        """
        if self.admin_dashboard_window is None:
            self.admin_dashboard_window = AdminDashboardWindow(admin)
            self.admin_dashboard_window.change_window.connect(self.handle_window_change)
            self.admin_dashboard_window.faculty_updated.connect(self.handle_faculty_updated)
            self.admin_dashboard_window.student_updated.connect(self.handle_student_updated)

        # Determine which window is currently visible
        current_window = None
        if self.login_window and self.login_window.isVisible():
            current_window = self.login_window
        elif self.dashboard_window and self.dashboard_window.isVisible():
            current_window = self.dashboard_window
        elif self.admin_login_window and self.admin_login_window.isVisible():
            current_window = self.admin_login_window

        # Hide other windows that aren't transitioning
        if self.login_window and self.login_window != current_window:
            self.login_window.hide()
        if self.dashboard_window and self.dashboard_window != current_window:
            self.dashboard_window.hide()
        if self.admin_login_window and self.admin_login_window != current_window:
            self.admin_login_window.hide()

        # Apply transition if there's a visible window to transition from
        if current_window:
            logger.info(f"Transitioning from {current_window.__class__.__name__} to AdminDashboardWindow")
            # Ensure admin dashboard window is ready for fullscreen
            self.admin_dashboard_window.showFullScreen()
            # Apply transition
            self.transition_manager.fade_out_in(current_window, self.admin_dashboard_window)
        else:
            # No transition needed, just show the window
            logger.info("Showing admin dashboard window without transition")
            self.admin_dashboard_window.show()
            self.admin_dashboard_window.showFullScreen()  # Force fullscreen

    def handle_rfid_scan(self, student, rfid_uid):
        """
        Handle RFID scan event.

        Args:
            student (Student): Verified student or None if not verified
            rfid_uid (str): RFID UID that was scanned
        """
        logger.info(f"Main.handle_rfid_scan called with student: {student}, rfid_uid: {rfid_uid}")

        # If login window is active and visible
        if self.login_window and self.login_window.isVisible():
            logger.info(f"Forwarding RFID scan to login window: {rfid_uid}")
            self.login_window.handle_rfid_read(rfid_uid, student)
        else:
            logger.info(f"Login window not visible, RFID scan not forwarded: {rfid_uid}")

    def handle_student_authenticated(self, student):
        """
        Handle student authentication event.

        Args:
            student (Student): Authenticated student
        """
        logger.info(f"Student authenticated: {student.name if student else 'Unknown'}")

        # Store the current student
        self.current_student = student

        # Show the dashboard window
        self.show_dashboard_window(student)

    def handle_admin_authenticated(self, credentials):
        """
        Handle admin authentication event.

        Args:
            credentials (tuple): Admin credentials (username, password)
        """
        # Unpack credentials from tuple
        username, password = credentials

        # Authenticate admin
        admin = self.admin_controller.authenticate(username, password)

        if admin:
            logger.info(f"Admin authenticated: {username}")
            # Create admin info to pass to dashboard
            admin_info = {
                'id': admin.id,
                'username': admin.username
            }
            self.show_admin_dashboard_window(admin_info)
        else:
            logger.warning(f"Admin authentication failed: {username}")
            if self.admin_login_window:
                self.admin_login_window.show_login_error("Invalid username or password")

    def handle_consultation_request(self, faculty, message, course_code):
        """
        Handle consultation request event.

        Args:
            faculty (object): Faculty object or dictionary
            message (str): Consultation message
            course_code (str): Course code
        """
        if not self.current_student:
            logger.error("Cannot request consultation: no student authenticated")
            return

        # Handle both Faculty object and dictionary
        if isinstance(faculty, dict):
            faculty_name = faculty['name']
            faculty_id = faculty['id']
        else:
            faculty_name = faculty.name
            faculty_id = faculty.id

        logger.info(f"Consultation requested with: {faculty_name}")

        # Create consultation request using the correct method
        consultation = self.consultation_controller.create_consultation(
            student_id=self.current_student.id,
            faculty_id=faculty_id,
            request_message=message,
            course_code=course_code
        )

        # Show success/error message
        if consultation:
            logger.info(f"Successfully created consultation request: {consultation.id}")
            # No need to show notification as DashboardWindow already shows a message box
        else:
            logger.error("Failed to create consultation request")
            # Show error message if the dashboard window has a show_notification method
            if hasattr(self.dashboard_window, 'show_notification'):
                self.dashboard_window.show_notification(
                    "Failed to send consultation request. Please try again.",
                    "error"
                )

    def handle_faculty_updated(self):
        """
        Handle faculty data updated event.
        """
        # Refresh faculty grid if dashboard is active
        if self.dashboard_window and self.dashboard_window.isVisible():
            faculties = self.faculty_controller.get_all_faculty()
            self.dashboard_window.populate_faculty_grid(faculties)

    def handle_student_updated(self):
        """
        Handle student data updated event.
        """
        logger.info("Student data updated, refreshing RFID service and controller")

        # Refresh RFID service and controller's student data
        try:
            # First, refresh the RFID service directly
            from central_system.services import get_rfid_service
            rfid_service = get_rfid_service()
            rfid_service.refresh_student_data()

            # Then refresh the RFID controller
            students = self.rfid_controller.refresh_student_data()

            # Log all students for debugging
            for student in students:
                logger.info(f"Student: ID={student.id}, Name={student.name}, RFID={student.rfid_uid}")

            # If login window is active, make sure it's ready for scanning
            if self.login_window and self.login_window.isVisible():
                logger.info("Login window is active, ensuring RFID scanning is active")
                self.login_window.start_rfid_scanning()

            logger.info("Student data refresh complete")
        except Exception as e:
            logger.error(f"Error refreshing student data: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def handle_window_change(self, window_name, data=None):
        """
        Handle window change event.

        Args:
            window_name (str): Name of window to show
            data (any): Optional data to pass to the window
        """
        if window_name == "login":
            self.show_login_window()
        elif window_name == "dashboard":
            self.show_dashboard_window(data)
        elif window_name == "admin_login":
            self.show_admin_login_window()
        elif window_name == "admin_dashboard":
            self.show_admin_dashboard_window(data)
        else:
            logger.warning(f"Unknown window: {window_name}")

if __name__ == "__main__":
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("consultease.log")
        ]
    )

    # Enable debug logging for RFID service
    rfid_logger = logging.getLogger('central_system.services.rfid_service')
    rfid_logger.setLevel(logging.DEBUG)

    # Set environment variables if needed
    import os

    # Configure RFID - enable simulation mode since we're on Raspberry Pi
    os.environ['RFID_SIMULATION_MODE'] = 'true'  # Enable if no RFID reader available

    # Set the theme to light as per the technical context document
    os.environ['CONSULTEASE_THEME'] = 'light'

    # Use SQLite for development and testing
    os.environ['DB_TYPE'] = 'sqlite'
    os.environ['DB_PATH'] = 'consultease.db'  # SQLite database file

    # Check if we're running in fullscreen mode
    fullscreen = os.environ.get('CONSULTEASE_FULLSCREEN', 'false').lower() == 'true'

    # Start the application
    app = ConsultEaseApp(fullscreen=fullscreen)
    sys.exit(app.run())
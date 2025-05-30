from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QGridLayout, QScrollArea, QFrame,
                               QLineEdit, QComboBox, QMessageBox, QTextEdit,
                               QSplitter, QApplication, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap

import os
import logging
from .base_window import BaseWindow
from .consultation_panel import ConsultationPanel
from ..utils.ui_components import FacultyCard
from ..ui.pooled_faculty_card import get_faculty_card_manager
from ..utils.ui_performance import (
    get_ui_batcher, get_widget_state_manager, SmartRefreshManager,
    batch_ui_update, timed_ui_update
)

# Set up logging
logger = logging.getLogger(__name__)



class ConsultationRequestForm(QFrame):
    """
    Form to request a consultation with a faculty member.
    """
    request_submitted = pyqtSignal(object, str, str)

    def __init__(self, faculty=None, parent=None):
        super().__init__(parent)
        self.faculty = faculty
        self.init_ui()

    def init_ui(self):
        """
        Initialize the consultation request form UI.
        """
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet('''
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 10px;
            }
        ''')

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Form title
        title_label = QLabel("Request Consultation")
        title_label.setStyleSheet("font-size: 20pt; font-weight: bold;")
        main_layout.addWidget(title_label)

        # Faculty information
        if self.faculty:
            # Create a layout for faculty info with image
            faculty_info_layout = QHBoxLayout()

            # Faculty image
            image_label = QLabel()
            image_label.setFixedSize(60, 60)
            image_label.setStyleSheet("border: 1px solid #ddd; border-radius: 30px; background-color: white;")
            image_label.setScaledContents(True)

            # Try to load faculty image
            if hasattr(self.faculty, 'get_image_path') and self.faculty.image_path:
                try:
                    image_path = self.faculty.get_image_path()
                    if image_path and os.path.exists(image_path):
                        pixmap = QPixmap(image_path)
                        if not pixmap.isNull():
                            image_label.setPixmap(pixmap)
                except Exception as e:
                    logger.error(f"Error loading faculty image in consultation form: {str(e)}")

            faculty_info_layout.addWidget(image_label)

            # Faculty text info
            faculty_info = QLabel(f"Faculty: {self.faculty.name} ({self.faculty.department})")
            faculty_info.setStyleSheet("font-size: 14pt;")
            faculty_info_layout.addWidget(faculty_info)
            faculty_info_layout.addStretch()

            main_layout.addLayout(faculty_info_layout)
        else:
            # If no faculty is selected, show a dropdown
            faculty_label = QLabel("Select Faculty:")
            faculty_label.setStyleSheet("font-size: 14pt;")
            main_layout.addWidget(faculty_label)

            self.faculty_combo = QComboBox()
            self.faculty_combo.setStyleSheet("font-size: 14pt; padding: 8px;")
            # Faculty options would be populated separately
            main_layout.addWidget(self.faculty_combo)

        # Course code input
        course_label = QLabel("Course Code (optional):")
        course_label.setStyleSheet("font-size: 14pt;")
        main_layout.addWidget(course_label)

        self.course_input = QLineEdit()
        self.course_input.setStyleSheet("font-size: 14pt; padding: 8px;")
        main_layout.addWidget(self.course_input)

        # Message input
        message_label = QLabel("Consultation Details:")
        message_label.setStyleSheet("font-size: 14pt;")
        main_layout.addWidget(message_label)

        self.message_input = QTextEdit()
        self.message_input.setStyleSheet("font-size: 14pt; padding: 8px;")
        self.message_input.setMinimumHeight(150)
        main_layout.addWidget(self.message_input)

        # Submit button
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet('''
            QPushButton {
                background-color: #f44336;
                min-width: 120px;
            }
        ''')
        cancel_button.clicked.connect(self.cancel_request)

        submit_button = QPushButton("Submit Request")
        submit_button.setStyleSheet('''
            QPushButton {
                background-color: #4caf50;
                min-width: 120px;
            }
        ''')
        submit_button.clicked.connect(self.submit_request)

        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(submit_button)

        main_layout.addLayout(button_layout)

    def set_faculty(self, faculty):
        """
        Set the faculty for the consultation request.
        """
        self.faculty = faculty
        self.init_ui()

    def set_faculty_options(self, faculties):
        """
        Set the faculty options for the dropdown.
        Only show available faculty members.
        """
        if hasattr(self, 'faculty_combo'):
            self.faculty_combo.clear()
            available_count = 0

            for faculty in faculties:
                # Only add available faculty to the dropdown
                if hasattr(faculty, 'status') and faculty.status:
                    self.faculty_combo.addItem(f"{faculty.name} ({faculty.department})", faculty)
                    available_count += 1

            # Show a message if no faculty is available
            if available_count == 0:
                self.faculty_combo.addItem("No faculty members are currently available", None)

    def get_selected_faculty(self):
        """
        Get the selected faculty from the dropdown.
        """
        if hasattr(self, 'faculty_combo') and self.faculty_combo.count() > 0:
            return self.faculty_combo.currentData()
        return self.faculty

    def submit_request(self):
        """
        Handle the submission of the consultation request.
        """
        faculty = self.get_selected_faculty()
        if not faculty:
            QMessageBox.warning(self, "Consultation Request", "Please select a faculty member.")
            return

        # Check if faculty is available
        if hasattr(faculty, 'status') and not faculty.status:
            QMessageBox.warning(self, "Consultation Request",
                               f"Faculty {faculty.name} is currently unavailable. Please select an available faculty member.")
            return

        message = self.message_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Consultation Request", "Please enter consultation details.")
            return

        course_code = self.course_input.text().strip()

        # Emit signal with the request details
        self.request_submitted.emit(faculty, message, course_code)

    def cancel_request(self):
        """
        Cancel the consultation request.
        """
        self.message_input.clear()
        self.course_input.clear()
        self.setVisible(False)

class DashboardWindow(BaseWindow):
    """
    Main dashboard window with faculty availability display and consultation request functionality.
    """
    # Signal to handle consultation request
    consultation_requested = pyqtSignal(object, str, str)

    def __init__(self, student=None, parent=None):
        self.student = student
        super().__init__(parent)
        self.init_ui()

        # Set up smart refresh manager for optimized faculty status updates
        self.smart_refresh = SmartRefreshManager(base_interval=180000, max_interval=600000)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_faculty_status_timer)
        self.refresh_timer.start(180000)  # Start with 3 minutes

        # UI performance utilities
        self.ui_batcher = get_ui_batcher()
        self.widget_state_manager = get_widget_state_manager()

        # Faculty card manager for pooling
        self.faculty_card_manager = get_faculty_card_manager()

        # Track faculty data for efficient comparison
        self._last_faculty_hash = None

        # Loading state management
        self._is_loading = False
        self._loading_widget = None

        # Log student info for debugging
        if student:
            # Handle both student object and student data dictionary
            if isinstance(student, dict):
                student_id = student.get('id', 'Unknown')
                student_name = student.get('name', 'Unknown')
                student_rfid = student.get('rfid_uid', 'Unknown')
            else:
                # Legacy support for student objects
                student_id = getattr(student, 'id', 'Unknown')
                student_name = getattr(student, 'name', 'Unknown')
                student_rfid = getattr(student, 'rfid_uid', 'Unknown')
            logger.info(f"Dashboard initialized with student: ID={student_id}, Name={student_name}, RFID={student_rfid}")
        else:
            logger.warning("Dashboard initialized without student information")

    def init_ui(self):
        """
        Initialize the dashboard UI.
        """
        # Main layout with splitter
        main_layout = QVBoxLayout()

        # Header with welcome message and student info - improved styling
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        header_layout.setContentsMargins(20, 15, 20, 15)

        if self.student:
            # Handle both student object and student data dictionary
            if isinstance(self.student, dict):
                student_name = self.student.get('name', 'Student')
            else:
                # Legacy support for student objects
                student_name = getattr(self.student, 'name', 'Student')
            welcome_label = QLabel(f"Welcome, {student_name}")
        else:
            welcome_label = QLabel("Welcome to ConsultEase")

        # Enhanced header styling for consistency with admin dashboard
        welcome_label.setStyleSheet("""
            QLabel {
                font-size: 28pt;
                font-weight: bold;
                color: #2c3e50;
                padding: 15px 20px;
                background-color: #ecf0f1;
                border-radius: 10px;
                margin: 10px 0;
                min-height: 60px;
            }
        """)
        header_layout.addWidget(welcome_label)

        # Logout button - smaller size as per user preference
        logout_button = QPushButton("Logout")
        logout_button.setFixedSize(50, 22)  # Even smaller size
        logout_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border-radius: 3px;
                font-size: 8pt;  /* Smaller font */
                font-weight: bold;
                padding: 1px 2px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a82315;
            }
        """)
        logout_button.clicked.connect(self.logout)
        header_layout.addWidget(logout_button)

        main_layout.addLayout(header_layout)

        # Main content with faculty grid and consultation form
        content_splitter = QSplitter(Qt.Horizontal)

        # Get screen size to set proportional initial sizes
        screen_size = QApplication.desktop().screenGeometry()
        screen_width = screen_size.width()

        # Faculty availability grid
        faculty_widget = QWidget()
        faculty_layout = QVBoxLayout(faculty_widget)

        # Search and filter controls in a more touch-friendly layout
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        # Search input with icon and better styling
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 2px;
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(5, 0, 5, 0)
        search_layout.setSpacing(5)

        search_icon = QLabel()
        try:
            search_icon_pixmap = QPixmap("resources/icons/search.png")
            if not search_icon_pixmap.isNull():
                search_icon.setPixmap(search_icon_pixmap.scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except:
            # If icon not available, use text
            search_icon.setText("🔍")

        search_layout.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or department")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: none;
                padding: 12px 8px;
                font-size: 14pt;
                min-height: 44px;
                background-color: transparent;
            }
            QLineEdit:focus {
                background-color: #f8f9fa;
            }
        """)
        self.search_input.textChanged.connect(self.filter_faculty)
        search_layout.addWidget(self.search_input)

        filter_layout.addWidget(search_frame, 3)  # Give search more space

        # Filter dropdown with better styling
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 2px;
            }
        """)
        filter_inner_layout = QHBoxLayout(filter_frame)
        filter_inner_layout.setContentsMargins(5, 0, 5, 0)
        filter_inner_layout.setSpacing(5)

        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("font-size: 12pt;")
        filter_inner_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All", None)
        self.filter_combo.addItem("Available Only", True)
        self.filter_combo.addItem("Unavailable Only", False)
        self.filter_combo.setStyleSheet("""
            QComboBox {
                border: none;
                padding: 12px 8px;
                font-size: 14pt;
                min-height: 44px;
                background-color: transparent;
            }
            QComboBox:focus {
                background-color: #f8f9fa;
            }
            QComboBox::drop-down {
                width: 30px;
                border: none;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
        """)
        self.filter_combo.currentIndexChanged.connect(self.filter_faculty)
        filter_inner_layout.addWidget(self.filter_combo)

        filter_layout.addWidget(filter_frame, 2)  # Give filter less space

        faculty_layout.addLayout(filter_layout)

        # Faculty grid in a scroll area with improved spacing and alignment
        self.faculty_grid = QGridLayout()
        self.faculty_grid.setSpacing(15)  # Reduced spacing between cards for better use of space
        self.faculty_grid.setAlignment(Qt.AlignTop | Qt.AlignHCenter)  # Align to top and center horizontally
        self.faculty_grid.setContentsMargins(10, 10, 10, 10)  # Reduced margins around the grid

        # Create a scroll area for the faculty grid
        faculty_scroll = QScrollArea()
        faculty_scroll.setWidgetResizable(True)
        faculty_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        faculty_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        faculty_scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 12px;
                background: #f0f0f0;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Create a container widget for the faculty grid
        faculty_scroll_content = QWidget()
        faculty_scroll_content.setLayout(self.faculty_grid)
        faculty_scroll_content.setStyleSheet("background-color: transparent;")

        # Set the scroll area widget
        faculty_scroll.setWidget(faculty_scroll_content)

        # Ensure scroll area starts at the top
        faculty_scroll.verticalScrollBar().setValue(0)

        # Store the scroll area for later reference
        self.faculty_scroll = faculty_scroll

        faculty_layout.addWidget(faculty_scroll)

        # Consultation panel with request form and history
        self.consultation_panel = ConsultationPanel(self.student)
        self.consultation_panel.consultation_requested.connect(self.handle_consultation_request)
        self.consultation_panel.consultation_cancelled.connect(self.handle_consultation_cancel)

        # Add widgets to splitter
        content_splitter.addWidget(faculty_widget)
        content_splitter.addWidget(self.consultation_panel)

        # Set splitter sizes proportionally to screen width
        content_splitter.setSizes([int(screen_width * 0.6), int(screen_width * 0.4)])

        # Save splitter state when it changes
        content_splitter.splitterMoved.connect(self.save_splitter_state)

        # Store the splitter for later reference
        self.content_splitter = content_splitter

        # Try to restore previous splitter state
        self.restore_splitter_state()

        # Add the splitter to the main layout
        main_layout.addWidget(content_splitter)

        # Schedule a scroll to top after the UI is fully loaded
        QTimer.singleShot(100, self._scroll_faculty_to_top)

        # Set the main layout to a widget and make it the central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def populate_faculty_grid_safe(self, faculty_data_list):
        """
        Populate the faculty grid with safe faculty data (no SQLAlchemy objects).
        This method avoids DetachedInstanceError by working with plain dictionaries.

        Args:
            faculty_data_list (list): List of faculty data dictionaries
        """
        # Log faculty data for debugging
        logger.info(f"Populating faculty grid with {len(faculty_data_list) if faculty_data_list else 0} faculty members (safe mode)")

        # Temporarily disable updates to reduce flickering and improve performance
        self.setUpdatesEnabled(False)

        try:
            # Clear existing grid efficiently using pooled cards
            self._clear_faculty_grid_pooled()

            # Handle empty faculty list
            if not faculty_data_list:
                logger.info("No faculty members found - showing empty state message")
                self._show_empty_faculty_message()
                return

            # Calculate optimal number of columns based on screen width
            screen_width = QApplication.desktop().screenGeometry().width()
            card_width = 280  # Updated to match the improved FacultyCard width
            spacing = 15
            grid_container_width = self.faculty_grid.parentWidget().width()
            if grid_container_width <= 0:
                grid_container_width = int(screen_width * 0.6)
            grid_container_width -= 30  # Account for margins
            max_cols = max(1, int(grid_container_width / (card_width + spacing)))
            if screen_width < 800:
                max_cols = 1

            # Add faculty cards to grid with centering containers
            row, col = 0, 0
            containers = []

            logger.info(f"Creating faculty cards for {len(faculty_data_list)} faculty members")

            for faculty_data in faculty_data_list:
                try:
                    # Create a container widget to center the card
                    container = QWidget()
                    container.setStyleSheet("background-color: transparent;")
                    container_layout = QHBoxLayout(container)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                    container_layout.setAlignment(Qt.AlignCenter)

                    # Convert to format expected by FacultyCard
                    card_data = {
                        'id': faculty_data['id'],
                        'name': faculty_data['name'],
                        'department': faculty_data['department'],
                        'available': faculty_data['status'] or faculty_data.get('always_available', False),
                        'status': 'Available' if (faculty_data['status'] or faculty_data.get('always_available', False)) else 'Unavailable',
                        'email': faculty_data.get('email', ''),
                        'room': faculty_data.get('room', None)
                    }

                    logger.debug(f"Creating card for faculty {faculty_data['name']}: available={card_data['available']}, status={card_data['status']}")

                    # Get pooled faculty card
                    card = self.faculty_card_manager.get_faculty_card(
                        card_data,
                        consultation_callback=lambda f_data=faculty_data: self.show_consultation_form_safe(f_data)
                    )

                    # Connect consultation signal if it exists
                    if hasattr(card, 'consultation_requested'):
                        card.consultation_requested.connect(lambda f_data=faculty_data: self.show_consultation_form_safe(f_data))

                    # Add card to container
                    container_layout.addWidget(card)

                    # Store container for batch processing
                    containers.append((container, row, col))

                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1

                    logger.debug(f"Successfully created card for faculty {faculty_data['name']}")

                except Exception as e:
                    logger.error(f"Error creating faculty card for {faculty_data.get('name', 'Unknown')}: {e}")
                    continue

            # Now add all containers to the grid at once
            for container, r, c in containers:
                self.faculty_grid.addWidget(container, r, c)

            # Log successful population
            logger.info(f"Successfully populated faculty grid with {len(containers)} faculty cards")

        finally:
            # Re-enable updates after all changes are made
            self.setUpdatesEnabled(True)

    def show_consultation_form_safe(self, faculty_data):
        """
        Show consultation form using safe faculty data dictionary.

        Args:
            faculty_data (dict): Faculty data dictionary
        """
        try:
            # Create a mock faculty object for compatibility
            class MockFaculty:
                def __init__(self, data):
                    self.id = data['id']
                    self.name = data['name']
                    self.department = data['department']
                    self.status = data['status']
                    self.email = data.get('email', '')
                    self.room = data.get('room', None)

            mock_faculty = MockFaculty(faculty_data)
            self.show_consultation_form(mock_faculty)
        except Exception as e:
            logger.error(f"Error showing consultation form for faculty {faculty_data.get('name', 'Unknown')}: {e}")

    def _extract_safe_faculty_data(self, faculty_data_list):
        """
        Extract relevant data from safe faculty data for comparison.

        Args:
            faculty_data_list (list): List of faculty data dictionaries

        Returns:
            str: Hash of faculty data for efficient comparison
        """
        import hashlib
        # Create a string representation of all relevant faculty data
        data_str = ""
        for f_data in sorted(faculty_data_list, key=lambda x: x['id']):  # Sort for consistent hashing
            data_str += f"{f_data['id']}:{f_data['name']}:{f_data['status']}:{f_data.get('department', '')};"

        # Return hash for efficient comparison
        return hashlib.md5(data_str.encode()).hexdigest()

    def populate_faculty_grid(self, faculties):
        """
        Populate the faculty grid with faculty cards.
        Optimized for performance with batch processing and reduced UI updates.

        Args:
            faculties (list): List of faculty objects
        """
        # Log faculty data for debugging
        logger.info(f"Populating faculty grid with {len(faculties) if faculties else 0} faculty members")
        if faculties:
            for faculty in faculties:
                try:
                    # Access attributes safely to avoid DetachedInstanceError
                    faculty_name = faculty.name
                    faculty_status = faculty.status
                    faculty_always_available = getattr(faculty, 'always_available', False)
                    logger.debug(f"Faculty: {faculty_name}, Status: {faculty_status}, Always Available: {faculty_always_available}")
                except Exception as e:
                    logger.warning(f"Error accessing faculty attributes: {e}")
                    continue

        # Temporarily disable updates to reduce flickering and improve performance
        self.setUpdatesEnabled(False)

        try:
            # Clear existing grid efficiently using pooled cards
            self._clear_faculty_grid_pooled()

            # Handle empty faculty list
            if not faculties:
                logger.info("No faculty members found - showing empty state message")
                self._show_empty_faculty_message()
                return

            # Calculate optimal number of columns based on screen width
            screen_width = QApplication.desktop().screenGeometry().width()

            # Fixed card width (matches the width set in FacultyCard)
            card_width = 280  # Updated to match the improved FacultyCard width

            # Grid spacing (matches the spacing set in faculty_grid)
            spacing = 15

            # Get the actual width of the faculty grid container
            grid_container_width = self.faculty_grid.parentWidget().width()
            if grid_container_width <= 0:  # If not yet available, estimate based on screen
                grid_container_width = int(screen_width * 0.6)  # 60% of screen for faculty grid

            # Account for grid margins
            grid_container_width -= 30  # 15px left + 15px right margin

            # Calculate how many cards can fit in a row, accounting for spacing
            max_cols = max(1, int(grid_container_width / (card_width + spacing)))

            # Adjust for very small screens
            if screen_width < 800:
                max_cols = 1  # Force single column on very small screens

            # Add faculty cards to grid with centering containers
            row, col = 0, 0

            # Create all widgets first before adding to layout (batch processing)
            containers = []

            logger.info(f"Creating faculty cards for {len(faculties)} faculty members")

            for faculty in faculties:
                try:
                    # Create a container widget to center the card
                    container = QWidget()
                    container.setStyleSheet("background-color: transparent;")
                    container_layout = QHBoxLayout(container)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                    container_layout.setAlignment(Qt.AlignCenter)

                    # Convert faculty object to dictionary format expected by FacultyCard
                    # Access all attributes at once to avoid DetachedInstanceError
                    faculty_id = faculty.id
                    faculty_name = faculty.name
                    faculty_department = faculty.department
                    faculty_status = faculty.status
                    faculty_always_available = getattr(faculty, 'always_available', False)
                    faculty_email = getattr(faculty, 'email', '')
                    faculty_room = getattr(faculty, 'room', None)

                    faculty_data = {
                        'id': faculty_id,
                        'name': faculty_name,
                        'department': faculty_department,
                        'available': faculty_status or faculty_always_available,  # Show if available OR always available
                        'status': 'Available' if (faculty_status or faculty_always_available) else 'Unavailable',
                        'email': faculty_email,
                        'room': faculty_room
                    }

                    logger.debug(f"Creating card for faculty {faculty.name}: available={faculty_data['available']}, status={faculty_data['status']}")

                    # Get pooled faculty card
                    card = self.faculty_card_manager.get_faculty_card(
                        faculty_data,
                        consultation_callback=lambda f=faculty: self.show_consultation_form(f)
                    )

                    # Connect consultation signal if it exists
                    if hasattr(card, 'consultation_requested'):
                        card.consultation_requested.connect(lambda f=faculty: self.show_consultation_form(f))

                    # Add card to container
                    container_layout.addWidget(card)

                    # Store container for batch processing
                    containers.append((container, row, col))

                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1

                    logger.debug(f"Successfully created card for faculty {faculty.name}")

                except Exception as e:
                    logger.error(f"Error creating faculty card for {faculty.name}: {e}")
                    continue

            # Now add all containers to the grid at once
            for container, r, c in containers:
                self.faculty_grid.addWidget(container, r, c)

            # Log successful population
            logger.info(f"Successfully populated faculty grid with {len(containers)} faculty cards")

        finally:
            # Re-enable updates after all changes are made
            self.setUpdatesEnabled(True)

    def _show_empty_faculty_message(self):
        """
        Show a message when no faculty members are available.
        """
        logger.info("Showing empty faculty message")

        # Create a message widget
        message_widget = QWidget()
        message_widget.setMinimumHeight(300)  # Ensure it's visible
        message_layout = QVBoxLayout(message_widget)
        message_layout.setAlignment(Qt.AlignCenter)
        message_layout.setSpacing(20)

        # Title
        title_label = QLabel("No Faculty Members Available")
        title_label.setObjectName("empty_state_title")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel#empty_state_title {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                margin: 20px;
                padding: 20px;
            }
        """)
        message_layout.addWidget(title_label)

        # Description
        desc_label = QLabel("Faculty members need to be added through the admin dashboard.\nOnce added, they will appear here when available for consultation.\n\nPlease contact your administrator to add faculty members.")
        desc_label.setObjectName("empty_state_desc")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            QLabel#empty_state_desc {
                font-size: 18px;
                color: #7f8c8d;
                margin: 10px 20px;
                padding: 20px;
                line-height: 1.6;
                background-color: #f8f9fa;
                border-radius: 10px;
                border: 2px solid #e9ecef;
            }
        """)
        message_layout.addWidget(desc_label)

        # Add some spacing
        message_layout.addStretch()

        # Add the message widget to the grid - span all columns
        self.faculty_grid.addWidget(message_widget, 0, 0, 1, self.faculty_grid.columnCount() if self.faculty_grid.columnCount() > 0 else 1)

    def _show_loading_indicator(self):
        """
        Show a loading indicator while faculty data is being fetched.
        """
        if self._is_loading:
            return  # Already showing loading indicator

        self._is_loading = True
        logger.debug("Showing loading indicator")

        # Create loading widget
        loading_widget = QWidget()
        loading_widget.setMinimumHeight(200)
        loading_layout = QVBoxLayout(loading_widget)
        loading_layout.setAlignment(Qt.AlignCenter)
        loading_layout.setSpacing(15)

        # Loading animation (simple text-based)
        loading_label = QLabel("Loading Faculty Information...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #3498db;
                padding: 20px;
            }
        """)
        loading_layout.addWidget(loading_label)

        # Progress indicator
        progress_label = QLabel("Please wait while we fetch the latest faculty data...")
        progress_label.setAlignment(Qt.AlignCenter)
        progress_label.setWordWrap(True)
        progress_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #7f8c8d;
                padding: 10px;
            }
        """)
        loading_layout.addWidget(progress_label)

        # Store reference and add to grid
        self._loading_widget = loading_widget
        self.faculty_grid.addWidget(loading_widget, 0, 0, 1, 1)

    def _hide_loading_indicator(self):
        """
        Hide the loading indicator.
        """
        if not self._is_loading or not self._loading_widget:
            return

        logger.debug("Hiding loading indicator")

        # Remove loading widget from grid
        self.faculty_grid.removeWidget(self._loading_widget)
        self._loading_widget.deleteLater()
        self._loading_widget = None
        self._is_loading = False

    def _show_error_message(self, error_text):
        """
        Show an error message in the faculty grid.

        Args:
            error_text (str): Error message to display
        """
        logger.info(f"Showing error message: {error_text}")

        # Clear existing grid first
        self._clear_faculty_grid_pooled()

        # Create error widget
        error_widget = QWidget()
        error_widget.setMinimumHeight(250)
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignCenter)
        error_layout.setSpacing(15)

        # Error title
        error_title = QLabel("⚠️ Error Loading Faculty Data")
        error_title.setAlignment(Qt.AlignCenter)
        error_title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #e74c3c;
                padding: 15px;
            }
        """)
        error_layout.addWidget(error_title)

        # Error message
        error_message = QLabel(error_text)
        error_message.setAlignment(Qt.AlignCenter)
        error_message.setWordWrap(True)
        error_message.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #7f8c8d;
                padding: 10px 20px;
                background-color: #fdf2f2;
                border: 2px solid #f5c6cb;
                border-radius: 8px;
                margin: 10px;
            }
        """)
        error_layout.addWidget(error_message)

        # Retry instruction
        retry_label = QLabel("The system will automatically retry in a few moments.\nIf the problem persists, please contact your administrator.")
        retry_label.setAlignment(Qt.AlignCenter)
        retry_label.setWordWrap(True)
        retry_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #95a5a6;
                padding: 10px;
                font-style: italic;
            }
        """)
        error_layout.addWidget(retry_label)

        # Add to grid
        self.faculty_grid.addWidget(error_widget, 0, 0, 1, 1)

    def filter_faculty(self):
        """
        Filter faculty grid based on search text and filter selection.
        Uses a debounce mechanism to prevent excessive updates.
        """
        # Cancel any pending filter operation
        if hasattr(self, '_filter_timer') and self._filter_timer.isActive():
            self._filter_timer.stop()

        # Create a new timer for debouncing
        if not hasattr(self, '_filter_timer'):
            self._filter_timer = QTimer(self)
            self._filter_timer.setSingleShot(True)
            self._filter_timer.timeout.connect(self._perform_filter)

        # Start the timer - will trigger _perform_filter after 300ms
        self._filter_timer.start(300)

    def _perform_filter(self):
        """
        Actually perform the faculty filtering after debounce delay.
        """
        try:
            # Import faculty controller
            from ..controllers import FacultyController

            # Get search text and filter value
            search_text = self.search_input.text().strip()
            filter_available = self.filter_combo.currentData()

            # Get faculty controller
            faculty_controller = FacultyController()

            # Get filtered faculty list
            faculties = faculty_controller.get_all_faculty(
                filter_available=filter_available,
                search_term=search_text
            )

            # Update the grid
            self.populate_faculty_grid(faculties)

            # Ensure scroll area starts at the top
            if hasattr(self, 'faculty_scroll') and self.faculty_scroll:
                self.faculty_scroll.verticalScrollBar().setValue(0)

            # Update current faculty data hash for future comparisons
            self._last_faculty_hash = self._extract_faculty_data(faculties)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error filtering faculty: {str(e)}")
            self.show_notification("Error filtering faculty list", "error")

    def _refresh_faculty_status_timer(self):
        """
        Timer-triggered refresh method that calls the main refresh method.
        This separates timer-based refreshes from manual/MQTT-based refreshes.
        """
        try:
            self.refresh_faculty_status()
        except Exception as e:
            logger.error(f"Error in timer-triggered faculty status refresh: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def refresh_faculty_status(self):
        """
        Refresh the faculty status from the server with optimizations to reduce loading indicators.
        Implements adaptive refresh rate based on activity.
        """
        try:
            # Store current scroll position to restore it later
            current_scroll_position = 0
            if hasattr(self, 'faculty_scroll') and self.faculty_scroll:
                current_scroll_position = self.faculty_scroll.verticalScrollBar().value()

            # Show loading indicator for initial load or significant delays
            if not hasattr(self, '_last_faculty_hash') or self._last_faculty_hash is None:
                self._show_loading_indicator()

            # Import faculty controller
            from ..controllers import FacultyController

            # Get current filter settings
            search_text = self.search_input.text().strip()
            filter_available = self.filter_combo.currentData()

            # Get faculty controller
            faculty_controller = FacultyController()

            # Get updated faculty list with current filters
            faculties = faculty_controller.get_all_faculty(
                filter_available=filter_available,
                search_term=search_text
            )

            # Use smart refresh manager for adaptive refresh rates
            faculty_hash = self._extract_faculty_data(faculties)
            new_interval = self.smart_refresh.update_refresh_rate(faculty_hash)

            # Update timer interval if it changed
            if new_interval != self.refresh_timer.interval():
                self.refresh_timer.setInterval(new_interval)
                logger.debug(f"Adjusted refresh interval to {new_interval/1000} seconds")

            # Check if data has changed
            if self._last_faculty_hash == faculty_hash:
                logger.debug("No faculty status changes detected, skipping UI update")
                return

            # Store the new faculty data hash
            self._last_faculty_hash = faculty_hash

            # Hide loading indicator before updating grid
            self._hide_loading_indicator()

            # Update the grid only if there are changes or this is the first load
            self.populate_faculty_grid(faculties)

            # Restore previous scroll position instead of always scrolling to top
            if hasattr(self, 'faculty_scroll') and self.faculty_scroll:
                self.faculty_scroll.verticalScrollBar().setValue(current_scroll_position)

            # Also refresh consultation history if student is logged in, but less frequently
            import time

            # Initialize last refresh time if not set
            if self.student and not hasattr(self, '_last_history_refresh'):
                self._last_history_refresh = time.time()

            current_time = time.time()
            # Only refresh history every 3 minutes (180 seconds) - increased from 2 minutes
            if self.student and (current_time - getattr(self, '_last_history_refresh', 0) > 180):
                self.consultation_panel.refresh_history()
                self._last_history_refresh = current_time

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error refreshing faculty status: {str(e)}")

            # Hide loading indicator on error
            self._hide_loading_indicator()

            # Show error message in faculty grid
            self._show_error_message(f"Error loading faculty data: {str(e)}")

            # Only show notification for serious errors, not for every refresh issue
            if "Connection refused" in str(e) or "Database error" in str(e):
                self.show_notification("Error refreshing faculty status", "error")

            # Reset consecutive no-change counter on errors to ensure we don't slow down too much
            if hasattr(self, '_consecutive_no_changes'):
                self._consecutive_no_changes = 0

    def _extract_faculty_data(self, faculties):
        """
        Extract relevant data from faculty objects for comparison.

        Args:
            faculties (list): List of faculty objects

        Returns:
            str: Hash of faculty data for efficient comparison
        """
        import hashlib
        # Create a string representation of all relevant faculty data
        data_str = ""
        for f in sorted(faculties, key=lambda x: x.id):  # Sort for consistent hashing
            try:
                # Access attributes safely to avoid DetachedInstanceError
                faculty_id = f.id
                faculty_name = f.name
                faculty_status = f.status
                faculty_department = getattr(f, 'department', '')
                data_str += f"{faculty_id}:{faculty_name}:{faculty_status}:{faculty_department};"
            except Exception as e:
                logger.warning(f"Error accessing faculty attributes for hashing: {e}")
                # Use a fallback representation
                data_str += f"error:{e};"

        # Return hash for efficient comparison
        return hashlib.md5(data_str.encode()).hexdigest()

    def _compare_faculty_data(self, old_hash, new_faculties):
        """
        Compare old and new faculty data to detect changes using hash comparison.

        Args:
            old_hash (str): Previous faculty data hash
            new_faculties (list): New faculty objects

        Returns:
            bool: True if data is the same, False if there are changes
        """
        if old_hash is None:
            return False  # First time, consider as changed

        # Extract hash from new faculty objects
        new_hash = self._extract_faculty_data(new_faculties)

        return old_hash == new_hash

    def show_consultation_form(self, faculty):
        """
        Show the consultation request form for a specific faculty.

        Args:
            faculty (object or dict): Faculty object or faculty data dictionary
        """
        # Handle both Faculty objects and faculty data dictionaries
        if isinstance(faculty, dict):
            faculty_id = faculty.get('id')
            faculty_name = faculty.get('name')
            faculty_status = faculty.get('status')
            faculty_department = faculty.get('department', '')
            faculty_email = faculty.get('email', '')
        else:
            # Handle Faculty object (with potential DetachedInstanceError protection)
            try:
                faculty_id = faculty.id
                faculty_name = faculty.name
                faculty_status = faculty.status
                faculty_department = getattr(faculty, 'department', '')
                faculty_email = getattr(faculty, 'email', '')
            except Exception as e:
                logger.error(f"Error accessing faculty object attributes: {e}")
                self.show_notification("Error accessing faculty information.", "error")
                return

        # Check if faculty is available
        if not faculty_status:
            self.show_notification(
                f"Faculty {faculty_name} is currently unavailable for consultation.",
                "error"
            )
            return

        # Also populate the dropdown with all available faculty
        try:
            from ..controllers import FacultyController
            faculty_controller = FacultyController()
            available_faculty = faculty_controller.get_all_faculty(filter_available=True)

            # Create a safe faculty data dictionary for the consultation panel
            safe_faculty_data = {
                'id': faculty_id,
                'name': faculty_name,
                'status': faculty_status,
                'department': faculty_department,
                'email': faculty_email
            }

            # Set the faculty and faculty options in the consultation panel
            self.consultation_panel.set_faculty(safe_faculty_data)
            self.consultation_panel.set_faculty_options(available_faculty)
        except Exception as e:
            logger.error(f"Error loading available faculty for consultation form: {str(e)}")

    def handle_consultation_request(self, faculty, message, course_code):
        """
        Handle consultation request submission.

        Args:
            faculty (object or dict): Faculty object or faculty data dictionary
            message (str): Consultation request message
            course_code (str): Optional course code
        """
        try:
            # Handle both Faculty objects and faculty data dictionaries
            if isinstance(faculty, dict):
                faculty_id = faculty.get('id')
                faculty_name = faculty.get('name')
            else:
                # Handle Faculty object (with potential DetachedInstanceError protection)
                try:
                    faculty_id = faculty.id
                    faculty_name = faculty.name
                except Exception as e:
                    logger.error(f"Error accessing faculty object attributes: {e}")
                    QMessageBox.warning(
                        self,
                        "Consultation Request",
                        "Error accessing faculty information."
                    )
                    return

            # Import consultation controller
            from ..controllers import ConsultationController

            # Get consultation controller
            consultation_controller = ConsultationController()

            # Create consultation
            if self.student:
                # Get student ID from either object or dictionary
                if isinstance(self.student, dict):
                    student_id = self.student.get('id')
                else:
                    # Legacy support for student objects
                    student_id = getattr(self.student, 'id', None)

                if not student_id:
                    logger.error("Cannot create consultation: student ID not available")
                    QMessageBox.warning(
                        self,
                        "Consultation Request",
                        "Unable to submit consultation request. Student information is incomplete."
                    )
                    return

                consultation = consultation_controller.create_consultation(
                    student_id=student_id,
                    faculty_id=faculty_id,
                    request_message=message,
                    course_code=course_code
                )

                if consultation:
                    # Show confirmation
                    QMessageBox.information(
                        self,
                        "Consultation Request",
                        f"Your consultation request with {faculty_name} has been submitted."
                    )

                    # Refresh the consultation history
                    self.consultation_panel.refresh_history()
                else:
                    QMessageBox.warning(
                        self,
                        "Consultation Request",
                        f"Failed to submit consultation request. Please try again."
                    )
            else:
                # No student logged in
                QMessageBox.warning(
                    self,
                    "Consultation Request",
                    "You must be logged in to submit a consultation request."
                )
        except Exception as e:
            logger.error(f"Error creating consultation: {str(e)}")
            QMessageBox.warning(
                self,
                "Consultation Request",
                f"An error occurred while submitting your consultation request: {str(e)}"
            )

    def handle_consultation_cancel(self, consultation_id):
        """
        Handle consultation cancellation.

        Args:
            consultation_id (int): ID of the consultation to cancel
        """
        try:
            # Import consultation controller
            from ..controllers import ConsultationController

            # Get consultation controller
            consultation_controller = ConsultationController()

            # Cancel consultation
            consultation = consultation_controller.cancel_consultation(consultation_id)

            if consultation:
                # Show confirmation
                QMessageBox.information(
                    self,
                    "Consultation Cancelled",
                    f"Your consultation request has been cancelled."
                )

                # Refresh the consultation history
                self.consultation_panel.refresh_history()
            else:
                QMessageBox.warning(
                    self,
                    "Consultation Cancellation",
                    f"Failed to cancel consultation request. Please try again."
                )
        except Exception as e:
            logger.error(f"Error cancelling consultation: {str(e)}")
            QMessageBox.warning(
                self,
                "Consultation Cancellation",
                f"An error occurred while cancelling your consultation request: {str(e)}"
            )

    def save_splitter_state(self):
        """
        Save the current splitter state to settings.
        """
        try:
            # Import QSettings
            from PyQt5.QtCore import QSettings

            # Create settings object
            settings = QSettings("ConsultEase", "Dashboard")

            # Save splitter state
            settings.setValue("splitter_state", self.content_splitter.saveState())
            settings.setValue("splitter_sizes", self.content_splitter.sizes())

            logger.debug("Saved splitter state")
        except Exception as e:
            logger.error(f"Error saving splitter state: {e}")

    def restore_splitter_state(self):
        """
        Restore the splitter state from settings.
        """
        try:
            # Import QSettings
            from PyQt5.QtCore import QSettings

            # Create settings object
            settings = QSettings("ConsultEase", "Dashboard")

            # Restore splitter state if available
            if settings.contains("splitter_state"):
                state = settings.value("splitter_state")
                if state:
                    self.content_splitter.restoreState(state)
                    logger.debug("Restored splitter state")

            # Fallback to sizes if state restoration fails
            elif settings.contains("splitter_sizes"):
                sizes = settings.value("splitter_sizes")
                if sizes:
                    self.content_splitter.setSizes(sizes)
                    logger.debug("Restored splitter sizes")
        except Exception as e:
            logger.error(f"Error restoring splitter state: {e}")
            # Use default sizes as fallback
            screen_width = QApplication.desktop().screenGeometry().width()
            self.content_splitter.setSizes([int(screen_width * 0.6), int(screen_width * 0.4)])

    def logout(self):
        """
        Handle logout button click.
        """
        # Save splitter state before logout
        self.save_splitter_state()

        self.change_window.emit("login", None)

    def show_notification(self, message, message_type="info"):
        """
        Show a notification message to the user using the standardized notification system.

        Args:
            message (str): Message to display
            message_type (str): Type of message ('success', 'error', 'warning', or 'info')
        """
        try:
            # Import notification manager
            from ..utils.notification import NotificationManager

            # Map message types
            type_mapping = {
                "success": NotificationManager.SUCCESS,
                "error": NotificationManager.ERROR,
                "warning": NotificationManager.WARNING,
                "info": NotificationManager.INFO
            }

            # Get standardized message type
            std_type = type_mapping.get(message_type.lower(), NotificationManager.INFO)

            # Show notification using the manager
            title = message_type.capitalize()
            if message_type == "error":
                title = "Error"
            elif message_type == "success":
                title = "Success"
            elif message_type == "warning":
                title = "Warning"
            else:
                title = "Information"

            NotificationManager.show_message(self, title, message, std_type)

        except ImportError:
            # Fallback to basic message boxes if notification manager is not available
            logger.warning("NotificationManager not available, using basic message boxes")
            if message_type == "success":
                QMessageBox.information(self, "Success", message)
            elif message_type == "error":
                QMessageBox.warning(self, "Error", message)
            elif message_type == "warning":
                QMessageBox.warning(self, "Warning", message)
            else:
                QMessageBox.information(self, "Information", message)

    def _scroll_faculty_to_top(self):
        """
        Scroll the faculty grid to the top.
        This is called after the UI is fully loaded to ensure faculty cards are visible.
        """
        if hasattr(self, 'faculty_scroll') and self.faculty_scroll:
            self.faculty_scroll.verticalScrollBar().setValue(0)
            logger.debug("Scrolled faculty grid to top")

    def simulate_consultation_request(self):
        """
        Simulate a consultation request for testing purposes.
        This method finds an available faculty and shows the consultation form.
        """
        try:
            # Import faculty controller
            from ..controllers import FacultyController

            # Get faculty controller
            faculty_controller = FacultyController()

            # Get available faculty
            available_faculty = faculty_controller.get_all_faculty(filter_available=True)

            if available_faculty:
                # Use the first available faculty
                faculty = available_faculty[0]
                logger.info(f"Simulating consultation request with faculty: {faculty.name}")

                # Show the consultation form
                self.show_consultation_form(faculty)
            else:
                logger.warning("No available faculty found for simulation")
                self.show_notification("No available faculty found. Please try again later.", "error")
        except Exception as e:
            logger.error(f"Error simulating consultation request: {str(e)}")
            self.show_notification("Error simulating consultation request", "error")

    def _clear_faculty_grid_pooled(self):
        """
        Clear the faculty grid efficiently using pooled cards.
        """
        # Return all active faculty cards to the pool
        self.faculty_card_manager.clear_all_cards()

        # Clear the grid layout
        while self.faculty_grid.count():
            item = self.faculty_grid.takeAt(0)
            if item.widget():
                # Don't delete the widget, it's managed by the pool
                item.widget().setParent(None)

    def showEvent(self, event):
        """
        Handle window show event to trigger initial faculty data loading.
        """
        # Call parent showEvent first
        super().showEvent(event)

        # Load faculty data immediately when the window is first shown
        # Only do this if we haven't loaded faculty data yet
        if not hasattr(self, '_initial_load_done') or not self._initial_load_done:
            logger.info("Dashboard window shown - triggering initial faculty data load")
            self._initial_load_done = True

            # Schedule the initial faculty load after a short delay to ensure UI is ready
            QTimer.singleShot(100, self._perform_initial_faculty_load)

    def _perform_initial_faculty_load(self):
        """
        Perform the initial faculty data load when the dashboard is first shown.
        """
        try:
            logger.info("Performing initial faculty data load")

            # Import faculty controller
            from ..controllers import FacultyController

            # Get faculty controller
            faculty_controller = FacultyController()

            # Get all faculty members
            faculties = faculty_controller.get_all_faculty()

            logger.info(f"Initial load: Found {len(faculties)} faculty members")

            # Debug: Log each faculty member
            for faculty in faculties:
                logger.debug(f"Faculty found: {faculty.name} (ID: {faculty.id}, Status: {faculty.status}, Department: {faculty.department})")

            # Populate the faculty grid
            self.populate_faculty_grid(faculties)

            # Also update the consultation panel with faculty options
            if hasattr(self, 'consultation_panel'):
                self.consultation_panel.set_faculty_options(faculties)
                logger.debug("Updated consultation panel with faculty options")

            # Ensure scroll area starts at the top
            if hasattr(self, 'faculty_scroll') and self.faculty_scroll:
                self.faculty_scroll.verticalScrollBar().setValue(0)
                logger.debug("Reset scroll position to top")

            logger.info("Initial faculty data load completed successfully")

        except Exception as e:
            logger.error(f"Error during initial faculty data load: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Show error message in the faculty grid
            self._show_error_message(f"Error loading faculty data: {str(e)}")

    def refresh_faculty_status_realtime(self, faculty_data):
        """
        Refresh faculty status in real-time based on MQTT updates.

        Args:
            faculty_data (dict): Faculty status data from MQTT
        """
        try:
            faculty_id = faculty_data.get('id')
            faculty_name = faculty_data.get('name')
            faculty_status = faculty_data.get('status')

            logger.info(f"🔄 Refreshing faculty status - ID: {faculty_id}, Name: {faculty_name}, Status: {faculty_status}")

            # Update the faculty card if it exists
            if hasattr(self, 'faculty_card_manager') and self.faculty_card_manager:
                # Use the manager's update method which handles the dictionary correctly
                logger.info(f"📱 Updating faculty card for {faculty_name}")
                self.faculty_card_manager.update_faculty_status(faculty_id, faculty_status)

            # Also refresh the entire faculty grid to ensure consistency
            # This is a lightweight operation that ensures all cards are up-to-date
            QTimer.singleShot(100, self._refresh_faculty_grid_lightweight)

        except Exception as e:
            logger.error(f"Error refreshing faculty status: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    def _refresh_faculty_grid_lightweight(self):
        """
        Lightweight refresh of faculty grid that only updates status without recreating cards.
        """
        try:
            # Import faculty controller
            from ..controllers import FacultyController

            # Get faculty controller
            faculty_controller = FacultyController()

            # Get current faculty data
            faculties = faculty_controller.get_all_faculty()

            # Update existing cards with new status
            if hasattr(self, 'faculty_card_manager') and self.faculty_card_manager:
                for faculty in faculties:
                    # Use the manager's update method which handles the dictionary correctly
                    self.faculty_card_manager.update_faculty_status(faculty.id, faculty.status)

            logger.debug("Lightweight faculty grid refresh completed")

        except Exception as e:
            logger.error(f"Error in lightweight faculty grid refresh: {e}")

    def closeEvent(self, event):
        """
        Handle window close event with proper cleanup.
        """
        # Clean up faculty card manager
        if hasattr(self, 'faculty_card_manager'):
            self.faculty_card_manager.clear_all_cards()

        # Save splitter state before closing
        self.save_splitter_state()

        # Call parent close event
        super().closeEvent(event)
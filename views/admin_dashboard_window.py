from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
                               QHeaderView, QFrame, QDialog, QFormLayout, QLineEdit,
                               QDialogButtonBox, QMessageBox, QComboBox, QCheckBox,
                               QGroupBox, QFileDialog, QTextEdit, QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QFont, QTextCursor

import os
import logging
from .base_window import BaseWindow
from ..controllers import FacultyController
from ..models import Student, get_db
from ..services import get_rfid_service

# Set up logging
logger = logging.getLogger(__name__)

class AdminDashboardWindow(BaseWindow):
    """
    Admin dashboard window with tabs for managing faculty, students, and system settings.
    """
    # Signals
    faculty_updated = pyqtSignal()
    student_updated = pyqtSignal()
    change_window = pyqtSignal(str, object)  # Add explicit signal if it's missing

    def __init__(self, admin=None, parent=None):
        self.admin = admin
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """
        Initialize the UI components.
        """
        # Set window title
        self.setWindowTitle("ConsultEase - Admin Dashboard")

        # Main layout
        main_layout = QVBoxLayout()

        # Header with admin info and logout button
        header_layout = QHBoxLayout()

        # Admin welcome label
        admin_username = "Admin"
        if self.admin:
            # Handle admin as either an object or a dictionary
            if isinstance(self.admin, dict):
                admin_username = self.admin.get('username', 'Admin')
            else:
                admin_username = getattr(self.admin, 'username', 'Admin')

        admin_label = QLabel(f"Admin Dashboard - Logged in as: {admin_username}")
        admin_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(admin_label)

        # Logout button
        logout_button = QPushButton("Logout")
        logout_button.setFixedWidth(100)
        logout_button.clicked.connect(self.logout)
        header_layout.addWidget(logout_button)

        main_layout.addLayout(header_layout)

        # Tab widget for different admin functions
        self.tab_widget = QTabWidget()

        # Create tabs
        self.faculty_tab = FacultyManagementTab()
        self.faculty_tab.faculty_updated.connect(self.handle_faculty_updated)

        self.student_tab = StudentManagementTab()
        self.student_tab.student_updated.connect(self.handle_student_updated)

        self.system_tab = SystemMaintenanceTab()

        # Add tabs to tab widget
        self.tab_widget.addTab(self.faculty_tab, "Faculty Management")
        self.tab_widget.addTab(self.student_tab, "Student Management")
        self.tab_widget.addTab(self.system_tab, "System Maintenance")

        main_layout.addWidget(self.tab_widget)

        # Set the central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def logout(self):
        """
        Handle logout button click.
        """
        logger.info("Admin logging out")

        # Clean up any resources
        try:
            # Clean up student tab resources
            if hasattr(self, 'student_tab') and self.student_tab:
                if hasattr(self.student_tab, 'cleanup'):
                    self.student_tab.cleanup()
                elif hasattr(self.student_tab, 'scan_dialog') and self.student_tab.scan_dialog:
                    self.student_tab.scan_dialog.close()
        except Exception as e:
            logger.error(f"Error during admin logout cleanup: {str(e)}")

        # Hide this window
        self.hide()

        # Emit signal to change to the main login window (RFID scan) instead of admin login
        logger.info("Redirecting to main login window (RFID scan) after admin logout")
        self.change_window.emit("login", None)

    def handle_faculty_updated(self):
        """
        Handle faculty updated signal.
        """
        # Refresh faculty tab data
        self.faculty_tab.refresh_data()
        # Forward signal
        self.faculty_updated.emit()

    def handle_student_updated(self):
        """
        Handle student updated signal.
        """
        # Refresh student tab data
        self.student_tab.refresh_data()
        # Forward signal
        self.student_updated.emit()

class FacultyManagementTab(QWidget):
    """
    Tab for managing faculty members.
    """
    # Signals
    faculty_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.faculty_controller = FacultyController()
        self.init_ui()

    def init_ui(self):
        """
        Initialize the UI components.
        """
        # Main layout
        main_layout = QVBoxLayout()

        # Buttons for actions
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add Faculty")
        self.add_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.add_button.clicked.connect(self.add_faculty)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Faculty")
        self.edit_button.clicked.connect(self.edit_faculty)
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Faculty")
        self.delete_button.setStyleSheet("background-color: #F44336; color: white;")
        self.delete_button.clicked.connect(self.delete_faculty)
        button_layout.addWidget(self.delete_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        button_layout.addWidget(self.refresh_button)

        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        # Faculty table
        self.faculty_table = QTableWidget()
        self.faculty_table.setColumnCount(7)
        self.faculty_table.setHorizontalHeaderLabels(["ID", "Name", "Department", "Email", "BLE ID", "Status", "Always Available"])
        self.faculty_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.faculty_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.faculty_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.faculty_table.setSelectionMode(QTableWidget.SingleSelection)

        main_layout.addWidget(self.faculty_table)

        # Set the layout
        self.setLayout(main_layout)

        # Initial data load
        self.refresh_data()

    def refresh_data(self):
        """
        Refresh the faculty data in the table.
        """
        # Clear the table
        self.faculty_table.setRowCount(0)

        try:
            # Get all faculty from the controller
            faculties = self.faculty_controller.get_all_faculty()

            for faculty in faculties:
                row_position = self.faculty_table.rowCount()
                self.faculty_table.insertRow(row_position)

                # Add data to each column
                self.faculty_table.setItem(row_position, 0, QTableWidgetItem(str(faculty.id)))
                self.faculty_table.setItem(row_position, 1, QTableWidgetItem(faculty.name))
                self.faculty_table.setItem(row_position, 2, QTableWidgetItem(faculty.department))
                self.faculty_table.setItem(row_position, 3, QTableWidgetItem(faculty.email))
                self.faculty_table.setItem(row_position, 4, QTableWidgetItem(faculty.ble_id))

                status_item = QTableWidgetItem("Available" if faculty.status else "Unavailable")
                if faculty.status:
                    status_item.setBackground(Qt.green)
                else:
                    status_item.setBackground(Qt.red)
                self.faculty_table.setItem(row_position, 5, status_item)

                # Add always available status
                always_available_item = QTableWidgetItem("Yes" if faculty.always_available else "No")
                if faculty.always_available:
                    always_available_item.setBackground(Qt.green)
                self.faculty_table.setItem(row_position, 6, always_available_item)

        except Exception as e:
            logger.error(f"Error refreshing faculty data: {str(e)}")
            QMessageBox.warning(self, "Data Error", f"Failed to refresh faculty data: {str(e)}")

    def add_faculty(self):
        """
        Show dialog to add a new faculty member.
        """
        dialog = FacultyDialog()
        if dialog.exec_() == QDialog.Accepted:
            try:
                name = dialog.name_input.text().strip()
                department = dialog.department_input.text().strip()
                email = dialog.email_input.text().strip()
                ble_id = dialog.ble_id_input.text().strip()
                image_path = dialog.image_path

                # Process image if provided
                if image_path:
                    # Get the filename only
                    import os
                    import shutil

                    # Create images directory if it doesn't exist
                    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    images_dir = os.path.join(base_dir, 'images', 'faculty')
                    if not os.path.exists(images_dir):
                        os.makedirs(images_dir)

                    # Generate a unique filename
                    filename = f"{email.split('@')[0]}_{os.path.basename(image_path)}"
                    dest_path = os.path.join(images_dir, filename)

                    # Copy the image file
                    shutil.copy2(image_path, dest_path)

                    # Store the relative path
                    image_path = filename
                else:
                    image_path = None

                # Get always available flag
                always_available = dialog.always_available_checkbox.isChecked()

                # Add faculty using controller
                faculty = self.faculty_controller.add_faculty(name, department, email, ble_id, image_path, always_available)

                if faculty:
                    QMessageBox.information(self, "Add Faculty", f"Faculty '{name}' added successfully.")
                    self.refresh_data()
                    self.faculty_updated.emit()
                else:
                    QMessageBox.warning(self, "Add Faculty", "Failed to add faculty. This email or BLE ID may already be in use.")

            except Exception as e:
                logger.error(f"Error adding faculty: {str(e)}")
                QMessageBox.warning(self, "Add Faculty", f"Error adding faculty: {str(e)}")

    def edit_faculty(self):
        """
        Show dialog to edit the selected faculty member.
        """
        # Get selected row
        selected_rows = self.faculty_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Edit Faculty", "Please select a faculty member to edit.")
            return

        # Get faculty ID from the first column
        row_index = selected_rows[0].row()
        faculty_id = int(self.faculty_table.item(row_index, 0).text())

        # Get faculty from controller
        faculty = self.faculty_controller.get_faculty_by_id(faculty_id)
        if not faculty:
            QMessageBox.warning(self, "Edit Faculty", f"Faculty with ID {faculty_id} not found.")
            return

        # Create and populate dialog
        dialog = FacultyDialog(faculty_id=faculty_id)
        dialog.name_input.setText(faculty.name)
        dialog.department_input.setText(faculty.department)
        dialog.email_input.setText(faculty.email)
        dialog.ble_id_input.setText(faculty.ble_id)
        dialog.always_available_checkbox.setChecked(faculty.always_available)

        # Set image path if available
        if faculty.image_path:
            dialog.image_path = faculty.get_image_path()
            dialog.image_path_input.setText(faculty.image_path)

        if dialog.exec_() == QDialog.Accepted:
            try:
                name = dialog.name_input.text().strip()
                department = dialog.department_input.text().strip()
                email = dialog.email_input.text().strip()
                ble_id = dialog.ble_id_input.text().strip()
                image_path = dialog.image_path

                # Process image if provided and different from current
                if image_path and (not faculty.image_path or image_path != faculty.get_image_path()):
                    # Get the filename only
                    import os
                    import shutil

                    # Create images directory if it doesn't exist
                    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    images_dir = os.path.join(base_dir, 'images', 'faculty')
                    if not os.path.exists(images_dir):
                        os.makedirs(images_dir)

                    # Generate a unique filename
                    filename = f"{email.split('@')[0]}_{os.path.basename(image_path)}"
                    dest_path = os.path.join(images_dir, filename)

                    # Copy the image file
                    shutil.copy2(image_path, dest_path)

                    # Store the relative path
                    image_path = filename
                elif faculty.image_path:
                    # Keep the existing image path
                    image_path = faculty.image_path

                # Get always available flag
                always_available = dialog.always_available_checkbox.isChecked()

                # Update faculty using controller
                updated_faculty = self.faculty_controller.update_faculty(
                    faculty_id, name, department, email, ble_id, image_path, always_available
                )

                if updated_faculty:
                    QMessageBox.information(self, "Edit Faculty", f"Faculty '{name}' updated successfully.")
                    self.refresh_data()
                    self.faculty_updated.emit()
                else:
                    QMessageBox.warning(self, "Edit Faculty", "Failed to update faculty. This email or BLE ID may already be in use.")

            except Exception as e:
                logger.error(f"Error updating faculty: {str(e)}")
                QMessageBox.warning(self, "Edit Faculty", f"Error updating faculty: {str(e)}")

    def delete_faculty(self):
        """
        Delete the selected faculty member.
        """
        # Get selected row
        selected_rows = self.faculty_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Delete Faculty", "Please select a faculty member to delete.")
            return

        # Get faculty ID and name from the table
        row_index = selected_rows[0].row()
        faculty_id = int(self.faculty_table.item(row_index, 0).text())
        faculty_name = self.faculty_table.item(row_index, 1).text()

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Faculty",
            f"Are you sure you want to delete faculty member '{faculty_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Delete faculty using controller
                success = self.faculty_controller.delete_faculty(faculty_id)

                if success:
                    QMessageBox.information(self, "Delete Faculty", f"Faculty '{faculty_name}' deleted successfully.")
                    self.refresh_data()
                    self.faculty_updated.emit()
                else:
                    QMessageBox.warning(self, "Delete Faculty", f"Failed to delete faculty '{faculty_name}'.")

            except Exception as e:
                logger.error(f"Error deleting faculty: {str(e)}")
                QMessageBox.warning(self, "Delete Faculty", f"Error deleting faculty: {str(e)}")

class FacultyDialog(QDialog):
    """
    Dialog for adding or editing faculty members.
    """
    def __init__(self, faculty_id=None, parent=None):
        super().__init__(parent)
        self.faculty_id = faculty_id
        self.image_path = None
        self.init_ui()

    def init_ui(self):
        """
        Initialize the UI components.
        """
        # Set title based on mode (add or edit)
        self.setWindowTitle("Edit Faculty" if self.faculty_id else "Add Faculty")

        # Main layout
        layout = QVBoxLayout()

        # Form layout for inputs
        form_layout = QFormLayout()

        # Name input
        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)

        # Department input
        self.department_input = QLineEdit()
        form_layout.addRow("Department:", self.department_input)

        # Email input
        self.email_input = QLineEdit()
        form_layout.addRow("Email:", self.email_input)

        # BLE ID input
        self.ble_id_input = QLineEdit()
        form_layout.addRow("BLE ID:", self.ble_id_input)

        # Always available checkbox
        self.always_available_checkbox = QCheckBox("Always Available (BLE Always On)")
        self.always_available_checkbox.setToolTip("If checked, this faculty member will always be shown as available, regardless of BLE status")
        form_layout.addRow("", self.always_available_checkbox)

        # Image selection
        image_layout = QHBoxLayout()
        self.image_path_input = QLineEdit()
        self.image_path_input.setReadOnly(True)
        self.image_path_input.setPlaceholderText("No image selected")

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_image)

        image_layout.addWidget(self.image_path_input)
        image_layout.addWidget(browse_button)

        form_layout.addRow("Profile Image:", image_layout)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

        # If editing, the faculty data will be populated by the caller
        # No need to fetch data here as it's passed in when the dialog is created

    def browse_image(self):
        """
        Open file dialog to select a faculty image.
        """
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.image_path = selected_files[0]
                self.image_path_input.setText(self.image_path)

    def accept(self):
        """
        Validate and accept the dialog.
        """
        # Validate inputs
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a name.")
            return

        if not self.department_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a department.")
            return

        if not self.email_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter an email.")
            return

        if not self.ble_id_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a BLE ID.")
            return

        # If all validations pass, accept the dialog
        super().accept()

class StudentManagementTab(QWidget):
    """
    Tab for managing students.
    """
    # Signals
    student_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

        # Initialize RFID service
        self.rfid_service = get_rfid_service()

        # For scanning RFID cards
        self.scanning_for_rfid = False
        self.scan_dialog = None
        self.rfid_callback = None

    def __del__(self):
        """
        Destructor to ensure cleanup happens when the object is destroyed.
        """
        try:
            self.cleanup()
        except Exception as e:
            # Can't use logger here as it might be None during shutdown
            print(f"Error in StudentManagementTab destructor: {str(e)}")

    def init_ui(self):
        """
        Initialize the UI components.
        """
        # Main layout
        main_layout = QVBoxLayout()

        # Buttons for actions
        button_layout = QHBoxLayout()

        self.add_button = QPushButton("Add Student")
        self.add_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.add_button.clicked.connect(self.add_student)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Student")
        self.edit_button.clicked.connect(self.edit_student)
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Student")
        self.delete_button.setStyleSheet("background-color: #F44336; color: white;")
        self.delete_button.clicked.connect(self.delete_student)
        button_layout.addWidget(self.delete_button)

        self.scan_button = QPushButton("Scan RFID")
        self.scan_button.clicked.connect(self.scan_rfid)
        button_layout.addWidget(self.scan_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_data)
        button_layout.addWidget(self.refresh_button)

        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        # Student table
        self.student_table = QTableWidget()
        self.student_table.setColumnCount(4)
        self.student_table.setHorizontalHeaderLabels(["ID", "Name", "Department", "RFID UID"])
        self.student_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.student_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.student_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.student_table.setSelectionMode(QTableWidget.SingleSelection)

        main_layout.addWidget(self.student_table)

        # Set the layout
        self.setLayout(main_layout)

        # Initial data load
        self.refresh_data()

    def cleanup(self):
        """
        Clean up resources when the tab is closed or the window is closed.
        """
        logger.info("Cleaning up StudentManagementTab resources")

        # Close any open scan dialog
        if self.scan_dialog and self.scan_dialog.isVisible():
            self.scan_dialog.close()
            self.scan_dialog = None

        # Unregister any RFID callbacks
        if self.rfid_callback:
            try:
                self.rfid_service.unregister_callback(self.rfid_callback)
                self.rfid_callback = None
                logger.info("Unregistered RFID callback")
            except Exception as e:
                logger.error(f"Error unregistering RFID callback: {str(e)}")

    def refresh_data(self):
        """
        Refresh the student data in the table.
        """
        # Clear the table
        self.student_table.setRowCount(0)

        try:
            # Get students from database
            db = get_db()
            students = db.query(Student).all()

            for student in students:
                row_position = self.student_table.rowCount()
                self.student_table.insertRow(row_position)

                # Add data to each column
                self.student_table.setItem(row_position, 0, QTableWidgetItem(str(student.id)))
                self.student_table.setItem(row_position, 1, QTableWidgetItem(student.name))
                self.student_table.setItem(row_position, 2, QTableWidgetItem(student.department))
                self.student_table.setItem(row_position, 3, QTableWidgetItem(student.rfid_uid))

        except Exception as e:
            logger.error(f"Error refreshing student data: {str(e)}")
            QMessageBox.warning(self, "Data Error", f"Failed to refresh student data: {str(e)}")

    def add_student(self):
        """
        Show dialog to add a new student.
        """
        # Import all necessary modules at the top level
        import traceback

        dialog = StudentDialog()
        if dialog.exec_() == QDialog.Accepted:
            try:
                name = dialog.name_input.text().strip()
                department = dialog.department_input.text().strip()
                rfid_uid = dialog.rfid_uid

                logger.info(f"Adding new student: Name={name}, Department={department}, RFID={rfid_uid}")

                # Use a separate function to handle the database operations
                self._add_student_to_database(name, department, rfid_uid)

            except Exception as e:
                logger.error(f"Error adding student: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                QMessageBox.warning(self, "Add Student", f"Error adding student: {str(e)}")

    def _add_student_to_database(self, name, department, rfid_uid):
        """
        Add a student to the database and refresh the RFID service.

        Args:
            name (str): Student name
            department (str): Student department
            rfid_uid (str): Student RFID UID
        """
        # Import all necessary modules
        import traceback
        from ..models import Student, get_db
        from ..services import get_rfid_service

        try:
            # Get a database connection
            db = get_db()

            # Check if RFID already exists
            existing = db.query(Student).filter(Student.rfid_uid == rfid_uid).first()
            if existing:
                QMessageBox.warning(self, "Add Student", f"A student with RFID {rfid_uid} already exists.")
                return

            # Create new student
            new_student = Student(
                name=name,
                department=department,
                rfid_uid=rfid_uid
            )

            # Add and commit
            db.add(new_student)
            db.commit()
            logger.info(f"Added student to database: {name} with RFID: {rfid_uid}")

            # Get the RFID service and refresh it
            rfid_service = get_rfid_service()
            rfid_service.refresh_student_data()
            logger.info(f"Refreshed RFID service after adding student: {name}")

            # Show success message
            QMessageBox.information(self, "Add Student", f"Student '{name}' added successfully.")

            # Refresh the UI and emit signal
            self.refresh_data()
            self.student_updated.emit()

            # Log all students for debugging
            try:
                # Use a new database connection to ensure we get fresh data
                fresh_db = get_db(force_new=True)
                all_students = fresh_db.query(Student).all()
                logger.info(f"Available students in database after adding: {len(all_students)}")
                for s in all_students:
                    logger.info(f"  - ID: {s.id}, Name: {s.name}, RFID: {s.rfid_uid}")
                fresh_db.close()
            except Exception as e:
                logger.error(f"Error logging students: {str(e)}")

        except Exception as e:
            logger.error(f"Error in _add_student_to_database: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.warning(self, "Add Student", f"Error adding student to database: {str(e)}")

    def edit_student(self):
        """
        Show dialog to edit the selected student.
        """
        # Import all necessary modules at the top level
        import traceback
        from ..models import Student, get_db

        # Get selected row
        selected_rows = self.student_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Edit Student", "Please select a student to edit.")
            return

        # Get student ID from the first column
        row_index = selected_rows[0].row()
        student_id = int(self.student_table.item(row_index, 0).text())

        try:
            # Get student from database
            db = get_db()
            student = db.query(Student).filter(Student.id == student_id).first()

            if not student:
                QMessageBox.warning(self, "Edit Student", f"Student with ID {student_id} not found.")
                return

            # Create and populate dialog
            dialog = StudentDialog(student_id=student_id)
            dialog.name_input.setText(student.name)
            dialog.department_input.setText(student.department)
            dialog.rfid_input.setText(student.rfid_uid)
            dialog.rfid_uid = student.rfid_uid

            if dialog.exec_() == QDialog.Accepted:
                name = dialog.name_input.text().strip()
                department = dialog.department_input.text().strip()
                rfid_uid = dialog.rfid_uid

                logger.info(f"Editing student: ID={student_id}, Name={name}, Department={department}, RFID={rfid_uid}")

                # Use a separate function to handle the database operations
                self._update_student_in_database(student_id, name, department, rfid_uid)

        except Exception as e:
            logger.error(f"Error editing student: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.warning(self, "Edit Student", f"Error editing student: {str(e)}")

    def _update_student_in_database(self, student_id, name, department, rfid_uid):
        """
        Update a student in the database and refresh the RFID service.

        Args:
            student_id (int): Student ID
            name (str): Student name
            department (str): Student department
            rfid_uid (str): Student RFID UID
        """
        # Import all necessary modules
        import traceback
        from ..models import Student, get_db
        from ..services import get_rfid_service

        try:
            # Get a database connection
            db = get_db()

            # Get the student
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                QMessageBox.warning(self, "Edit Student", f"Student with ID {student_id} not found.")
                return

            # Check if new RFID already exists (if changed)
            if rfid_uid != student.rfid_uid:
                existing = db.query(Student).filter(Student.rfid_uid == rfid_uid).first()
                if existing and existing.id != student_id:
                    QMessageBox.warning(self, "Edit Student", f"A student with RFID {rfid_uid} already exists.")
                    return

            # Update student
            student.name = name
            student.department = department
            student.rfid_uid = rfid_uid

            # Commit changes
            db.commit()
            logger.info(f"Updated student in database: ID={student_id}, Name={name}, RFID={rfid_uid}")

            # Get the RFID service and refresh it
            rfid_service = get_rfid_service()
            rfid_service.refresh_student_data()
            logger.info(f"Refreshed RFID service after updating student: {name}")

            # Show success message
            QMessageBox.information(self, "Edit Student", f"Student '{name}' updated successfully.")

            # Refresh the UI and emit signal
            self.refresh_data()
            self.student_updated.emit()

            # Log all students for debugging
            try:
                # Use a new database connection to ensure we get fresh data
                fresh_db = get_db(force_new=True)
                all_students = fresh_db.query(Student).all()
                logger.info(f"Available students in database after updating: {len(all_students)}")
                for s in all_students:
                    logger.info(f"  - ID: {s.id}, Name: {s.name}, RFID: {s.rfid_uid}")
                fresh_db.close()
            except Exception as e:
                logger.error(f"Error logging students: {str(e)}")

        except Exception as e:
            logger.error(f"Error in _update_student_in_database: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.warning(self, "Edit Student", f"Error updating student in database: {str(e)}")

    def delete_student(self):
        """
        Delete the selected student.
        """
        # Import all necessary modules at the top level
        import traceback

        # Get selected row
        selected_rows = self.student_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Delete Student", "Please select a student to delete.")
            return

        # Get student ID and name from the table
        row_index = selected_rows[0].row()
        student_id = int(self.student_table.item(row_index, 0).text())
        student_name = self.student_table.item(row_index, 1).text()

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Student",
            f"Are you sure you want to delete student '{student_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                logger.info(f"Deleting student: ID={student_id}, Name={student_name}")

                # Use a separate function to handle the database operations
                self._delete_student_from_database(student_id, student_name)

            except Exception as e:
                logger.error(f"Error deleting student: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                QMessageBox.warning(self, "Delete Student", f"Error deleting student: {str(e)}")

    def _delete_student_from_database(self, student_id, student_name):
        """
        Delete a student from the database and refresh the RFID service.

        Args:
            student_id (int): Student ID
            student_name (str): Student name
        """
        # Import all necessary modules
        import traceback
        from ..models import Student, get_db
        from ..services import get_rfid_service

        try:
            # Get a database connection
            db = get_db()

            # Get the student
            student = db.query(Student).filter(Student.id == student_id).first()
            if not student:
                QMessageBox.warning(self, "Delete Student", f"Student with ID {student_id} not found.")
                return

            # Delete the student
            db.delete(student)
            db.commit()
            logger.info(f"Deleted student from database: ID={student_id}, Name={student_name}")

            # Get the RFID service and refresh it
            rfid_service = get_rfid_service()
            rfid_service.refresh_student_data()
            logger.info(f"Refreshed RFID service after deleting student: {student_name}")

            # Show success message
            QMessageBox.information(self, "Delete Student", f"Student '{student_name}' deleted successfully.")

            # Refresh the UI and emit signal
            self.refresh_data()
            self.student_updated.emit()

            # Log all students for debugging
            try:
                # Use a new database connection to ensure we get fresh data
                fresh_db = get_db(force_new=True)
                all_students = fresh_db.query(Student).all()
                logger.info(f"Available students in database after deletion: {len(all_students)}")
                for s in all_students:
                    logger.info(f"  - ID: {s.id}, Name: {s.name}, RFID: {s.rfid_uid}")
                fresh_db.close()
            except Exception as e:
                logger.error(f"Error logging students: {str(e)}")

        except Exception as e:
            logger.error(f"Error in _delete_student_from_database: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            QMessageBox.warning(self, "Delete Student", f"Error deleting student from database: {str(e)}")

    def scan_rfid(self):
        """
        Scan RFID card for student registration.
        """
        dialog = RFIDScanDialog(self.rfid_service)
        self.scan_dialog = dialog

        if dialog.exec_() == QDialog.Accepted:
            rfid_uid = dialog.get_rfid_uid()
            if rfid_uid:
                QMessageBox.information(self, "RFID Scan", f"RFID card scanned: {rfid_uid}")

                # Look up student by RFID
                try:
                    db = get_db()
                    student = db.query(Student).filter(Student.rfid_uid == rfid_uid).first()

                    if student:
                        # Select the student in the table
                        for row in range(self.student_table.rowCount()):
                            if self.student_table.item(row, 3).text() == rfid_uid:
                                self.student_table.selectRow(row)
                                QMessageBox.information(
                                    self,
                                    "Student Found",
                                    f"Student found: {student.name}\nDepartment: {student.department}"
                                )
                                break
                    else:
                        # No student with this RFID
                        reply = QMessageBox.question(
                            self,
                            "Add New Student",
                            f"No student found with RFID: {rfid_uid}\nWould you like to add a new student with this RFID?",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.Yes
                        )

                        if reply == QMessageBox.Yes:
                            # Pre-fill the RFID field in the student dialog
                            dialog = StudentDialog()
                            dialog.rfid_uid = rfid_uid
                            dialog.rfid_input.setText(rfid_uid)

                            if dialog.exec_() == QDialog.Accepted:
                                try:
                                    name = dialog.name_input.text().strip()
                                    department = dialog.department_input.text().strip()

                                    logger.info(f"Adding new student via RFID scan: Name={name}, Department={department}, RFID={rfid_uid}")

                                    # Use the existing method to add the student to the database
                                    self._add_student_to_database(name, department, rfid_uid)

                                except Exception as e:
                                    logger.error(f"Error adding student: {str(e)}")
                                    QMessageBox.warning(self, "Add Student", f"Error adding student: {str(e)}")

                except Exception as e:
                    logger.error(f"Error looking up student by RFID: {str(e)}")
                    QMessageBox.warning(self, "RFID Lookup Error", f"Error looking up student: {str(e)}")

class StudentDialog(QDialog):
    """
    Dialog for adding or editing students.
    """
    def __init__(self, student_id=None, parent=None):
        super().__init__(parent)
        self.student_id = student_id
        self.rfid_uid = ""
        self.rfid_service = get_rfid_service()

        # Track if we're currently scanning
        self.is_scanning = False

        # Store a reference to our scan callback
        self.scan_callback = None

        self.init_ui()

        # If we're in simulation mode, enable the simulate button
        self.simulation_mode = os.environ.get('RFID_SIMULATION_MODE', 'true').lower() == 'true'

    def init_ui(self):
        """
        Initialize the UI components.
        """
        # Set title based on mode (add or edit)
        self.setWindowTitle("Edit Student" if self.student_id else "Add Student")

        # Main layout
        layout = QVBoxLayout()

        # Form layout for inputs
        form_layout = QFormLayout()

        # Name input
        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)

        # Department input
        self.department_input = QLineEdit()
        form_layout.addRow("Department:", self.department_input)

        # RFID UID input and scan button
        rfid_layout = QHBoxLayout()
        self.rfid_input = QLineEdit()
        self.rfid_input.setReadOnly(True)
        rfid_layout.addWidget(self.rfid_input, 1)

        scan_button = QPushButton("Scan RFID")
        scan_button.clicked.connect(self.scan_rfid)
        rfid_layout.addWidget(scan_button)

        form_layout.addRow("RFID UID:", rfid_layout)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

        # If editing, the student data will be populated by the caller
        # No need to fetch data here as it's passed in when the dialog is created

    def scan_rfid(self):
        """
        Scan RFID card.
        """
        try:
            logger.info("StudentDialog: Starting RFID scan")

            # Create our own RFID scan handler to receive directly from the service
            def handle_scan(student=None, rfid_uid=None):
                if not rfid_uid:
                    return

                logger.info(f"StudentDialog: RFID scan received: {rfid_uid}")
                self.rfid_uid = rfid_uid
                self.rfid_input.setText(self.rfid_uid)

                # If this was a simulation, trigger the animation to stop
                if self.rfid_scan_dialog and self.rfid_scan_dialog.isVisible():
                    self.rfid_scan_dialog.handle_rfid_scan(student, rfid_uid)

            # Store the callback reference to prevent garbage collection
            self.scan_callback = handle_scan

            # Register our callback with the RFID service
            self.rfid_service.register_callback(self.scan_callback)
            self.is_scanning = True

            # Create and show the dialog
            self.rfid_scan_dialog = RFIDScanDialog(self.rfid_service)

            # Wait for the dialog to complete
            result = self.rfid_scan_dialog.exec_()

            # When the dialog completes, get the value
            if result == QDialog.Accepted:
                rfid_uid = self.rfid_scan_dialog.get_rfid_uid()
                if rfid_uid:
                    logger.info(f"StudentDialog: Dialog returned RFID: {rfid_uid}")
                    self.rfid_uid = rfid_uid
                    self.rfid_input.setText(self.rfid_uid)

            # Clean up our callback
            try:
                if self.scan_callback:
                    self.rfid_service.unregister_callback(self.scan_callback)
                    self.scan_callback = None
                self.is_scanning = False
            except Exception as e:
                logger.error(f"Error unregistering RFID callback: {str(e)}")

        except Exception as e:
            logger.error(f"Error in student RFID scan: {str(e)}")
            QMessageBox.warning(self, "RFID Scan Error", f"An error occurred while scanning: {str(e)}")

    def closeEvent(self, event):
        """Handle dialog close to clean up callback"""
        # Clean up our callback if we're still scanning
        if hasattr(self, 'scan_callback') and self.scan_callback and self.is_scanning:
            try:
                self.rfid_service.unregister_callback(self.scan_callback)
                self.scan_callback = None
                self.is_scanning = False
                logger.info("Unregistered RFID callback in StudentDialog closeEvent")
            except Exception as e:
                logger.error(f"Error unregistering RFID callback in closeEvent: {str(e)}")
        super().closeEvent(event)

    def accept(self):
        """
        Validate and accept the dialog.
        """
        # Validate inputs
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a name.")
            return

        if not self.department_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Please enter a department.")
            return

        if not self.rfid_uid:
            QMessageBox.warning(self, "Validation Error", "Please scan an RFID card.")
            return

        # If all validations pass, accept the dialog
        super().accept()

class RFIDScanDialog(QDialog):
    """
    Dialog for RFID card scanning.
    """
    def __init__(self, rfid_service=None, parent=None):
        super().__init__(parent)
        self.rfid_uid = ""
        self.rfid_service = rfid_service or get_rfid_service()

        # Track whether we've received a scan
        self.scan_received = False

        self.init_ui()

        # Add a direct callback reference to prevent garbage collection
        self.callback_fn = self.handle_rfid_scan

        # Register RFID callback - ensure we're using the instance method
        self.rfid_service.register_callback(self.callback_fn)

        # Start the scanning animation
        self.scanning_timer = QTimer(self)
        self.scanning_timer.timeout.connect(self.update_animation)
        self.scanning_timer.start(500)  # Update every 500ms

        # For development, add a simulate button
        if os.environ.get('RFID_SIMULATION_MODE', 'true').lower() == 'true':
            self.simulate_button = QPushButton("Simulate Scan")
            self.simulate_button.clicked.connect(self.simulate_scan)
            self.layout().addWidget(self.simulate_button, alignment=Qt.AlignCenter)

    def init_ui(self):
        """
        Initialize the UI components.
        """
        self.setWindowTitle("RFID Scan")
        self.setFixedSize(350, 350)  # Make dialog taller for manual input

        # Main layout
        layout = QVBoxLayout()

        # Instructions
        instruction_label = QLabel("Please scan the 13.56 MHz RFID card...")
        instruction_label.setAlignment(Qt.AlignCenter)
        instruction_label.setStyleSheet("font-size: 14pt;")
        layout.addWidget(instruction_label)

        # Animation label
        self.animation_label = QLabel("🔄")
        self.animation_label.setAlignment(Qt.AlignCenter)
        self.animation_label.setStyleSheet("font-size: 48pt; color: #4a86e8;")
        layout.addWidget(self.animation_label)

        # Status label
        self.status_label = QLabel("Scanning...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12pt; color: #4a86e8;")
        layout.addWidget(self.status_label)

        # Add manual input section
        manual_section = QGroupBox("Manual RFID Input")
        manual_layout = QVBoxLayout()

        manual_instructions = QLabel("If scanning doesn't work, enter the RFID manually:")
        manual_layout.addWidget(manual_instructions)

        self.manual_input = QLineEdit()
        self.manual_input.setPlaceholderText("Enter RFID UID manually")
        self.manual_input.returnPressed.connect(self.handle_manual_input)
        manual_layout.addWidget(self.manual_input)

        manual_submit = QPushButton("Submit Manual RFID")
        manual_submit.clicked.connect(self.handle_manual_input)
        manual_layout.addWidget(manual_submit)

        manual_section.setLayout(manual_layout)
        layout.addWidget(manual_section)

        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def handle_manual_input(self):
        """
        Handle manual RFID input.
        """
        uid = self.manual_input.text().strip().upper()
        if uid:
            logger.info(f"Manual RFID input: {uid}")
            self.manual_input.clear()
            self.handle_rfid_scan(None, uid)
        else:
            self.status_label.setText("Please enter a valid RFID UID")
            self.status_label.setStyleSheet("font-size: 12pt; color: #f44336;")
            QTimer.singleShot(2000, lambda: self.reset_status_label())

    def reset_status_label(self):
        """Reset the status label to its default state"""
        if not self.scan_received:  # Only reset if we haven't received a scan
            self.status_label.setText("Scanning...")
            self.status_label.setStyleSheet("font-size: 12pt; color: #4a86e8;")

    def update_animation(self):
        """
        Update the scanning animation.
        """
        if self.scan_received:  # Don't update if we've received a scan
            return

        animations = ["🔄", "🔁", "🔃", "🔂"]
        current_index = animations.index(self.animation_label.text()) if self.animation_label.text() in animations else 0
        next_index = (current_index + 1) % len(animations)
        self.animation_label.setText(animations[next_index])

    def handle_rfid_scan(self, student=None, rfid_uid=None):
        """
        Handle RFID scan event.
        """
        logger.info(f"RFIDScanDialog received scan: {rfid_uid}")

        # Ignore if no UID was provided or if we already received a scan
        if not rfid_uid or self.scan_received:
            logger.info(f"Ignoring scan - no UID or already received: {rfid_uid}")
            return

        self.scan_received = True
        self.rfid_uid = rfid_uid

        # Update UI
        self.scanning_timer.stop()
        self.animation_label.setText("✅")
        self.animation_label.setStyleSheet("font-size: 48pt; color: #4caf50;")
        self.status_label.setText(f"Card detected: {self.rfid_uid}")
        self.status_label.setStyleSheet("font-size: 12pt; color: #4caf50;")

        # If a student was found with this RFID, show a warning
        if student:
            QMessageBox.warning(
                self,
                "RFID Already Registered",
                f"This RFID card is already registered to student:\n{student.name}"
            )

        # Auto-accept after a delay
        QTimer.singleShot(1500, self.accept)

    def closeEvent(self, event):
        """Handle dialog close to clean up callback"""
        # Unregister callback to prevent memory leaks
        if hasattr(self, 'callback_fn') and self.callback_fn:
            try:
                self.rfid_service.unregister_callback(self.callback_fn)
                logger.info("Unregistered RFID callback in RFIDScanDialog closeEvent")
            except Exception as e:
                logger.error(f"Error unregistering RFID callback in closeEvent: {str(e)}")
        super().closeEvent(event)

    def reject(self):
        """Override reject to clean up callback"""
        # Unregister callback to prevent memory leaks
        if hasattr(self, 'callback_fn') and self.callback_fn:
            try:
                self.rfid_service.unregister_callback(self.callback_fn)
                logger.info("Unregistered RFID callback in RFIDScanDialog reject")
            except Exception as e:
                logger.error(f"Error unregistering RFID callback in reject: {str(e)}")
        super().reject()

    def accept(self):
        """Override accept to clean up callback"""
        # Unregister callback to prevent memory leaks
        if hasattr(self, 'callback_fn') and self.callback_fn:
            try:
                self.rfid_service.unregister_callback(self.callback_fn)
                logger.info("Unregistered RFID callback in RFIDScanDialog accept")
            except Exception as e:
                logger.error(f"Error unregistering RFID callback in accept: {str(e)}")
        super().accept()

    def simulate_scan(self):
        """
        Simulate a successful RFID scan.
        """
        try:
            # Disable the simulate button to prevent multiple clicks
            if hasattr(self, 'simulate_button'):
                self.simulate_button.setEnabled(False)

            # Only simulate if no real scan has occurred yet
            if not self.scan_received:
                logger.info("Simulating RFID scan from RFIDScanDialog")

                # Generate a random RFID number
                import random
                random_uid = ''.join(random.choices('0123456789ABCDEF', k=8))
                logger.info(f"Generated random RFID: {random_uid}")

                # Call the service's simulate method
                self.rfid_service.simulate_card_read(random_uid)

                logger.info(f"Simulation complete, RFID: {random_uid}")
        except Exception as e:
            logger.error(f"Error in RFID simulation: {str(e)}")
            self.status_label.setText(f"Simulation error: {str(e)}")
            # Re-enable the button if there was an error
            if hasattr(self, 'simulate_button'):
                self.simulate_button.setEnabled(True)

    def get_rfid_uid(self):
        """
        Get the scanned RFID UID.
        """
        return self.rfid_uid

class SystemMaintenanceTab(QWidget):
    """
    Tab for system maintenance tasks.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """
        Initialize the UI components.
        """
        # Main layout
        main_layout = QVBoxLayout()

        # Database section
        database_group = QGroupBox("Database Maintenance")
        database_layout = QVBoxLayout()

        # Backup/restore buttons
        backup_button = QPushButton("Backup Database")
        backup_button.clicked.connect(self.backup_database)
        database_layout.addWidget(backup_button)

        restore_button = QPushButton("Restore Database")
        restore_button.clicked.connect(self.restore_database)
        database_layout.addWidget(restore_button)

        database_group.setLayout(database_layout)
        main_layout.addWidget(database_group)

        # System logs section
        logs_group = QGroupBox("System Logs")
        logs_layout = QVBoxLayout()

        view_logs_button = QPushButton("View Logs")
        view_logs_button.clicked.connect(self.view_logs)
        logs_layout.addWidget(view_logs_button)

        logs_group.setLayout(logs_layout)
        main_layout.addWidget(logs_group)

        # System settings section
        settings_group = QGroupBox("System Settings")
        settings_layout = QFormLayout()

        # MQTT settings
        self.mqtt_host_input = QLineEdit(os.environ.get('MQTT_BROKER_HOST', 'localhost'))
        settings_layout.addRow("MQTT Broker Host:", self.mqtt_host_input)

        self.mqtt_port_input = QLineEdit(os.environ.get('MQTT_BROKER_PORT', '1883'))
        settings_layout.addRow("MQTT Broker Port:", self.mqtt_port_input)

        # Auto-start settings
        self.auto_start_checkbox = QCheckBox()
        self.auto_start_checkbox.setChecked(True)
        settings_layout.addRow("Auto-start on boot:", self.auto_start_checkbox)

        # Save button
        save_settings_button = QPushButton("Save Settings")
        save_settings_button.clicked.connect(self.save_settings)
        settings_layout.addRow("", save_settings_button)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # Set the layout
        self.setLayout(main_layout)

    def backup_database(self):
        """
        Backup the database to a file.
        """
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Database",
            os.path.expanduser("~/consultease_backup.db"),
            "Database Files (*.db *.sql)"
        )

        if file_path:
            try:
                # Get database type
                from ..models.base import DB_TYPE

                # Show progress dialog
                progress_dialog = QMessageBox(self)
                progress_dialog.setWindowTitle("Database Backup")
                progress_dialog.setText("Backing up database, please wait...")
                progress_dialog.setStandardButtons(QMessageBox.NoButton)
                progress_dialog.show()
                QApplication.processEvents()

                if DB_TYPE.lower() == 'sqlite':
                    # For SQLite, just copy the file
                    from ..models.base import DB_PATH
                    import shutil

                    # Create backup command for display
                    backup_cmd = f"Copy {DB_PATH} to {file_path}"

                    # Ask for confirmation
                    progress_dialog.close()
                    reply = QMessageBox.question(
                        self,
                        "Backup Database",
                        f"The system will backup the SQLite database:\n\n{backup_cmd}\n\nContinue?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )

                    if reply == QMessageBox.Yes:
                        progress_dialog.show()
                        QApplication.processEvents()

                        # Copy the SQLite database file
                        shutil.copy2(DB_PATH, file_path)
                        success = True
                    else:
                        success = False
                else:
                    # For PostgreSQL, use pg_dump
                    from ..models.base import DB_USER, DB_PASSWORD, DB_HOST, DB_NAME

                    # Create backup command
                    backup_cmd = f"pg_dump -U {DB_USER} -h {DB_HOST} -d {DB_NAME} -f {file_path}"

                    # Ask for confirmation
                    progress_dialog.close()
                    reply = QMessageBox.question(
                        self,
                        "Backup Database",
                        f"The system will execute the following command:\n\n{backup_cmd}\n\nContinue?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )

                    if reply == QMessageBox.Yes:
                        progress_dialog.show()
                        QApplication.processEvents()

                        # Execute the command
                        import subprocess
                        env = os.environ.copy()
                        env["PGPASSWORD"] = DB_PASSWORD
                        result = subprocess.run(
                            backup_cmd,
                            shell=True,
                            env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )

                        success = (result.returncode == 0)
                    else:
                        success = False

                # Close progress dialog
                progress_dialog.close()

                if success:
                    QMessageBox.information(self, "Backup Database", f"Database backup saved to:\n{file_path}")
                else:
                    if 'result' in locals() and hasattr(result, 'stderr'):
                        error_msg = result.stderr.decode('utf-8')
                        QMessageBox.critical(self, "Backup Error", f"Failed to backup database:\n{error_msg}")
                    else:
                        QMessageBox.critical(self, "Backup Error", "Backup operation was cancelled or failed.")

            except Exception as e:
                logger.error(f"Error backing up database: {str(e)}")
                QMessageBox.critical(self, "Backup Error", f"Error backing up database: {str(e)}")

    def restore_database(self):
        """
        Restore the database from a file.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Database",
            os.path.expanduser("~"),
            "Database Files (*.db *.sql)"
        )

        if file_path:
            # Confirm restore
            reply = QMessageBox.warning(
                self,
                "Restore Database",
                "Restoring the database will overwrite all current data. Are you sure you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    # Get database type
                    from ..models.base import DB_TYPE

                    # Show progress dialog
                    progress_dialog = QMessageBox(self)
                    progress_dialog.setWindowTitle("Database Restore")
                    progress_dialog.setText("Restoring database, please wait...")
                    progress_dialog.setStandardButtons(QMessageBox.NoButton)
                    progress_dialog.show()
                    QApplication.processEvents()

                    success = False

                    if DB_TYPE.lower() == 'sqlite':
                        # For SQLite, just copy the file
                        from ..models.base import DB_PATH
                        import shutil

                        # Create restore command for display
                        restore_cmd = f"Copy {file_path} to {DB_PATH}"

                        # Make a backup of the current database first
                        backup_path = f"{DB_PATH}.bak"
                        if os.path.exists(DB_PATH):
                            shutil.copy2(DB_PATH, backup_path)
                            logger.info(f"Created backup of current database at {backup_path}")

                        # Copy the backup file to the database location
                        shutil.copy2(file_path, DB_PATH)

                        # Verify the restore
                        if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
                            success = True
                        else:
                            # Restore from backup if the restore failed
                            if os.path.exists(backup_path):
                                shutil.copy2(backup_path, DB_PATH)
                                logger.warning("Restore failed, reverted to backup")
                    else:
                        # For PostgreSQL, use psql
                        from ..models.base import DB_USER, DB_PASSWORD, DB_HOST, DB_NAME

                        # Create restore command
                        restore_cmd = f"psql -U {DB_USER} -h {DB_HOST} -d {DB_NAME} -f {file_path}"

                        # Execute the command
                        import subprocess
                        env = os.environ.copy()
                        env["PGPASSWORD"] = DB_PASSWORD
                        result = subprocess.run(
                            restore_cmd,
                            shell=True,
                            env=env,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )

                        success = (result.returncode == 0)

                    # Close progress dialog
                    progress_dialog.close()

                    if success:
                        QMessageBox.information(self, "Restore Database", f"Database restored from:\n{file_path}")

                        # Inform the user that a restart is needed
                        QMessageBox.information(
                            self,
                            "Restart Required",
                            "The database has been restored. Please restart the application for changes to take effect."
                        )
                    else:
                        if 'result' in locals() and hasattr(result, 'stderr'):
                            error_msg = result.stderr.decode('utf-8')
                            QMessageBox.critical(self, "Restore Error", f"Failed to restore database:\n{error_msg}")
                        else:
                            QMessageBox.critical(self, "Restore Error", "Failed to restore database.")

                except Exception as e:
                    logger.error(f"Error restoring database: {str(e)}")
                    QMessageBox.critical(self, "Restore Error", f"Error restoring database: {str(e)}")

    def view_logs(self):
        """
        View system logs.
        """
        # Create a log viewer dialog
        log_dialog = LogViewerDialog(self)
        log_dialog.exec_()

    def save_settings(self):
        """
        Save system settings.
        """
        try:
            # Get settings values
            mqtt_host = self.mqtt_host_input.text().strip()
            mqtt_port = self.mqtt_port_input.text().strip()
            auto_start = self.auto_start_checkbox.isChecked()

            # Validate settings
            if not mqtt_host:
                QMessageBox.warning(self, "Validation Error", "Please enter an MQTT broker host.")
                return

            if not mqtt_port.isdigit():
                QMessageBox.warning(self, "Validation Error", "MQTT broker port must be a number.")
                return

            # Create a settings file
            settings_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.ini")

            with open(settings_path, 'w') as f:
                f.write("[MQTT]\n")
                f.write(f"broker_host = {mqtt_host}\n")
                f.write(f"broker_port = {mqtt_port}\n")
                f.write("\n[System]\n")
                f.write(f"auto_start = {str(auto_start).lower()}\n")

            # Update environment variables
            os.environ['MQTT_BROKER_HOST'] = mqtt_host
            os.environ['MQTT_BROKER_PORT'] = mqtt_port

            QMessageBox.information(self, "Save Settings", "Settings saved successfully.\nSome settings may require an application restart to take effect.")

        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            QMessageBox.critical(self, "Save Error", f"Error saving settings: {str(e)}")

class LogViewerDialog(QDialog):
    """
    Dialog for viewing system logs.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_logs()

    def init_ui(self):
        """
        Initialize the UI components.
        """
        self.setWindowTitle("System Logs")
        self.resize(800, 600)

        # Main layout
        layout = QVBoxLayout()

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.NoWrap)
        self.log_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.log_text)

        # Controls
        controls_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.load_logs)
        controls_layout.addWidget(self.refresh_button)

        self.clear_button = QPushButton("Clear Logs")
        self.clear_button.clicked.connect(self.clear_logs)
        controls_layout.addWidget(self.clear_button)

        controls_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        controls_layout.addWidget(self.close_button)

        layout.addLayout(controls_layout)

        self.setLayout(layout)

    def load_logs(self):
        """
        Load and display the system logs.
        """
        try:
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "consultease.log")

            if os.path.exists(log_path):
                with open(log_path, 'r') as f:
                    log_content = f.read()

                # Set the log content
                self.log_text.setText(log_content)

                # Scroll to end
                cursor = self.log_text.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.log_text.setTextCursor(cursor)
            else:
                self.log_text.setText("Log file not found.")

        except Exception as e:
            self.log_text.setText(f"Error loading logs: {str(e)}")

    def clear_logs(self):
        """
        Clear the system logs.
        """
        try:
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "consultease.log")

            # Confirm clear
            reply = QMessageBox.warning(
                self,
                "Clear Logs",
                "Are you sure you want to clear all logs?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                if os.path.exists(log_path):
                    with open(log_path, 'w') as f:
                        f.write("")

                    self.log_text.setText("")
                    QMessageBox.information(self, "Clear Logs", "Logs cleared successfully.")
                else:
                    QMessageBox.warning(self, "Clear Logs", "Log file not found.")

        except Exception as e:
            QMessageBox.critical(self, "Clear Logs", f"Error clearing logs: {str(e)}")
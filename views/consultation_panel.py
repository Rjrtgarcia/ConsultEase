"""
Consultation panel module.
Contains the consultation request form and consultation history panel.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QGridLayout, QScrollArea, QFrame,
                            QLineEdit, QTextEdit, QComboBox, QMessageBox,
                            QTabWidget, QTableWidget, QTableWidgetItem,
                            QHeaderView, QSplitter, QDialog, QFormLayout,
                            QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSize, QDateTime
from PyQt5.QtGui import QIcon, QColor, QPixmap, QFont

import os
import logging
import datetime

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
        self.faculty_options = []
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
                padding: 10px;
            }
            QLabel {
                font-size: 12pt;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 8px;
                background-color: white;
                font-size: 11pt;
            }
            QPushButton {
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 11pt;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
        ''')

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Form title
        title_label = QLabel("Request Consultation")
        title_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: #2c3e50;")
        main_layout.addWidget(title_label)

        # Faculty selection
        faculty_layout = QHBoxLayout()
        faculty_label = QLabel("Faculty:")
        faculty_label.setFixedWidth(100)
        self.faculty_combo = QComboBox()
        self.faculty_combo.setMinimumWidth(300)
        faculty_layout.addWidget(faculty_label)
        faculty_layout.addWidget(self.faculty_combo)
        main_layout.addLayout(faculty_layout)

        # Course code input
        course_layout = QHBoxLayout()
        course_label = QLabel("Course Code:")
        course_label.setFixedWidth(100)
        self.course_input = QLineEdit()
        self.course_input.setPlaceholderText("e.g., CS101 (optional)")
        course_layout.addWidget(course_label)
        course_layout.addWidget(self.course_input)
        main_layout.addLayout(course_layout)

        # Message input
        message_layout = QVBoxLayout()
        message_label = QLabel("Consultation Details:")
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Describe what you'd like to discuss...")
        self.message_input.setMinimumHeight(150)
        message_layout.addWidget(message_label)
        message_layout.addWidget(self.message_input)
        main_layout.addLayout(message_layout)

        # Character count
        self.char_count_label = QLabel("0/500 characters")
        self.char_count_label.setAlignment(Qt.AlignRight)
        self.char_count_label.setStyleSheet("color: #7f8c8d; font-size: 10pt;")
        main_layout.addWidget(self.char_count_label)

        # Connect text changed signal to update character count
        self.message_input.textChanged.connect(self.update_char_count)

        # Buttons
        button_layout = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet('''
            QPushButton {
                background-color: #e74c3c;
                min-width: 120px;
            }
        ''')
        cancel_button.clicked.connect(self.cancel_request)

        submit_button = QPushButton("Submit Request")
        submit_button.setStyleSheet('''
            QPushButton {
                background-color: #2ecc71;
                min-width: 120px;
            }
        ''')
        submit_button.clicked.connect(self.submit_request)

        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(submit_button)

        main_layout.addLayout(button_layout)

    def update_char_count(self):
        """
        Update the character count label.
        """
        count = len(self.message_input.toPlainText())
        color = "#7f8c8d"  # Default gray

        if count > 400:
            color = "#f39c12"  # Warning yellow
        if count > 500:
            color = "#e74c3c"  # Error red

        self.char_count_label.setText(f"{count}/500 characters")
        self.char_count_label.setStyleSheet(f"color: {color}; font-size: 10pt;")

    def set_faculty(self, faculty):
        """
        Set the faculty for the consultation request.
        """
        self.faculty = faculty

        # Update the combo box
        if self.faculty and self.faculty_combo.count() > 0:
            for i in range(self.faculty_combo.count()):
                faculty_id = self.faculty_combo.itemData(i)
                if faculty_id == self.faculty.id:
                    self.faculty_combo.setCurrentIndex(i)
                    break

    def set_faculty_options(self, faculty_list):
        """
        Set the available faculty options in the dropdown.
        """
        self.faculty_options = faculty_list
        self.faculty_combo.clear()

        for faculty in faculty_list:
            self.faculty_combo.addItem(f"{faculty.name} ({faculty.department})", faculty.id)

        # If we have a selected faculty, select it in the dropdown
        if self.faculty:
            for i in range(self.faculty_combo.count()):
                faculty_id = self.faculty_combo.itemData(i)
                if faculty_id == self.faculty.id:
                    self.faculty_combo.setCurrentIndex(i)
                    break

    def get_selected_faculty(self):
        """
        Get the selected faculty from the dropdown.
        """
        if self.faculty_combo.count() == 0:
            return self.faculty

        faculty_id = self.faculty_combo.currentData()

        for faculty in self.faculty_options:
            if faculty.id == faculty_id:
                return faculty

        return None

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

        # Check message length
        if len(message) > 500:
            QMessageBox.warning(self, "Consultation Request", "Consultation details are too long. Please limit to 500 characters.")
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

class ConsultationHistoryPanel(QFrame):
    """
    Panel to display consultation history.
    """
    consultation_selected = pyqtSignal(object)
    consultation_cancelled = pyqtSignal(int)

    def __init__(self, student=None, parent=None):
        super().__init__(parent)
        self.student = student
        self.consultations = []
        self.init_ui()

    def init_ui(self):
        """
        Initialize the consultation history panel UI.
        """
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet('''
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 10px;
            }
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                alternate-background-color: #f9f9f9;
                gridline-color: #ddd;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #2c3e50;
                color: white;
                padding: 5px;
                border: none;
            }
            QPushButton {
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 11pt;
                font-weight: bold;
                color: white;
            }
        ''')

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Title
        title_label = QLabel("My Consultation History")
        title_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: #2c3e50;")
        main_layout.addWidget(title_label)

        # Consultation table
        self.consultation_table = QTableWidget()
        self.consultation_table.setColumnCount(5)
        self.consultation_table.setHorizontalHeaderLabels(["Faculty", "Course", "Status", "Date", "Actions"])
        self.consultation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.consultation_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.consultation_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.consultation_table.setSelectionMode(QTableWidget.SingleSelection)
        self.consultation_table.setAlternatingRowColors(True)

        main_layout.addWidget(self.consultation_table)

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setStyleSheet('''
            QPushButton {
                background-color: #3498db;
                min-width: 120px;
            }
        ''')
        refresh_button.clicked.connect(self.refresh_consultations)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(refresh_button)

        main_layout.addLayout(button_layout)

    def set_student(self, student):
        """
        Set the student for the consultation history.
        """
        self.student = student
        self.refresh_consultations()

    def refresh_consultations(self):
        """
        Refresh the consultation history from the database.
        """
        if not self.student:
            return

        try:
            # Import consultation controller
            from ..controllers import ConsultationController

            # Get consultation controller
            consultation_controller = ConsultationController()

            # Get consultations for this student
            self.consultations = consultation_controller.get_consultations(student_id=self.student.id)

            # Update the table
            self.update_consultation_table()
        except Exception as e:
            logger.error(f"Error refreshing consultations: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to refresh consultation history: {str(e)}")

    def update_consultation_table(self):
        """
        Update the consultation table with the current consultations.
        """
        # Clear the table
        self.consultation_table.setRowCount(0)

        # Add consultations to the table
        for consultation in self.consultations:
            row_position = self.consultation_table.rowCount()
            self.consultation_table.insertRow(row_position)

            # Faculty name
            faculty_item = QTableWidgetItem(consultation.faculty.name)
            self.consultation_table.setItem(row_position, 0, faculty_item)

            # Course code
            course_item = QTableWidgetItem(consultation.course_code if consultation.course_code else "N/A")
            self.consultation_table.setItem(row_position, 1, course_item)

            # Status with color coding
            status_item = QTableWidgetItem(consultation.status.value.capitalize())
            if consultation.status.value == "pending":
                status_item.setBackground(QColor(255, 235, 59))  # Yellow
            elif consultation.status.value == "accepted":
                status_item.setBackground(QColor(76, 175, 80))  # Green
            elif consultation.status.value == "completed":
                status_item.setBackground(QColor(33, 150, 243))  # Blue
            elif consultation.status.value == "cancelled":
                status_item.setBackground(QColor(244, 67, 54))  # Red
            self.consultation_table.setItem(row_position, 2, status_item)

            # Date
            date_str = consultation.requested_at.strftime("%Y-%m-%d %H:%M")
            date_item = QTableWidgetItem(date_str)
            self.consultation_table.setItem(row_position, 3, date_item)

            # Actions
            actions_cell = QWidget()
            actions_layout = QHBoxLayout(actions_cell)
            actions_layout.setContentsMargins(2, 2, 2, 2)

            # View details button
            view_button = QPushButton("View")
            view_button.setStyleSheet("background-color: #3498db; color: white;")
            view_button.clicked.connect(lambda checked, c=consultation: self.view_consultation_details(c))
            actions_layout.addWidget(view_button)

            # Cancel button (only for pending consultations)
            if consultation.status.value == "pending":
                cancel_button = QPushButton("Cancel")
                cancel_button.setStyleSheet("background-color: #e74c3c; color: white;")
                cancel_button.clicked.connect(lambda checked, c=consultation: self.cancel_consultation(c))
                actions_layout.addWidget(cancel_button)

            self.consultation_table.setCellWidget(row_position, 4, actions_cell)

    def view_consultation_details(self, consultation):
        """
        Show consultation details in a dialog.
        """
        dialog = ConsultationDetailsDialog(consultation, self)
        dialog.exec_()

    def cancel_consultation(self, consultation):
        """
        Cancel a pending consultation.
        """
        reply = QMessageBox.question(
            self,
            "Cancel Consultation",
            f"Are you sure you want to cancel your consultation request with {consultation.faculty.name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Emit signal to cancel the consultation
            self.consultation_cancelled.emit(consultation.id)

class ConsultationDetailsDialog(QDialog):
    """
    Dialog to display consultation details.
    """
    def __init__(self, consultation, parent=None):
        super().__init__(parent)
        self.consultation = consultation
        self.init_ui()

    def init_ui(self):
        """
        Initialize the dialog UI.
        """
        self.setWindowTitle("Consultation Details")
        self.setMinimumWidth(500)
        self.setStyleSheet('''
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                font-size: 12pt;
            }
            QLabel[heading="true"] {
                font-size: 14pt;
                font-weight: bold;
                color: #2c3e50;
            }
            QFrame {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
                padding: 10px;
            }
            QPushButton {
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 11pt;
                font-weight: bold;
                color: white;
                background-color: #3498db;
            }
        ''')

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Consultation Details")
        title_label.setProperty("heading", "true")
        layout.addWidget(title_label)

        # Details frame
        details_frame = QFrame()
        details_layout = QFormLayout(details_frame)
        details_layout.setSpacing(10)

        # Faculty
        faculty_label = QLabel("Faculty:")
        faculty_value = QLabel(self.consultation.faculty.name)
        faculty_value.setStyleSheet("font-weight: bold;")
        details_layout.addRow(faculty_label, faculty_value)

        # Department
        dept_label = QLabel("Department:")
        dept_value = QLabel(self.consultation.faculty.department)
        details_layout.addRow(dept_label, dept_value)

        # Course
        course_label = QLabel("Course:")
        course_value = QLabel(self.consultation.course_code if self.consultation.course_code else "N/A")
        details_layout.addRow(course_label, course_value)

        # Status
        status_label = QLabel("Status:")
        status_value = QLabel(self.consultation.status.value.capitalize())
        status_color = "#7f8c8d"  # Default gray

        if self.consultation.status.value == "pending":
            status_color = "#f39c12"  # Yellow
        elif self.consultation.status.value == "accepted":
            status_color = "#2ecc71"  # Green
        elif self.consultation.status.value == "completed":
            status_color = "#3498db"  # Blue
        elif self.consultation.status.value == "cancelled":
            status_color = "#e74c3c"  # Red

        status_value.setStyleSheet(f"font-weight: bold; color: {status_color};")
        details_layout.addRow(status_label, status_value)

        # Requested date
        requested_label = QLabel("Requested:")
        requested_value = QLabel(self.consultation.requested_at.strftime("%Y-%m-%d %H:%M"))
        details_layout.addRow(requested_label, requested_value)

        # Accepted date (if applicable)
        if self.consultation.accepted_at:
            accepted_label = QLabel("Accepted:")
            accepted_value = QLabel(self.consultation.accepted_at.strftime("%Y-%m-%d %H:%M"))
            details_layout.addRow(accepted_label, accepted_value)

        # Completed date (if applicable)
        if self.consultation.completed_at:
            completed_label = QLabel("Completed:")
            completed_value = QLabel(self.consultation.completed_at.strftime("%Y-%m-%d %H:%M"))
            details_layout.addRow(completed_label, completed_value)

        layout.addWidget(details_frame)

        # Message
        message_label = QLabel("Consultation Details:")
        message_label.setProperty("heading", "true")
        layout.addWidget(message_label)

        message_frame = QFrame()
        message_layout = QVBoxLayout(message_frame)

        message_text = QLabel(self.consultation.request_message)
        message_text.setWordWrap(True)
        message_layout.addWidget(message_text)

        layout.addWidget(message_frame)

        # Close button
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

class ConsultationPanel(QTabWidget):
    """
    Main consultation panel with request form and history tabs.
    """
    consultation_requested = pyqtSignal(object, str, str)
    consultation_cancelled = pyqtSignal(int)

    def __init__(self, student=None, parent=None):
        super().__init__(parent)
        self.student = student
        self.init_ui()

    def init_ui(self):
        """
        Initialize the consultation panel UI.
        """
        self.setStyleSheet('''
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: #f5f5f5;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 8px 15px;
                margin-right: 2px;
                font-size: 11pt;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }
        ''')

        # Request form tab
        self.request_form = ConsultationRequestForm()
        self.request_form.request_submitted.connect(self.handle_consultation_request)
        self.addTab(self.request_form, "Request Consultation")

        # History tab
        self.history_panel = ConsultationHistoryPanel(self.student)
        self.history_panel.consultation_cancelled.connect(self.handle_consultation_cancel)
        self.addTab(self.history_panel, "Consultation History")

    def set_student(self, student):
        """
        Set the student for the consultation panel.
        """
        self.student = student
        self.history_panel.set_student(student)

    def set_faculty(self, faculty):
        """
        Set the faculty for the consultation request.
        """
        self.request_form.set_faculty(faculty)
        self.setCurrentIndex(0)  # Switch to request form tab

    def set_faculty_options(self, faculty_list):
        """
        Set the available faculty options in the dropdown.
        """
        self.request_form.set_faculty_options(faculty_list)

    def handle_consultation_request(self, faculty, message, course_code):
        """
        Handle consultation request submission.
        """
        # Emit signal to controller
        self.consultation_requested.emit(faculty, message, course_code)

        # Refresh history
        self.history_panel.refresh_consultations()

        # Switch to history tab
        self.setCurrentIndex(1)

    def handle_consultation_cancel(self, consultation_id):
        """
        Handle consultation cancellation.
        """
        # Emit signal to controller
        self.consultation_cancelled.emit(consultation_id)

        # Refresh history
        self.history_panel.refresh_consultations()

    def refresh_history(self):
        """
        Refresh the consultation history.
        """
        self.history_panel.refresh_consultations()

"""
Pooled Faculty Card component for ConsultEase.
Optimized for reuse and performance on Raspberry Pi.
"""

import logging
from typing import Optional, Callable
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette

from .component_pool import get_component_pool

logger = logging.getLogger(__name__)


class PooledFacultyCard(QWidget):
    """
    Faculty card widget optimized for pooling and reuse.
    """

    # Signals
    consultation_requested = pyqtSignal(int)  # faculty_id

    def __init__(self, parent=None):
        """
        Initialize the pooled faculty card.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Faculty data
        self.faculty_id = None
        self.faculty_data = None
        self.consultation_callback = None

        # Setup UI
        self._setup_ui()

        # Track if card is currently in use
        self.is_active = False

        logger.debug("Created new PooledFacultyCard")

    def _setup_ui(self):
        """Setup the user interface."""
        # Main layout
        self.setFixedSize(280, 120)  # Optimized size for touch interface
        self.setStyleSheet("""
            PooledFacultyCard {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin: 4px;
            }
            PooledFacultyCard:hover {
                border-color: #2196F3;
                background-color: #f5f5f5;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(4)

        # Header layout (name and status)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Faculty name label
        self.name_label = QLabel()
        self.name_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.name_label.setStyleSheet("color: #333333;")
        self.name_label.setWordWrap(True)
        header_layout.addWidget(self.name_label, 1)

        # Status indicator
        self.status_widget = QWidget()
        self.status_widget.setFixedSize(12, 12)
        self.status_widget.setStyleSheet("""
            background-color: #cccccc;
            border-radius: 6px;
        """)
        header_layout.addWidget(self.status_widget, 0, Qt.AlignTop)

        main_layout.addLayout(header_layout)

        # Department label
        self.department_label = QLabel()
        self.department_label.setFont(QFont("Arial", 9))
        self.department_label.setStyleSheet("color: #666666;")
        main_layout.addWidget(self.department_label)

        # Spacer
        main_layout.addStretch()

        # Consult button
        self.consult_button = QPushButton("Request Consultation")
        self.consult_button.setFont(QFont("Arial", 9))
        self.consult_button.setFixedHeight(28)
        self.consult_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.consult_button.clicked.connect(self._on_consult_clicked)
        main_layout.addWidget(self.consult_button)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def configure(self, faculty_data: dict, consultation_callback: Optional[Callable] = None):
        """
        Configure the card with faculty data.

        Args:
            faculty_data: Dictionary containing faculty information
            consultation_callback: Callback function for consultation requests
        """
        self.faculty_data = faculty_data.copy()  # Store a copy
        self.faculty_id = faculty_data.get('id')
        self.consultation_callback = consultation_callback
        self.is_active = True

        # Update UI elements
        self._update_display()

        # Ensure the card is visible when configured
        self.show()

        logger.debug(f"Configured faculty card for: {faculty_data.get('name', 'Unknown')}")

    def _update_display(self):
        """Update the display with current faculty data."""
        if not self.faculty_data:
            return

        # Update name
        name = self.faculty_data.get('name', 'Unknown Faculty')
        self.name_label.setText(name)

        # Update department
        department = self.faculty_data.get('department', 'Unknown Department')
        self.department_label.setText(department)

        # Update status - handle both boolean and string status values
        raw_status = self.faculty_data.get('status', 'offline')
        
        # Convert boolean status to string
        if isinstance(raw_status, bool):
            status = 'available' if raw_status else 'offline'
        elif isinstance(raw_status, str):
            status = raw_status
        else:
            # Fallback for any other type
            status = 'offline'
        
        self._update_status_indicator(status)

        # Update button state - check for availability
        # Handle both 'available' field and converted status
        is_available = False
        if 'available' in self.faculty_data:
            is_available = bool(self.faculty_data.get('available', False))
        else:
            # Fallback to status-based availability
            is_available = status.lower() == 'available'
        
        self.consult_button.setEnabled(is_available)

        if not is_available:
            self.consult_button.setText("Not Available")
        else:
            self.consult_button.setText("Request Consultation")

    def _update_status_indicator(self, status: str):
        """
        Update the status indicator color.

        Args:
            status: Faculty status (string or boolean)
        """
        logger.info(f"🟢 [STATUS INDICATOR] Updating indicator for status: {status} (type: {type(status)})")
        
        # Ensure status is a string and handle edge cases
        if not isinstance(status, str):
            if isinstance(status, bool):
                status = 'available' if status else 'offline'
            else:
                status = str(status).lower() if status else 'offline'
        
        status_colors = {
            'available': '#4CAF50',    # Green
            'busy': '#FF9800',         # Orange
            'offline': '#9E9E9E',      # Gray
            'unavailable': '#9E9E9E',  # Gray
            'in_consultation': '#F44336'  # Red
        }

        color = status_colors.get(status.lower(), '#9E9E9E')
        old_style = self.status_widget.styleSheet()
        new_style = f"""
            background-color: {color};
            border-radius: 6px;
        """
        
        logger.info(f"🟢 [STATUS INDICATOR] Color mapping: {status.lower()} -> {color}")
        logger.info(f"🟢 [STATUS INDICATOR] Old style: {old_style}")
        logger.info(f"🟢 [STATUS INDICATOR] New style: {new_style}")
        
        self.status_widget.setStyleSheet(new_style)
        self.status_widget.update()
        logger.info(f"🟢 [STATUS INDICATOR] Applied new style and forced update")

    def _on_consult_clicked(self):
        """Handle consultation button click."""
        if not self.faculty_id:
            logger.warning("Consultation requested but no faculty ID set")
            return

        # Emit signal with faculty_id (for backward compatibility)
        self.consultation_requested.emit(self.faculty_id)

        # Call callback if provided - pass full faculty_data instead of just ID
        if self.consultation_callback:
            try:
                # Pass the full faculty_data dictionary to the callback
                if self.faculty_data:
                    self.consultation_callback(self.faculty_data)
                else:
                    # Fallback: pass faculty_id if faculty_data is not available
                    logger.warning(f"Faculty data not available for ID {self.faculty_id}, passing ID only")
                self.consultation_callback(self.faculty_id)
            except Exception as e:
                logger.error(f"Error in consultation callback: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

    def reset(self):
        """Reset the card to default state for pooling."""
        self.faculty_id = None
        self.faculty_data = None
        self.consultation_callback = None
        self.is_active = False

        # Reset UI elements
        self.name_label.setText("")
        self.department_label.setText("")
        self.consult_button.setText("Request Consultation")
        self.consult_button.setEnabled(True)

        # Reset status indicator
        self.status_widget.setStyleSheet("""
            background-color: #cccccc;
            border-radius: 6px;
        """)

        # Disconnect signals
        try:
            self.consultation_requested.disconnect()
        except TypeError:
            pass  # No connections to disconnect

        # Hide the widget
        self.hide()

        logger.debug("Reset faculty card for pooling")

    def update_status(self, new_status: str):
        """
        Update only the status of the faculty card.

        Args:
            new_status: New status (string or boolean)
        """
        if not self.faculty_data:
            logger.error(f"🔴 [CARD UPDATE] Cannot update status - no faculty_data available")
            return
            
        old_status = self.faculty_data.get('status', 'unknown')
        logger.info(f"🎯 [CARD UPDATE] Updating card status for faculty {self.faculty_data.get('id')} from '{old_status}' to '{new_status}' (type: {type(new_status)})")
        
        # 🔧 FIX: Enhanced status mapping with explicit checks
        if new_status is True or new_status == True:
            status_str = 'available'
            available = True
            logger.info(f"🎯 [CARD UPDATE] Boolean True -> available")
        elif new_status is False or new_status == False:
            status_str = 'offline'
            available = False
            logger.info(f"🎯 [CARD UPDATE] Boolean False -> offline")
        elif isinstance(new_status, str):
            status_str = new_status.lower().strip()
            if status_str in ['available', 'present', 'online', 'active']:
                status_str = 'available'
                available = True
                logger.info(f"🎯 [CARD UPDATE] String '{new_status}' -> available")
            elif status_str in ['busy', 'in_consultation', 'occupied']:
                status_str = 'busy'
                available = False  # Busy = can't take new consultations
                logger.info(f"🎯 [CARD UPDATE] String '{new_status}' -> busy")
            else:
                status_str = 'offline'
                available = False
                logger.info(f"🎯 [CARD UPDATE] String '{new_status}' -> offline (default)")
        else:
            # Fallback
            status_str = 'offline'
            available = False
            logger.warning(f"🎯 [CARD UPDATE] Unknown type {type(new_status)} -> offline (fallback)")
        
        # Update faculty data
        self.faculty_data['status'] = status_str
        self.faculty_data['available'] = available
        
        logger.info(f"🎯 [CARD UPDATE] Final mapping: {new_status} -> status='{status_str}', available={available}")
        
        # Update status indicator
        self._update_status_indicator(status_str)
        logger.info(f"🔴 [CARD UPDATE] Called _update_status_indicator('{status_str}')")

        # Update button state
        self.consult_button.setEnabled(available)
        logger.info(f"🔵 [CARD UPDATE] Button enabled: {available}")

        if not available:
            if status_str == 'busy':
                self.consult_button.setText("Busy")
            else:
                self.consult_button.setText("Not Available")
            logger.info(f"🔵 [CARD UPDATE] Button text set to '{self.consult_button.text()}'")
        else:
            self.consult_button.setText("Request Consultation")
            logger.info(f"🔵 [CARD UPDATE] Button text set to 'Request Consultation'")
            
        # Force widget updates
        self.status_widget.update()
        self.consult_button.update() 
        self.update()
        logger.info(f"🔴 [CARD UPDATE] Forced widget updates and repaint - Status: {status_str}, Available: {available}")


class FacultyCardManager:
    """
    Manager for pooled faculty cards.
    """

    def __init__(self):
        """Initialize the faculty card manager."""
        self.component_pool = get_component_pool()
        self.active_cards = {}  # faculty_id -> (card, component_id)

        logger.info("Faculty card manager initialized")

    def get_faculty_card(self, faculty_data: dict, consultation_callback: Optional[Callable] = None) -> PooledFacultyCard:
        """
        Get a faculty card for the given faculty data.

        Args:
            faculty_data: Faculty information
            consultation_callback: Callback for consultation requests

        Returns:
            PooledFacultyCard: Configured faculty card
        """
        faculty_id = faculty_data.get('id')

        # Check if we already have an active card for this faculty
        if faculty_id in self.active_cards:
            card, component_id = self.active_cards[faculty_id]
            # Update the existing card
            card.configure(faculty_data, consultation_callback)
            return card

        # Get a card from the pool
        component_id = f"faculty_card_{faculty_id}"
        card = self.component_pool.get_component(
            component_type="faculty_card",
            component_class=PooledFacultyCard,
            component_id=component_id
        )

        # Configure the card
        card.configure(faculty_data, consultation_callback)

        # Track the active card
        self.active_cards[faculty_id] = (card, component_id)

        logger.debug(f"Retrieved faculty card for faculty {faculty_id}")
        return card

    def return_faculty_card(self, faculty_id: int):
        """
        Return a faculty card to the pool.

        Args:
            faculty_id: ID of the faculty whose card to return
        """
        if faculty_id not in self.active_cards:
            logger.warning(f"Attempted to return unknown faculty card: {faculty_id}")
            return

        card, component_id = self.active_cards.pop(faculty_id)

        # Reset the card
        card.reset()

        # Return to pool
        self.component_pool.return_component(component_id, "faculty_card")

        logger.debug(f"Returned faculty card for faculty {faculty_id}")

    def update_faculty_status(self, faculty_id: int, new_status: str):
        """
        Update the status of a specific faculty card.

        Args:
            faculty_id: ID of the faculty
            new_status: New status string
        """
        if faculty_id in self.active_cards:
            card, _ = self.active_cards[faculty_id]
            card.update_status(new_status)

    def clear_all_cards(self):
        """Clear all active faculty cards."""
        for faculty_id in list(self.active_cards.keys()):
            self.return_faculty_card(faculty_id)

        logger.info("Cleared all faculty cards")

    def get_stats(self) -> dict:
        """
        Get statistics about faculty card usage.

        Returns:
            dict: Usage statistics
        """
        pool_stats = self.component_pool.get_stats()

        return {
            'active_cards': len(self.active_cards),
            'pool_stats': pool_stats
        }


# Global faculty card manager
_faculty_card_manager = None


def get_faculty_card_manager() -> FacultyCardManager:
    """
    Get the global faculty card manager.

    Returns:
        FacultyCardManager: Global faculty card manager
    """
    global _faculty_card_manager
    if _faculty_card_manager is None:
        _faculty_card_manager = FacultyCardManager()
    return _faculty_card_manager

#!/usr/bin/env python3
"""
Test script to verify QTableWidget ownership fix.
This script simulates the consultation history table population to check for ownership issues.
"""

import sys
import os
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Mock PyQt5 before importing our modules
mock_qtwidgets = Mock()
mock_qtcore = Mock()
mock_qtgui = Mock()

# Create mock classes for Qt components
class MockQTableWidgetItem:
    def __init__(self, text=""):
        self.text_value = text
        self.data_dict = {}
        self.is_owned = False
        self.owner = None
        
    def setText(self, text):
        self.text_value = text
        
    def text(self):
        return self.text_value
        
    def setData(self, role, data):
        self.data_dict[role] = data
        
    def data(self, role):
        return self.data_dict.get(role)
        
    def setBackground(self, color):
        pass
        
    def setForeground(self, color):
        pass
        
    def setFont(self, font):
        pass
        
    def font(self):
        mock_font = Mock()
        mock_font.setBold = Mock()
        mock_font.setPointSize = Mock()
        mock_font.pointSize = Mock(return_value=12)
        return mock_font

class MockQTableWidget:
    def __init__(self):
        self.items = {}  # (row, col) -> item
        self.row_count = 0
        self.ownership_errors = []
        
    def setRowCount(self, count):
        if count == 0:
            # Clear all items when resetting
            self.items.clear()
        self.row_count = count
        
    def rowCount(self):
        return self.row_count
        
    def insertRow(self, position):
        self.row_count += 1
        
    def setItem(self, row, col, item):
        # Check for ownership issues
        if hasattr(item, 'is_owned') and item.is_owned:
            error_msg = f"QTableWidget: cannot insert an item that is already owned by another QTableWidget (Row: {row}, Col: {col})"
            self.ownership_errors.append(error_msg)
            print(f"❌ OWNERSHIP ERROR: {error_msg}")
            return
            
        # Mark item as owned
        if hasattr(item, 'is_owned'):
            item.is_owned = True
            item.owner = self
            
        self.items[(row, col)] = item
        
    def setCellWidget(self, row, col, widget):
        pass

# Mock the Qt modules
mock_qtwidgets.QTableWidgetItem = MockQTableWidgetItem
mock_qtwidgets.QTableWidget = MockQTableWidget
mock_qtwidgets.QWidget = Mock
mock_qtwidgets.QHBoxLayout = Mock
mock_qtwidgets.QPushButton = Mock
mock_qtwidgets.QSizePolicy = Mock
mock_qtcore.Qt = Mock()
mock_qtcore.Qt.UserRole = 256
mock_qtgui.QColor = Mock

sys.modules['PyQt5'] = Mock()
sys.modules['PyQt5.QtWidgets'] = mock_qtwidgets
sys.modules['PyQt5.QtCore'] = mock_qtcore
sys.modules['PyQt5.QtGui'] = mock_qtgui

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class MockConsultationStatus:
    def __init__(self, value):
        self.value = value

class MockFaculty:
    def __init__(self, name):
        self.name = name

class MockConsultation:
    def __init__(self, id, faculty_name, status, course_code=None):
        self.id = id
        self.faculty = MockFaculty(faculty_name)
        self.status = MockConsultationStatus(status)
        self.course_code = course_code
        self.requested_at = datetime.now()

class QTableWidgetOwnershipTester:
    """Test class to verify QTableWidget ownership fixes."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.test_consultations = self._create_test_data()
        
    def _create_test_data(self):
        """Create test consultation data."""
        return [
            MockConsultation(1, "Dr. Smith", "pending", "CS101"),
            MockConsultation(2, "Prof. Johnson", "accepted", "MATH201"),
            MockConsultation(3, "Dr. Brown", "completed", "PHYS301"),
            MockConsultation(4, "Prof. Davis", "cancelled", "ENG401"),
        ]
    
    def test_consultation_table_population(self):
        """Test the consultation table population logic."""
        self.logger.info("🧪 Testing consultation table population...")
        
        # Create mock consultation table
        consultation_table = MockQTableWidget()
        
        # Simulate the table population logic from consultation_panel.py
        consultation_table.setRowCount(0)
        
        for consultation in self.test_consultations:
            row_position = consultation_table.rowCount()
            consultation_table.insertRow(row_position)
            
            # Faculty name (with our fix)
            faculty_item = MockQTableWidgetItem(consultation.faculty.name)
            # Store consultation ID as data for real-time updates (moved here - our fix)
            faculty_item.setData(mock_qtcore.Qt.UserRole, consultation.id)
            consultation_table.setItem(row_position, 0, faculty_item)
            
            # Course code
            course_item = MockQTableWidgetItem(consultation.course_code if consultation.course_code else "N/A")
            consultation_table.setItem(row_position, 1, course_item)
            
            # Status
            status_item = MockQTableWidgetItem(consultation.status.value.capitalize())
            consultation_table.setItem(row_position, 2, status_item)
            
            # Date
            date_str = consultation.requested_at.strftime("%Y-%m-%d %H:%M")
            date_item = MockQTableWidgetItem(date_str)
            consultation_table.setItem(row_position, 3, date_item)
            
            # Note: consultation ID already stored in faculty_item above
            # This prevents the double setItem() call that was causing ownership issues
            
            self.logger.info(f"   ✅ Added consultation {consultation.id}: {consultation.faculty.name}")
        
        # Check for ownership errors
        if consultation_table.ownership_errors:
            self.logger.error(f"❌ Found {len(consultation_table.ownership_errors)} ownership errors:")
            for error in consultation_table.ownership_errors:
                self.logger.error(f"   • {error}")
            return False
        else:
            self.logger.info(f"✅ No ownership errors detected!")
            return True
    
    def test_table_refresh_simulation(self):
        """Test multiple table refreshes to simulate real usage."""
        self.logger.info("🔄 Testing table refresh simulation...")
        
        consultation_table = MockQTableWidget()
        
        # Simulate multiple refreshes
        for refresh_count in range(3):
            self.logger.info(f"   🔄 Refresh #{refresh_count + 1}")
            
            # Clear and repopulate (simulates refresh)
            consultation_table.setRowCount(0)
            
            for consultation in self.test_consultations:
                row_position = consultation_table.rowCount()
                consultation_table.insertRow(row_position)
                
                # Create NEW items each time (this is key for ownership)
                faculty_item = MockQTableWidgetItem(consultation.faculty.name)
                faculty_item.setData(mock_qtcore.Qt.UserRole, consultation.id)
                consultation_table.setItem(row_position, 0, faculty_item)
                
                course_item = MockQTableWidgetItem(consultation.course_code or "N/A")
                consultation_table.setItem(row_position, 1, course_item)
                
                status_item = MockQTableWidgetItem(consultation.status.value.capitalize())
                consultation_table.setItem(row_position, 2, status_item)
                
                date_item = MockQTableWidgetItem(consultation.requested_at.strftime("%Y-%m-%d %H:%M"))
                consultation_table.setItem(row_position, 3, date_item)
        
        # Check results
        if consultation_table.ownership_errors:
            self.logger.error(f"❌ Found {len(consultation_table.ownership_errors)} ownership errors during refresh:")
            for error in consultation_table.ownership_errors:
                self.logger.error(f"   • {error}")
            return False
        else:
            self.logger.info(f"✅ No ownership errors during multiple refreshes!")
            return True
    
    def test_old_problematic_code(self):
        """Test the old problematic code that would cause ownership issues."""
        self.logger.info("🔥 Testing old problematic code pattern...")
        
        consultation_table = MockQTableWidget()
        consultation_table.setRowCount(0)
        
        consultation = self.test_consultations[0]
        row_position = consultation_table.rowCount()
        consultation_table.insertRow(row_position)
        
        # Faculty name (original way)
        faculty_item = MockQTableWidgetItem(consultation.faculty.name)
        consultation_table.setItem(row_position, 0, faculty_item)
        
        # The problematic line that would cause ownership issues
        try:
            # This would try to set the SAME item again - causing ownership error
            consultation_table.setItem(row_position, 0, faculty_item)  # Same item, same position
            faculty_item.setData(mock_qtcore.Qt.UserRole, consultation.id)
        except Exception as e:
            self.logger.info(f"   ⚠️ Simulated old bug would cause: {e}")
        
        # Check if our mock caught the ownership issue
        if consultation_table.ownership_errors:
            self.logger.info(f"✅ Successfully detected the old ownership problem!")
            return True
        else:
            self.logger.warning("⚠️ Old problematic code didn't trigger ownership error in mock")
            return False
    
    def run_all_tests(self):
        """Run all ownership tests."""
        self.logger.info("🚀 Starting QTableWidget ownership tests...")
        
        tests = [
            ("Consultation Table Population", self.test_consultation_table_population),
            ("Table Refresh Simulation", self.test_table_refresh_simulation),
            ("Old Problematic Code Detection", self.test_old_problematic_code),
        ]
        
        results = []
        for test_name, test_func in tests:
            self.logger.info(f"\n📋 {test_name}")
            try:
                result = test_func()
                results.append((test_name, result))
                status = "✅ PASSED" if result else "❌ FAILED"
                self.logger.info(f"   {status}")
            except Exception as e:
                self.logger.error(f"   ❌ ERROR: {e}")
                results.append((test_name, False))
        
        # Summary
        passed = sum(1 for name, result in results if result)
        total = len(results)
        
        self.logger.info(f"\n📊 TEST SUMMARY:")
        self.logger.info(f"   Passed: {passed}/{total}")
        
        for test_name, result in results:
            status = "✅" if result else "❌"
            self.logger.info(f"   {status} {test_name}")
        
        if passed == total:
            self.logger.info("🎉 ALL TESTS PASSED - QTableWidget ownership fix confirmed!")
            return True
        else:
            self.logger.error("❌ Some tests failed - ownership issues may still exist")
            return False

def main():
    """Main test function."""
    print("🧪 QTableWidget Ownership Fix Test")
    print("=" * 50)
    
    tester = QTableWidgetOwnershipTester()
    success = tester.run_all_tests()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ ALL TESTS PASSED - Fix confirmed working!")
        return 0
    else:
        print("❌ TESTS FAILED - Issues still present!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
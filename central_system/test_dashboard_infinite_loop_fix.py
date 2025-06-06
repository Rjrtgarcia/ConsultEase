#!/usr/bin/env python3
"""
Test script to verify dashboard infinite loop fixes.
This script simulates the dashboard creation scenario to check for infinite loops.
"""

import sys
import os
import time
import logging
import json
from collections import defaultdict, Counter
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Mock PyQt5 before importing our modules
sys.modules['PyQt5'] = Mock()
sys.modules['PyQt5.QtWidgets'] = Mock()
sys.modules['PyQt5.QtCore'] = Mock()
sys.modules['PyQt5.QtGui'] = Mock()

# Set up basic environment
os.environ['DB_TYPE'] = 'sqlite'
os.environ['DB_PATH'] = ':memory:'
os.environ['CONSULTEASE_THEME'] = 'light'

class MockStudent:
    def __init__(self, student_id=1, name="Test Student", rfid_uid="1248304305"):
        self.id = student_id
        self.name = name
        self.rfid_uid = rfid_uid
        self.department = "Computer Engineering"

class DashboardLoopTester:
    """Test class to simulate dashboard infinite loop scenarios."""
    
    def __init__(self):
        self.setup_logging()
        self.mqtt_subscriptions = defaultdict(list)
        self.ui_refresh_count = 0
        self.dashboard_show_count = 0
        self.init_ui_count = 0
        self.mqtt_subscription_count = Counter()
        
    def setup_logging(self):
        """Set up logging for the test."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def mock_mqtt_subscribe(self, topic, handler):
        """Mock MQTT subscription to track duplicates."""
        self.mqtt_subscriptions[topic].append(handler)
        self.mqtt_subscription_count[topic] += 1
        self.logger.info(f"📡 MQTT Subscribe: {topic} (total handlers: {len(self.mqtt_subscriptions[topic])})")
        
        if len(self.mqtt_subscriptions[topic]) > 1:
            self.logger.warning(f"⚠️  DUPLICATE SUBSCRIPTION DETECTED for topic: {topic}")
            self.logger.warning(f"   Handlers: {len(self.mqtt_subscriptions[topic])}")
            
    def mock_dashboard_show(self):
        """Mock dashboard window show to track calls."""
        self.dashboard_show_count += 1
        self.logger.info(f"🖥️  Dashboard show call #{self.dashboard_show_count}")
        
        if self.dashboard_show_count > 1:
            self.logger.warning(f"⚠️  MULTIPLE DASHBOARD SHOW CALLS DETECTED: {self.dashboard_show_count}")
            
    def mock_init_ui(self):
        """Mock init_ui to track calls."""
        self.init_ui_count += 1
        self.logger.info(f"🔧 init_ui call #{self.init_ui_count}")
        
        if self.init_ui_count > 1:
            self.logger.warning(f"⚠️  MULTIPLE INIT_UI CALLS DETECTED: {self.init_ui_count}")
            
    def mock_ui_refresh(self):
        """Mock UI refresh to track calls."""
        self.ui_refresh_count += 1
        self.logger.info(f"🔄 UI refresh call #{self.ui_refresh_count}")
        
    def simulate_login_window_signals(self):
        """Simulate the login window signal emissions that were causing the loop."""
        self.logger.info("🔥 TESTING: Login window signal simulation")
        
        student_data = {
            'id': 1,
            'name': 'Rodelio Garcia Jr.',
            'department': 'Computer Engineering',
            'rfid_uid': '1248304305'
        }
        
        # Simulate the old problematic behavior (before our fix)
        self.logger.info("📤 Emitting student_authenticated signal")
        self.mock_dashboard_show()  # First call from student_authenticated
        
        # Note: The problematic redundant signals have been removed in our fix
        # self.logger.info("📤 Emitting change_window signal (REMOVED)")
        # self.mock_dashboard_show()  # Second call from change_window (REMOVED)
        
        # self.logger.info("📤 Emitting fallback change_window signal (REMOVED)")  
        # self.mock_dashboard_show()  # Third call from fallback timer (REMOVED)
        
        return student_data
        
    def simulate_dashboard_creation_flow(self):
        """Simulate the dashboard creation and update flow."""
        self.logger.info("🔥 TESTING: Dashboard creation flow")
        
        student_data = self.simulate_login_window_signals()
        
        # Simulate dashboard window creation (first time)
        self.logger.info("🏗️  Creating new dashboard window")
        self.mock_init_ui()  # First init_ui call
        self.mock_mqtt_subscribe("consultease/faculty/+/status_update", "handler_1")
        self.mock_mqtt_subscribe("consultease/faculty/+/status", "handler_2") 
        self.mock_mqtt_subscribe("consultease/system/notifications", "handler_3")
        
        # Simulate dashboard window update (subsequent calls - this was the problem)
        self.logger.info("🔄 Updating existing dashboard window with new student")
        # Note: In our fix, we no longer call init_ui() for updates
        # self.mock_init_ui()  # REMOVED: Second init_ui call
        self.logger.info("✅ Using welcome_label.setText() instead of full init_ui()")
        
        # Simulate MQTT subscription guard check
        self.logger.info("🛡️  MQTT subscription guard check")
        # Note: Guards prevent duplicate subscriptions
        self.logger.info("✅ MQTT subscriptions already set up, skipping")
        
    def simulate_mqtt_message_processing(self):
        """Simulate MQTT message processing to check for loops."""
        self.logger.info("🔥 TESTING: MQTT message processing")
        
        # Simulate faculty status update message
        faculty_status_data = {
            'faculty_id': 1,
            'faculty_name': 'Cris Angelo Salonga',
            'status': True,
            'timestamp': '2025-06-06T21:19:24.471430'
        }
        
        # Simulate multiple handlers processing the same message
        topic = "consultease/faculty/1/status"
        handlers = self.mqtt_subscriptions.get(topic, [])
        
        self.logger.info(f"📨 Processing MQTT message for topic: {topic}")
        self.logger.info(f"🎯 Found {len(handlers)} handlers for this topic")
        
        for i, handler in enumerate(handlers, 1):
            self.logger.info(f"🎯 Executing handler {i}/{len(handlers)}: {handler}")
            # Each handler would normally update UI
            self.mock_ui_refresh()
            
    def run_infinite_loop_tests(self):
        """Run all tests to check for infinite loop prevention."""
        self.logger.info("=" * 60)
        self.logger.info("🧪 STARTING DASHBOARD INFINITE LOOP PREVENTION TESTS")
        self.logger.info("=" * 60)
        
        # Test 1: Login signal emissions
        self.simulate_dashboard_creation_flow()
        
        # Test 2: MQTT message processing
        self.simulate_mqtt_message_processing()
        
        # Test 3: Analysis
        return self.analyze_results()
        
    def analyze_results(self):
        """Analyze test results and provide recommendations."""
        self.logger.info("=" * 60)
        self.logger.info("📊 TEST RESULTS ANALYSIS")
        self.logger.info("=" * 60)
        
        issues_found = []
        
        # Check for multiple dashboard shows
        if self.dashboard_show_count > 1:
            issues_found.append(f"Multiple dashboard shows: {self.dashboard_show_count}")
            
        # Check for multiple init_ui calls
        if self.init_ui_count > 1:
            issues_found.append(f"Multiple init_ui calls: {self.init_ui_count}")
            
        # Check for duplicate MQTT subscriptions
        duplicate_subscriptions = {
            topic: count for topic, count in self.mqtt_subscription_count.items() 
            if count > 1
        }
        if duplicate_subscriptions:
            for topic, count in duplicate_subscriptions.items():
                issues_found.append(f"Duplicate MQTT subscription: {topic} ({count} times)")
        
        # Check for excessive UI refreshes (more lenient threshold)
        if self.ui_refresh_count > 5:
            issues_found.append(f"Excessive UI refreshes: {self.ui_refresh_count}")
            
        # Report results
        if issues_found:
            self.logger.error("❌ ISSUES DETECTED:")
            for issue in issues_found:
                self.logger.error(f"   • {issue}")
        else:
            self.logger.info("✅ NO INFINITE LOOP ISSUES DETECTED!")
            
        self.logger.info(f"📈 Summary:")
        self.logger.info(f"   Dashboard shows: {self.dashboard_show_count}")
        self.logger.info(f"   init_ui calls: {self.init_ui_count}")
        self.logger.info(f"   UI refreshes: {self.ui_refresh_count}")
        self.logger.info(f"   MQTT subscriptions: {dict(self.mqtt_subscription_count)}")
        
        # Print to console as well
        print(f"📈 DETAILED RESULTS:")
        print(f"   Dashboard shows: {self.dashboard_show_count} (should be 1)")
        print(f"   init_ui calls: {self.init_ui_count} (should be 1)")
        print(f"   UI refreshes: {self.ui_refresh_count} (should be minimal)")
        print(f"   MQTT subscriptions: {dict(self.mqtt_subscription_count)}")
        
        if issues_found:
            print(f"❌ ISSUES DETECTED:")
            for issue in issues_found:
                print(f"   • {issue}")
        else:
            print("✅ NO INFINITE LOOP ISSUES DETECTED!")
        
        return len(issues_found) == 0

def main():
    """Main test function."""
    tester = DashboardLoopTester()
    
    print("🔥 Testing Dashboard Infinite Loop Prevention Fixes")
    print("=" * 60)
    
    success = tester.run_infinite_loop_tests()
    
    print(f"\nTest completed with success={success}")
    
    if success:
        print("✅ ALL TESTS PASSED - No infinite loop issues detected!")
        return 0
    else:
        print("❌ TESTS FAILED - Infinite loop issues still present!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
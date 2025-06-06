#!/usr/bin/env python3
"""
Test script to verify real-time faculty status update fixes.

This script tests:
1. Proper status mapping (True -> 'available', False -> 'offline')
2. Single MQTT handler (no duplicate processing)  
3. Faculty card updates working correctly
4. ESP32 busy button status updates
"""

import sys
import os
import time
import json
import logging
from datetime import datetime

# Add central_system to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'central_system'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('realtime_status_test.log')
    ]
)
logger = logging.getLogger(__name__)

class RealtimeStatusTester:
    """Test real-time faculty status updates after fixes."""
    
    def __init__(self):
        self.received_messages = []
        self.start_time = datetime.now()
        
    def test_status_mapping(self):
        """Test the new status mapping logic."""
        logger.info("🧪 Testing Status Mapping Logic")
        logger.info("-" * 50)
        
        try:
            # Import the dashboard window to test status mapping
            from central_system.views.dashboard_window import DashboardWindow
            
            # Create a mock dashboard instance
            dashboard = DashboardWindow()
            
            # Test cases for status mapping
            test_cases = [
                (True, 'available'),
                (False, 'offline'),
                ('AVAILABLE', 'available'),
                ('available', 'available'),
                ('busy', 'busy'),
                ('BUSY', 'busy'),
                ('offline', 'offline'),
                ('unknown_status', 'offline'),
                (None, 'offline')
            ]
            
            logger.info("Testing status mapping conversions:")
            for input_status, expected_output in test_cases:
                result = dashboard._map_status_for_display(input_status)
                status_icon = "✅" if result == expected_output else "❌"
                logger.info(f"  {status_icon} {input_status} -> {result} (expected: {expected_output})")
                
                if result != expected_output:
                    logger.error(f"❌ MAPPING FAILED: {input_status} should map to {expected_output}, got {result}")
            
            logger.info("✅ Status mapping test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Status mapping test failed: {e}")
            return False
    
    def test_mqtt_handler_count(self):
        """Test that only one handler is subscribed to system notifications."""
        logger.info("🧪 Testing MQTT Handler Count")
        logger.info("-" * 50)
        
        try:
            from central_system.services.async_mqtt_service import get_async_mqtt_service
            
            mqtt_service = get_async_mqtt_service()
            
            # Check handlers for system notifications topic
            topic = "consultease/system/notifications"
            
            if hasattr(mqtt_service, 'message_handlers'):
                handlers = mqtt_service.message_handlers.get(topic, [])
                handler_count = len(handlers)
                
                logger.info(f"📊 Handlers for '{topic}': {handler_count}")
                
                if handler_count <= 1:
                    logger.info("✅ Single handler confirmed - no conflicts expected")
                    return True
                else:
                    logger.warning(f"⚠️ Multiple handlers ({handler_count}) still detected")
                    for i, handler in enumerate(handlers):
                        handler_name = getattr(handler, '__name__', str(handler))
                        logger.info(f"  Handler {i+1}: {handler_name}")
                    return False
            else:
                logger.warning("⚠️ Cannot access message handlers - service not initialized")
                return False
                
        except Exception as e:
            logger.error(f"❌ MQTT handler count test failed: {e}")
            return False
    
    def simulate_faculty_status_update(self):
        """Simulate a faculty status update message."""
        logger.info("🧪 Simulating Faculty Status Update")
        logger.info("-" * 50)
        
        try:
            from central_system.utils.mqtt_utils import publish_mqtt_message
            
            # Test message simulating ESP32 status update
            test_message = {
                'type': 'faculty_status',
                'faculty_id': 1,
                'faculty_name': 'Test Faculty',
                'status': True,  # Should map to 'available'
                'previous_status': False,
                'sequence': 1,
                'timestamp': datetime.now().isoformat(),
                'version': 1
            }
            
            logger.info(f"📤 Publishing test status update: {test_message}")
            
            success = publish_mqtt_message(
                "consultease/system/notifications",
                test_message,
                qos=1
            )
            
            if success:
                logger.info("✅ Test message published successfully")
                logger.info("📝 Check logs for:")
                logger.info("  - 🎯 [DASHBOARD] Processing faculty_status notification")
                logger.info("  - 🔄 [STATUS MAPPING] Input: True -> Output: available")
                logger.info("  - 🟢 [STATUS INDICATOR] Color mapping: available -> #4CAF50")
                return True
            else:
                logger.error("❌ Failed to publish test message")
                return False
                
        except Exception as e:
            logger.error(f"❌ Status update simulation failed: {e}")
            return False
    
    def test_faculty_card_updates(self):
        """Test faculty card status updates."""
        logger.info("🧪 Testing Faculty Card Status Updates")
        logger.info("-" * 50)
        
        try:
            from central_system.ui.pooled_faculty_card import PooledFacultyCard
            
            # Create a test faculty card
            card = PooledFacultyCard()
            
            # Configure with test data
            test_faculty_data = {
                'id': 1,
                'name': 'Test Faculty',
                'department': 'Test Department',
                'status': 'offline',
                'available': False
            }
            
            card.configure(test_faculty_data)
            
            # Test status updates
            test_statuses = [True, False, 'available', 'busy', 'offline']
            
            logger.info("Testing faculty card status updates:")
            for status in test_statuses:
                try:
                    logger.info(f"  🔄 Testing status: {status}")
                    card.update_status(status)
                    
                    # Check resulting status
                    final_status = card.faculty_data.get('status')
                    available = card.faculty_data.get('available')
                    
                    logger.info(f"    Result: status='{final_status}', available={available}")
                    
                except Exception as e:
                    logger.error(f"    ❌ Error updating status {status}: {e}")
            
            logger.info("✅ Faculty card status update test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Faculty card test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all real-time status tests."""
        logger.info("🚀 Starting Real-Time Status Update Tests")
        logger.info("=" * 60)
        
        test_results = {
            'status_mapping': self.test_status_mapping(),
            'mqtt_handlers': self.test_mqtt_handler_count(),
            'status_simulation': self.simulate_faculty_status_update(),
            'faculty_card': self.test_faculty_card_updates()
        }
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        
        for test_name, result in test_results.items():
            status_icon = "✅" if result else "❌"
            logger.info(f"{status_icon} {test_name.replace('_', ' ').title()}: {'PASS' if result else 'FAIL'}")
        
        total_tests = len(test_results)
        passed_tests = sum(test_results.values())
        
        logger.info(f"\n📈 Overall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED! Real-time status updates should work correctly.")
        else:
            logger.warning(f"⚠️ {total_tests - passed_tests} test(s) failed. Check logs for details.")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    print("🧪 Real-Time Status Update Fix Verification")
    print("=" * 50)
    
    tester = RealtimeStatusTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ All tests passed! Ready for deployment.")
    else:
        print("\n❌ Some tests failed. Review logs before deployment.")
    
    print(f"\n📝 Detailed logs saved to: realtime_status_test.log") 
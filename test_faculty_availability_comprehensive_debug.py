#!/usr/bin/env python3
"""
Comprehensive Faculty Availability Real-Time Debug Script

This script tests the complete chain of faculty availability updates:
1. ESP32 status simulation
2. Faculty Controller processing
3. MQTT message publishing 
4. Dashboard subscription and UI updates

Run this to identify exactly where the real-time updates are failing.
"""

import sys
import os
import time
import logging
import json
import threading
from datetime import datetime

# Add the central_system path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'central_system'))

from central_system.models import Faculty, get_db
from central_system.controllers.faculty_controller import FacultyController
from central_system.utils.mqtt_utils import publish_mqtt_message, subscribe_to_topic
from central_system.services.async_mqtt_service import get_async_mqtt_service

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FacultyAvailabilityDebugger:
    """Comprehensive debugger for faculty availability real-time system."""
    
    def __init__(self):
        self.received_messages = []
        self.test_faculty = None
        self.faculty_controller = None
        self.mqtt_service = None
        self.message_lock = threading.Lock()
        
    def run_comprehensive_test(self):
        """Run the complete debugging test suite."""
        logger.info("🔍 FACULTY AVAILABILITY REAL-TIME DEBUG - COMPREHENSIVE TEST")
        logger.info("=" * 80)
        
        try:
            # Step 1: Initialize services
            if not self._initialize_services():
                return False
                
            # Step 2: Find test faculty
            if not self._find_test_faculty():
                return False
                
            # Step 3: Set up MQTT monitoring
            self._setup_mqtt_monitoring()
            
            # Step 4: Test Faculty Controller directly
            self._test_faculty_controller_direct()
            
            # Step 5: Test ESP32 MQTT simulation  
            self._test_esp32_mqtt_simulation()
            
            # Step 6: Test Dashboard processing simulation
            self._test_dashboard_processing_simulation()
            
            # Step 7: Analyze results
            self._analyze_test_results()
            
        except Exception as e:
            logger.error(f"❌ Critical error in comprehensive test: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
            
    def _initialize_services(self):
        """Initialize MQTT service and Faculty Controller."""
        logger.info("\n1️⃣ INITIALIZING SERVICES")
        logger.info("-" * 40)
        
        try:
            # Initialize MQTT service
            self.mqtt_service = get_async_mqtt_service()
            if not self.mqtt_service:
                logger.error("❌ Failed to get MQTT service")
                return False
                
            # Start MQTT service if not running
            if not self.mqtt_service.running:
                self.mqtt_service.start()
                time.sleep(2)
                
            # Connect to MQTT broker
            if not self.mqtt_service.is_connected:
                self.mqtt_service.connect()
                time.sleep(3)
                
            if not self.mqtt_service.is_connected:
                logger.error("❌ MQTT service failed to connect")
                return False
                
            logger.info(f"✅ MQTT service connected: {self.mqtt_service.is_connected}")
            
            # Initialize Faculty Controller
            self.faculty_controller = FacultyController()
            self.faculty_controller.start()
            
            logger.info("✅ Faculty Controller initialized and started")
            return True
            
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            return False
            
    def _find_test_faculty(self):
        """Find a faculty member to test with."""
        logger.info("\n2️⃣ FINDING TEST FACULTY")
        logger.info("-" * 40)
        
        try:
            with get_db() as db:
                faculties = db.query(Faculty).all()
                
            if not faculties:
                logger.error("❌ No faculty found in database")
                return False
                
            self.test_faculty = faculties[0]
            logger.info(f"✅ Using test faculty: {self.test_faculty.name} (ID: {self.test_faculty.id})")
            logger.info(f"   Current status: {self.test_faculty.status}")
            logger.info(f"   Department: {self.test_faculty.department}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to find test faculty: {e}")
            return False
            
    def _setup_mqtt_monitoring(self):
        """Set up MQTT message monitoring on all relevant topics."""
        logger.info("\n3️⃣ SETTING UP MQTT MONITORING")
        logger.info("-" * 40)
        
        # Topics to monitor
        topics = [
            # ESP32 raw messages
            f"consultease/faculty/{self.test_faculty.id}/status",
            f"consultease/faculty/{self.test_faculty.id}/mac_status",
            f"consultease/faculty/{self.test_faculty.id}/heartbeat",
            
            # Faculty Controller processed messages
            f"consultease/faculty/{self.test_faculty.id}/status_update",
            
            # System notifications
            "consultease/system/notifications",
            
            # Legacy topics
            f"faculty/{self.test_faculty.id}/status",
        ]
        
        def message_handler(topic, data):
            with self.message_lock:
                message_info = {
                    'timestamp': datetime.now().isoformat(),
                    'topic': topic,
                    'data': data,
                    'data_type': type(data).__name__
                }
                self.received_messages.append(message_info)
                logger.info(f"📨 [MQTT MONITOR] {topic} -> {data}")
        
        # Subscribe to all topics
        for topic in topics:
            try:
                subscribe_to_topic(topic, message_handler)
                logger.info(f"✅ Subscribed to: {topic}")
            except Exception as e:
                logger.error(f"❌ Failed to subscribe to {topic}: {e}")
                
        # Wait for subscriptions to be processed
        time.sleep(2)
        logger.info("✅ MQTT monitoring setup complete")
        
    def _test_faculty_controller_direct(self):
        """Test Faculty Controller methods directly."""
        logger.info("\n4️⃣ TESTING FACULTY CONTROLLER DIRECT")
        logger.info("-" * 40)
        
        try:
            faculty_id = self.test_faculty.id
            original_status = self.test_faculty.status
            
            logger.info(f"🧪 Testing direct Faculty Controller update")
            logger.info(f"   Faculty: {self.test_faculty.name} (ID: {faculty_id})")
            logger.info(f"   Original status: {original_status}")
            
            # Test setting to available
            logger.info("🔄 Setting status to True (Available)")
            result = self.faculty_controller.update_faculty_status(faculty_id, True)
            logger.info(f"   Result: {result}")
            
            time.sleep(2)
            
            # Test setting to unavailable
            logger.info("🔄 Setting status to False (Unavailable)")
            result = self.faculty_controller.update_faculty_status(faculty_id, False)
            logger.info(f"   Result: {result}")
            
            time.sleep(2)
            
            # Test setting back to original
            logger.info(f"🔄 Setting status back to original: {original_status}")
            result = self.faculty_controller.update_faculty_status(faculty_id, original_status)
            logger.info(f"   Result: {result}")
            
            time.sleep(2)
            
            logger.info("✅ Faculty Controller direct test complete")
            
        except Exception as e:
            logger.error(f"❌ Faculty Controller direct test failed: {e}")
            
    def _test_esp32_mqtt_simulation(self):
        """Simulate ESP32 MQTT messages."""
        logger.info("\n5️⃣ TESTING ESP32 MQTT SIMULATION")
        logger.info("-" * 40)
        
        try:
            faculty_id = self.test_faculty.id
            faculty_name = self.test_faculty.name
            topic = f"consultease/faculty/{faculty_id}/status"
            
            # Test messages in ESP32 format
            test_messages = [
                {
                    "description": "ESP32 Available Message",
                    "payload": {
                        "faculty_id": faculty_id,
                        "faculty_name": faculty_name,
                        "present": True,
                        "status": "AVAILABLE",
                        "timestamp": int(time.time() * 1000),
                        "ntp_sync_status": "SYNCED",
                        "in_grace_period": False,
                        "detailed_status": "AVAILABLE"
                    }
                },
                {
                    "description": "ESP32 Away Message", 
                    "payload": {
                        "faculty_id": faculty_id,
                        "faculty_name": faculty_name,
                        "present": False,
                        "status": "AWAY",
                        "timestamp": int(time.time() * 1000),
                        "ntp_sync_status": "SYNCED",
                        "in_grace_period": False,
                        "detailed_status": "AWAY"
                    }
                },
                {
                    "description": "ESP32 Busy Message",
                    "payload": {
                        "faculty_id": faculty_id,
                        "faculty_name": faculty_name,
                        "present": True,
                        "status": "BUSY",
                        "timestamp": int(time.time() * 1000),
                        "ntp_sync_status": "SYNCED",
                        "in_grace_period": False,
                        "detailed_status": "BUSY"
                    }
                }
            ]
            
            for i, test_msg in enumerate(test_messages, 1):
                logger.info(f"🚀 Test {i}/3: {test_msg['description']}")
                logger.info(f"   Topic: {topic}")
                logger.info(f"   Payload: {json.dumps(test_msg['payload'], indent=2)}")
                
                # Publish the message
                success = publish_mqtt_message(topic, test_msg['payload'])
                logger.info(f"   Publish result: {success}")
                
                # Wait for processing
                time.sleep(3)
                
                # Check database status
                with get_db() as db:
                    updated_faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
                    if updated_faculty:
                        logger.info(f"   Database status now: {updated_faculty.status}")
                        logger.info(f"   Last seen: {updated_faculty.last_seen}")
                    else:
                        logger.error(f"   ❌ Faculty not found in database")
                        
                logger.info("")
                
            logger.info("✅ ESP32 MQTT simulation complete")
            
        except Exception as e:
            logger.error(f"❌ ESP32 MQTT simulation failed: {e}")
            
    def _test_dashboard_processing_simulation(self):
        """Test dashboard-style status update processing."""
        logger.info("\n6️⃣ TESTING DASHBOARD PROCESSING SIMULATION")
        logger.info("-" * 40)
        
        try:
            faculty_id = self.test_faculty.id
            faculty_name = self.test_faculty.name
            
            # Test dashboard-style processed notifications
            dashboard_messages = [
                {
                    "topic": f"consultease/faculty/{faculty_id}/status_update",
                    "description": "Dashboard Processed Update - Available",
                    "payload": {
                        "type": "faculty_status",
                        "faculty_id": faculty_id,
                        "faculty_name": faculty_name,
                        "status": True,
                        "previous_status": False,
                        "sequence": 1,
                        "timestamp": datetime.now().isoformat()
                    }
                },
                {
                    "topic": "consultease/system/notifications",
                    "description": "System Notification - Unavailable",
                    "payload": {
                        "type": "faculty_status",
                        "faculty_id": faculty_id,
                        "faculty_name": faculty_name,
                        "status": False,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            ]
            
            for i, test_msg in enumerate(dashboard_messages, 1):
                logger.info(f"📊 Dashboard Test {i}/{len(dashboard_messages)}: {test_msg['description']}")
                logger.info(f"   Topic: {test_msg['topic']}")
                logger.info(f"   Payload: {json.dumps(test_msg['payload'], indent=2)}")
                
                # Publish the message
                success = publish_mqtt_message(test_msg['topic'], test_msg['payload'])
                logger.info(f"   Publish result: {success}")
                
                # Wait for processing
                time.sleep(2)
                
            logger.info("✅ Dashboard processing simulation complete")
            
        except Exception as e:
            logger.error(f"❌ Dashboard processing simulation failed: {e}")
            
    def _analyze_test_results(self):
        """Analyze all test results and provide recommendations."""
        logger.info("\n7️⃣ ANALYZING TEST RESULTS")
        logger.info("-" * 40)
        
        # Sort messages by timestamp
        sorted_messages = sorted(self.received_messages, key=lambda x: x['timestamp'])
        
        logger.info(f"📊 Total messages received: {len(sorted_messages)}")
        
        if not sorted_messages:
            logger.error("❌ NO MQTT MESSAGES RECEIVED!")
            logger.error("   This indicates a problem with:")
            logger.error("   1. MQTT service connectivity")
            logger.error("   2. MQTT subscriptions not working")
            logger.error("   3. Faculty Controller not processing messages")
            logger.error("   4. Messages not being published")
            return
            
        # Analyze message flow
        logger.info("\n📋 RECEIVED MESSAGES:")
        for i, msg in enumerate(sorted_messages, 1):
            logger.info(f"{i:2d}. {msg['timestamp']} | {msg['topic']}")
            logger.info(f"    Data: {msg['data']}")
            logger.info("")
            
        # Check for expected message flow
        esp32_messages = [m for m in sorted_messages if '/status' in m['topic'] and 'status_update' not in m['topic']]
        processed_messages = [m for m in sorted_messages if 'status_update' in m['topic']]
        system_notifications = [m for m in sorted_messages if 'system/notifications' in m['topic']]
        
        logger.info("🔍 MESSAGE FLOW ANALYSIS:")
        logger.info(f"   ESP32 status messages: {len(esp32_messages)}")
        logger.info(f"   Processed status updates: {len(processed_messages)}")
        logger.info(f"   System notifications: {len(system_notifications)}")
        
        # Recommendations
        logger.info("\n💡 ANALYSIS & RECOMMENDATIONS:")
        
        if esp32_messages and not processed_messages:
            logger.warning("⚠️ ESP32 messages received but NO processed updates!")
            logger.warning("   - Faculty Controller may not be processing ESP32 messages")
            logger.warning("   - Check Faculty Controller handle_faculty_status_update method")
            logger.warning("   - Verify faculty exists in database")
            
        elif esp32_messages and processed_messages:
            logger.info("✅ ESP32 messages AND processed updates found!")
            logger.info("   - Faculty Controller is working correctly")
            logger.info("   - Real-time system should be functional")
            
        if not esp32_messages:
            logger.warning("⚠️ No ESP32 messages received")
            logger.warning("   - Check MQTT publishing in ESP32 simulation")
            logger.warning("   - Verify MQTT broker connectivity")
            
        if processed_messages and not system_notifications:
            logger.warning("⚠️ Processed updates but no system notifications")
            logger.warning("   - Dashboard may not receive updates")
            logger.warning("   - Check Faculty Controller notification publishing")
            
        # Final database state
        logger.info("\n📊 FINAL DATABASE STATE:")
        try:
            with get_db() as db:
                final_faculty = db.query(Faculty).filter(Faculty.id == self.test_faculty.id).first()
                if final_faculty:
                    logger.info(f"   Faculty: {final_faculty.name}")
                    logger.info(f"   Status: {final_faculty.status}")
                    logger.info(f"   Last seen: {final_faculty.last_seen}")
                else:
                    logger.error("   ❌ Faculty not found in database")
        except Exception as e:
            logger.error(f"   ❌ Error checking database: {e}")

if __name__ == "__main__":
    # Note about Raspberry Pi requirement
    logger.info("⚠️ IMPORTANT: This system is designed to run on Raspberry Pi")
    logger.info("⚠️ For complete testing, run this on the actual Raspberry Pi deployment")
    logger.info("")
    
    debugger = FacultyAvailabilityDebugger()
    debugger.run_comprehensive_test() 
#!/usr/bin/env python3
"""
MQTT Status Debug Script
Tests the complete faculty status update flow to identify where it's breaking.
"""

import sys
import os
import time
import logging
import json
import paho.mqtt.client as mqtt
from datetime import datetime

# Add the central_system path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'central_system'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MQTTStatusDebugger:
    """Debug MQTT status messages flow."""
    
    def __init__(self):
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.received_messages = {}
        self.faculty_id = 1
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("🔌 Connected to MQTT broker")
            # Subscribe to all faculty status related topics
            topics = [
                f"consultease/faculty/{self.faculty_id}/status",
                f"consultease/faculty/{self.faculty_id}/status_update", 
                "consultease/system/notifications",
                "consultease/dashboard/updates"
            ]
            
            for topic in topics:
                client.subscribe(topic)
                logger.info(f"📡 Subscribed to: {topic}")
        else:
            logger.error(f"❌ MQTT connection failed with code: {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            
            logger.info(f"📨 MQTT Message Received:")
            logger.info(f"   Topic: {topic}")
            logger.info(f"   Payload: {payload}")
            
            # Store message for analysis
            if topic not in self.received_messages:
                self.received_messages[topic] = []
            self.received_messages[topic].append({
                'payload': payload,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error processing MQTT message: {e}")
    
    def test_faculty_controller_direct(self):
        """Test Faculty Controller directly without MQTT."""
        logger.info("🧪 Testing Faculty Controller Direct Access")
        logger.info("-" * 50)
        
        try:
            from central_system.models import Faculty, get_db
            from central_system.controllers.faculty_controller import FacultyController
            
            # Check if faculty exists
            db = get_db()
            faculty = db.query(Faculty).filter(Faculty.id == self.faculty_id).first()
            
            if not faculty:
                logger.error(f"❌ Faculty with ID {self.faculty_id} not found!")
                return False
            
            logger.info(f"✅ Faculty found: {faculty.name}")
            logger.info(f"   Current status: {'Available' if faculty.status else 'Unavailable'}")
            logger.info(f"   Last seen: {faculty.last_seen}")
            
            # Test Faculty Controller
            controller = FacultyController()
            
            # Simulate ESP32 status message
            esp32_message = {
                "faculty_id": self.faculty_id,
                "faculty_name": faculty.name,
                "present": True,
                "status": "AVAILABLE",
                "timestamp": int(time.time() * 1000),
                "ntp_sync_status": "SYNCED"
            }
            
            logger.info("🔄 Testing Faculty Controller MQTT handler...")
            logger.info(f"   Simulating message: {esp32_message}")
            
            # Call the handler directly
            topic = f"consultease/faculty/{self.faculty_id}/status"
            controller.handle_faculty_status_update(topic, esp32_message)
            
            # Check database update
            db.refresh(faculty)
            logger.info(f"   New status: {'Available' if faculty.status else 'Unavailable'}")
            logger.info(f"   Status changed: {faculty.status == True}")
            
            db.close()
            return True
            
    except Exception as e:
            logger.error(f"❌ Faculty Controller test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def test_database_faculty_status_update(self):
        """Test direct database faculty status update."""
        logger.info("🧪 Testing Database Faculty Status Update")
        logger.info("-" * 50)
        
        try:
            from central_system.models import Faculty, get_db
            
            db = get_db()
            faculty = db.query(Faculty).filter(Faculty.id == self.faculty_id).first()
            
            if not faculty:
                logger.error(f"❌ Faculty with ID {self.faculty_id} not found!")
                return False
            
            original_status = faculty.status
            logger.info(f"📝 Original status: {'Available' if original_status else 'Unavailable'}")
            
            # Toggle status
            new_status = not original_status
            faculty.status = new_status
            faculty.last_seen = datetime.now()
            db.commit()
            
            logger.info(f"📝 New status: {'Available' if new_status else 'Unavailable'}")
            logger.info("✅ Database update successful")
            
            db.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Database update test failed: {e}")
            return False
    
    def test_mqtt_publishing(self):
        """Test MQTT message publishing."""
        logger.info("🧪 Testing MQTT Message Publishing")
        logger.info("-" * 50)
        
        try:
            # Connect to MQTT broker
            broker_configs = [
                {"host": "localhost", "port": 1883},
                {"host": "127.0.0.1", "port": 1883}, 
                {"host": "192.168.100.3", "port": 1883}
            ]
            
            connected = False
            for config in broker_configs:
                try:
                    self.mqtt_client.connect(config["host"], config["port"], 60)
                    self.mqtt_client.loop_start()
                    time.sleep(2)  # Wait for connection
                    
                    if self.mqtt_client.is_connected():
                        logger.info(f"✅ Connected to MQTT broker: {config['host']}:{config['port']}")
                        connected = True
                        break
                except Exception as e:
                    logger.debug(f"Failed to connect to {config['host']}:{config['port']}: {e}")
            
            if not connected:
                logger.error("❌ Could not connect to any MQTT broker")
                return False
            
            # Simulate ESP32 status message
            status_message = {
                "faculty_id": self.faculty_id,
                "faculty_name": "Cris Angelo Salonga",
                "present": True,
                "status": "AVAILABLE",
                "timestamp": int(time.time() * 1000),
                "ntp_sync_status": "SYNCED"
            }
            
            topic = f"consultease/faculty/{self.faculty_id}/status"
            message = json.dumps(status_message)
            
            logger.info(f"📡 Publishing to topic: {topic}")
            logger.info(f"📊 Message: {message}")
            
            result = self.mqtt_client.publish(topic, message, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("✅ Message published successfully")
                
                # Wait for potential responses
                logger.info("⏳ Waiting for responses...")
                time.sleep(5)
                
                # Check received messages
                if self.received_messages:
                    logger.info("📨 Received messages:")
                    for topic, messages in self.received_messages.items():
                        logger.info(f"   Topic: {topic}")
                        for msg in messages:
                            logger.info(f"     {msg['timestamp']}: {msg['payload']}")
                else:
                    logger.warning("⚠️ No messages received")
                
                return True
            else:
                logger.error(f"❌ Message publish failed with code: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"❌ MQTT publishing test failed: {e}")
            return False
        finally:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except:
                pass
    
    def run_all_tests(self):
        """Run all debugging tests."""
        logger.info("🔍 MQTT STATUS DEBUG TESTS")
        logger.info("=" * 60)
        
        tests = [
            ("Database Faculty Status Update", self.test_database_faculty_status_update),
            ("Faculty Controller Direct", self.test_faculty_controller_direct),
            ("MQTT Publishing", self.test_mqtt_publishing)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            logger.info(f"\n🧪 Running: {test_name}")
            logger.info("-" * 50)
            results[test_name] = test_func()
        
        # Summary
        logger.info("\n📊 TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        
        all_passed = True
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status}: {test_name}")
            if not result:
                all_passed = False
        
        if all_passed:
            logger.info("\n🎉 All tests passed! Faculty status system should be working.")
        else:
            logger.info("\n⚠️ Some tests failed. Check the Faculty Controller or MQTT setup.")
        
        return results

if __name__ == "__main__":
    debugger = MQTTStatusDebugger()
    debugger.run_all_tests() 
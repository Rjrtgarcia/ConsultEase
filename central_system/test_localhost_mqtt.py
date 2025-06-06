#!/usr/bin/env python3
"""
Test script to verify localhost MQTT broker configuration.
This script tests that the central system can connect to the MQTT broker on localhost.
"""

import sys
import os
import time
import logging

# Add the central_system directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_localhost_mqtt_config():
    """Test the localhost MQTT configuration."""
    print("🚀 Testing Localhost MQTT Configuration")
    print("=" * 50)
    
    try:
        # Test 1: Check MQTT broker auto-detection
        print("\n1. Testing MQTT Broker Auto-Detection...")
        from utils.mqtt_broker_detection import auto_detect_mqtt_broker, verify_broker_connectivity
        
        detected_broker = auto_detect_mqtt_broker()
        print(f"   Detected broker: {detected_broker}")
        
        success, message = verify_broker_connectivity(detected_broker)
        print(f"   {message}")
        
        # Test 2: Test configuration manager
        print("\n2. Testing Configuration Manager...")
        from utils.config_manager import get_config
        
        broker_host = get_config('mqtt.broker_host', 'localhost')
        broker_port = get_config('mqtt.broker_port', 1883)
        print(f"   Configured broker: {broker_host}:{broker_port}")
        
        # Test 3: Test async MQTT service
        print("\n3. Testing Async MQTT Service...")
        from services.async_mqtt_service import get_async_mqtt_service
        
        mqtt_service = get_async_mqtt_service()
        print(f"   MQTT service broker: {mqtt_service.broker_host}:{mqtt_service.broker_port}")
        
        # Start the service
        print("   Starting MQTT service...")
        mqtt_service.start()
        
        # Wait for connection
        timeout = 10
        start_time = time.time()
        while not mqtt_service.is_connected and (time.time() - start_time) < timeout:
            time.sleep(0.5)
            print("   ⏳ Waiting for connection...")
        
        if mqtt_service.is_connected:
            print("   ✅ MQTT service connected successfully")
            
            # Test 4: Test basic pub/sub
            print("\n4. Testing Basic Publish/Subscribe...")
            
            # Set up a test handler
            test_messages = []
            
            def test_handler(topic, data):
                test_messages.append({'topic': topic, 'data': data})
                print(f"   📨 Received: {topic} -> {data}")
            
            # Subscribe to test topic
            mqtt_service.register_topic_handler("test/localhost", test_handler)
            time.sleep(1)  # Wait for subscription
            
            # Publish test message
            mqtt_service.publish_message("test/localhost", {"message": "Hello from localhost!", "timestamp": time.time()})
            
            # Wait for message
            time.sleep(2)
            
            if test_messages:
                print("   ✅ Publish/Subscribe test successful")
            else:
                print("   ⚠️ No messages received - check MQTT broker")
            
        else:
            print("   ❌ MQTT service failed to connect")
            return False
        
        # Test 5: Test MQTT utilities
        print("\n5. Testing MQTT Utilities...")
        from utils.mqtt_utils import publish_mqtt_message, is_mqtt_connected
        
        connected = is_mqtt_connected()
        print(f"   MQTT connected: {connected}")
        
        if connected:
            result = publish_mqtt_message("test/utils", {"test": "utilities", "success": True})
            print(f"   Publish result: {result}")
        
        # Cleanup
        print("\n6. Cleaning up...")
        mqtt_service.stop()
        print("   ✅ MQTT service stopped")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"\n❌ Test failed: {e}")
        return False


def test_network_discovery():
    """Test the network discovery capabilities."""
    print("\n🔍 Testing Network Discovery")
    print("=" * 30)
    
    try:
        from utils.mqtt_broker_detection import MQTTBrokerDetector
        
        detector = MQTTBrokerDetector()
        
        # Test localhost detection
        print("Testing localhost detection...")
        localhost_broker = detector._check_localhost_brokers()
        print(f"Localhost broker: {localhost_broker}")
        
        # Test network interface detection
        print("Testing network interfaces...")
        local_ips = detector._get_local_ip_addresses()
        print(f"Local IPs: {local_ips}")
        
        # Test full detection
        print("Running full detection...")
        detected = detector.detect_broker()
        print(f"Detected broker: {detected}")
        
    except Exception as e:
        print(f"Network discovery test failed: {e}")


def main():
    """Main test function."""
    print("ConsultEase - Localhost MQTT Configuration Test")
    print("=" * 60)
    
    # Test localhost MQTT configuration
    success = test_localhost_mqtt_config()
    
    # Test network discovery
    test_network_discovery()
    
    if success:
        print("\n✅ All tests passed! Localhost MQTT configuration is working.")
        return 0
    else:
        print("\n❌ Some tests failed. Check MQTT broker setup.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 
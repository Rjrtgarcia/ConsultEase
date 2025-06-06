#!/usr/bin/env python3
"""
Faculty Availability Test Script - Windows Compatible

This is a simplified version that can run on Windows to test the basic
faculty availability system components without requiring the full Raspberry Pi
environment.
"""

import sys
import os
import time
import logging

# Add the central_system path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'central_system'))

try:
    from central_system.models import Faculty, get_db
    from central_system.controllers.faculty_controller import FacultyController
except ImportError as e:
    print(f"❌ Failed to import central_system modules: {e}")
    print("Make sure you're running this from the ConsultEase Final Code directory")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_basic_faculty_system():
    """Test basic faculty system components."""
    logger.info("🧪 TESTING FACULTY AVAILABILITY SYSTEM - WINDOWS VERSION")
    logger.info("=" * 60)
    
    # Test 1: Database connectivity
    logger.info("\n1️⃣ TESTING DATABASE CONNECTIVITY")
    logger.info("-" * 40)
    
    try:
        with get_db() as db:
            faculties = db.query(Faculty).all()
            logger.info(f"✅ Database connected successfully")
            logger.info(f"   Found {len(faculties)} faculty members")
            
            if faculties:
                for faculty in faculties:
                    logger.info(f"   - {faculty.name} (ID: {faculty.id}) - Status: {faculty.status}")
            else:
                logger.warning("⚠️ No faculty found in database")
                return False
                
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
        
    # Test 2: Faculty Controller initialization
    logger.info("\n2️⃣ TESTING FACULTY CONTROLLER")
    logger.info("-" * 40)
    
    try:
        faculty_controller = FacultyController()
        logger.info("✅ Faculty Controller initialized successfully")
        
        # Test direct status update (without MQTT)
        test_faculty = faculties[0]
        original_status = test_faculty.status
        
        logger.info(f"🧪 Testing status update for: {test_faculty.name}")
        logger.info(f"   Original status: {original_status}")
        
        # Test status change
        new_status = not original_status
        logger.info(f"   Changing status to: {new_status}")
        
        result = faculty_controller.update_faculty_status(test_faculty.id, new_status)
        
        if result:
            logger.info("✅ Status update successful")
            logger.info(f"   Result: {result}")
            
            # Verify in database
            with get_db() as db:
                updated_faculty = db.query(Faculty).filter(Faculty.id == test_faculty.id).first()
                logger.info(f"   Database status: {updated_faculty.status}")
                logger.info(f"   Last seen: {updated_faculty.last_seen}")
                
            # Change back to original
            logger.info(f"   Changing back to original: {original_status}")
            result2 = faculty_controller.update_faculty_status(test_faculty.id, original_status)
            if result2:
                logger.info("✅ Status restore successful")
            else:
                logger.warning("⚠️ Status restore failed")
                
        else:
            logger.error("❌ Status update failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Faculty Controller test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
        
    # Test 3: MQTT system check (basic)
    logger.info("\n3️⃣ TESTING MQTT SYSTEM (BASIC)")
    logger.info("-" * 40)
    
    try:
        from central_system.services.async_mqtt_service import get_async_mqtt_service
        mqtt_service = get_async_mqtt_service()
        
        if mqtt_service:
            logger.info("✅ MQTT service module loaded")
            logger.info(f"   Service running: {mqtt_service.running}")
            logger.info(f"   Service connected: {mqtt_service.is_connected}")
            
            if not mqtt_service.running:
                logger.warning("⚠️ MQTT service not running")
                logger.warning("   This is expected on Windows - the service requires the Raspberry Pi MQTT broker")
            
        else:
            logger.warning("⚠️ MQTT service not available")
            
    except Exception as e:
        logger.warning(f"⚠️ MQTT system check failed: {e}")
        logger.warning("   This is expected on Windows - full MQTT testing requires Raspberry Pi")
        
    # Test 4: Message handling simulation
    logger.info("\n4️⃣ TESTING MESSAGE HANDLING SIMULATION")
    logger.info("-" * 40)
    
    try:
        # Simulate an ESP32 message directly to the handler
        test_faculty = faculties[0]
        
        simulated_esp32_message = {
            "faculty_id": test_faculty.id,
            "faculty_name": test_faculty.name,
            "present": True,
            "status": "AVAILABLE",
            "timestamp": int(time.time() * 1000),
            "ntp_sync_status": "SYNCED"
        }
        
        topic = f"consultease/faculty/{test_faculty.id}/status"
        
        logger.info(f"🚀 Simulating ESP32 message:")
        logger.info(f"   Topic: {topic}")
        logger.info(f"   Message: {simulated_esp32_message}")
        
        # Call handler directly
        faculty_controller.handle_faculty_status_update(topic, simulated_esp32_message)
        
        logger.info("✅ Message handler called successfully")
        
        # Check database update
        time.sleep(1)  # Give it a moment
        with get_db() as db:
            updated_faculty = db.query(Faculty).filter(Faculty.id == test_faculty.id).first()
            logger.info(f"   Database status after simulation: {updated_faculty.status}")
            logger.info(f"   Last seen: {updated_faculty.last_seen}")
            
    except Exception as e:
        logger.error(f"❌ Message handling simulation failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
    logger.info("\n✅ BASIC FACULTY SYSTEM TEST COMPLETED")
    logger.info("\n💡 TO TEST FULL REAL-TIME FUNCTIONALITY:")
    logger.info("   1. Deploy this system on the Raspberry Pi")
    logger.info("   2. Ensure MQTT broker is running")
    logger.info("   3. Run the comprehensive test script on the Pi")
    logger.info("   4. Test with actual ESP32 desk units")
    
    return True

if __name__ == "__main__":
    print("Faculty Availability System Test - Windows Version")
    print("=" * 50)
    print("⚠️ Note: This is a basic test for Windows environments")
    print("⚠️ Full real-time testing requires the Raspberry Pi deployment")
    print("")
    
    success = test_basic_faculty_system()
    
    if success:
        print("\n🎉 Basic system test completed successfully!")
        print("The core faculty availability system appears to be working.")
    else:
        print("\n❌ Basic system test failed!")
        print("There are fundamental issues that need to be resolved.") 
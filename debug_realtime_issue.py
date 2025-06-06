#!/usr/bin/env python3
"""
Debug script to analyze the real-time faculty status update issue.
This script will help identify why faculty cards are not updating in real-time.
"""

import sys
import os
import time
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_faculty_controller_status_flow():
    """Test the Faculty Controller status update flow"""
    print("🔍 Testing Faculty Controller Status Update Flow...")
    print("=" * 60)
    
    try:
        # Import required modules
        from central_system.controllers.faculty_controller import get_faculty_controller, set_faculty_controller, FacultyController
        from central_system.models.base import get_db
        from central_system.models.faculty import Faculty
        
        # Test 1: Check global controller
        print("\n1️⃣ Testing Global Faculty Controller...")
        global_controller = get_faculty_controller()
        if global_controller:
            print(f"✅ Global controller exists: {type(global_controller)}")
            print(f"   - Started: {getattr(global_controller, '_started', False)}")
            print(f"   - MQTT subscribed: {hasattr(global_controller, '_mqtt_subscribed')}")
        else:
            print("❌ No global controller found")
            
        # Test 2: Check database status
        print("\n2️⃣ Testing Database Faculty Status...")
        db = get_db()
        try:
            faculty = db.query(Faculty).filter(Faculty.id == 1).first()
            if faculty:
                print(f"✅ Faculty ID 1 found: {faculty.name}")
                print(f"   - Status: {faculty.status}")
                print(f"   - Last seen: {faculty.last_seen}")
            else:
                print("❌ Faculty ID 1 not found in database")
        finally:
            db.close()
            
        # Test 3: Manual status update
        print("\n3️⃣ Testing Manual Status Update...")
        if global_controller:
            print("Attempting to update faculty 1 status to True...")
            result = global_controller.update_faculty_status(1, True)
            if result:
                print(f"✅ Update successful: {result}")
            else:
                print("❌ Update failed")
                
        # Test 4: Check database after update
        print("\n4️⃣ Checking Database After Update...")
        db = get_db()
        try:
            faculty = db.query(Faculty).filter(Faculty.id == 1).first()
            if faculty:
                print(f"✅ Faculty ID 1 status after update: {faculty.status}")
                print(f"   - Last seen: {faculty.last_seen}")
            else:
                print("❌ Faculty ID 1 not found after update")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error in faculty controller test: {e}")
        import traceback
        print(traceback.format_exc())

def test_mqtt_message_simulation():
    """Simulate MQTT message processing"""
    print("\n\n🔍 Testing MQTT Message Simulation...")
    print("=" * 60)
    
    try:
        # Simulate the exact MQTT message from the logs
        mqtt_data = {
            'type': 'faculty_status',
            'faculty_id': 1,
            'faculty_name': 'Cris Angelo Salonga',
            'status': True,
            'previous_status': False,
            'sequence': 1,
            'timestamp': datetime.now().isoformat(),
            'version': 1,
            'change_detected': True
        }
        
        print(f"📨 Simulating MQTT message: {json.dumps(mqtt_data, indent=2)}")
        
        # Test Faculty Controller handling
        from central_system.controllers.faculty_controller import get_faculty_controller
        controller = get_faculty_controller()
        
        if controller:
            print("\n🔧 Testing Faculty Controller MQTT Handling...")
            
            # Simulate the same handling that would happen from ESP32
            topic = f"consultease/faculty/{mqtt_data['faculty_id']}/status"
            esp32_data = {
                "status": "AVAILABLE" if mqtt_data['status'] else "AWAY",
                "timestamp": mqtt_data['timestamp']
            }
            
            print(f"📡 Simulating ESP32 message: Topic={topic}, Data={esp32_data}")
            controller.handle_faculty_status_update(topic, esp32_data)
            
            # Check database after simulated update
            print("\n📊 Checking Database After Simulated MQTT...")
            from central_system.models.base import get_db
            from central_system.models.faculty import Faculty
            
            db = get_db()
            try:
                faculty = db.query(Faculty).filter(Faculty.id == 1).first()
                if faculty:
                    print(f"✅ Faculty status after MQTT simulation: {faculty.status}")
                    print(f"   - Expected: {mqtt_data['status']}")
                    print(f"   - Match: {faculty.status == mqtt_data['status']}")
                else:
                    print("❌ Faculty not found after MQTT simulation")
            finally:
                db.close()
        else:
            print("❌ No faculty controller available for MQTT simulation")
            
    except Exception as e:
        print(f"❌ Error in MQTT simulation: {e}")
        import traceback
        print(traceback.format_exc())

def test_dashboard_status_mapping():
    """Test dashboard status mapping logic"""
    print("\n\n🔍 Testing Dashboard Status Mapping...")
    print("=" * 60)
    
    try:
        # Test status mappings
        test_statuses = [True, False, "AVAILABLE", "UNAVAILABLE", "available", "offline"]
        
        # Mock the _map_status_for_display function
        def _map_status_for_display(status):
            if status is True or status == True:
                return 'available'
            elif status is False or status == False:
                return 'offline'
            elif isinstance(status, str):
                status_lower = status.lower().strip()
                if status_lower in ['available', 'present', 'online', 'active']:
                    return 'available'
                elif status_lower in ['busy', 'in_consultation', 'occupied']:
                    return 'busy'
                elif status_lower in ['offline', 'away', 'unavailable', 'absent']:
                    return 'offline'
                else:
                    return 'offline'
            else:
                return 'offline'
        
        print("📊 Testing Status Mappings:")
        for status in test_statuses:
            mapped = _map_status_for_display(status)
            print(f"   {status} ({type(status).__name__}) → {mapped}")
            
        # Test the specific case from logs
        mqtt_status = True
        mapped_status = _map_status_for_display(mqtt_status)
        print(f"\n🎯 MQTT Status {mqtt_status} → Dashboard Status: {mapped_status}")
        
    except Exception as e:
        print(f"❌ Error in status mapping test: {e}")
        import traceback
        print(traceback.format_exc())

def main():
    """Run all diagnostic tests"""
    print("🚀 Faculty Real-Time Update Diagnostic Tool")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now()}")
    
    # Run all tests
    test_faculty_controller_status_flow()
    test_mqtt_message_simulation()
    test_dashboard_status_mapping()
    
    print("\n" + "=" * 60)
    print("🏁 Diagnostic Complete")
    print("\n💡 Key Points to Check:")
    print("1. Is the global Faculty Controller properly initialized and started?")
    print("2. Does the Faculty Controller successfully update the database?")
    print("3. Are MQTT messages being processed correctly?")
    print("4. Is the dashboard using the global controller for all operations?")

if __name__ == "__main__":
    main() 
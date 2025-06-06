#!/usr/bin/env python3
"""
Test script to add sample faculty data for testing the dashboard.
This script creates test faculty members to verify the dashboard functionality.
"""

import sys
import os
import logging

# Add the central_system directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'central_system'))

from models.base import init_db, get_db
from models.faculty import Faculty
from controllers.faculty_controller import FacultyController

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_faculty():
    """Create test faculty members for dashboard testing."""
    print("🚀 Creating test faculty data for dashboard testing...")
    
    # Initialize database
    init_db()
    
    # Get faculty controller
    faculty_controller = FacultyController()
    
    # Test faculty data
    test_faculty = [
        {
            'name': 'Dr. John Smith',
            'department': 'Computer Science',
            'email': 'john.smith@university.edu',
            'ble_id': 'AA:BB:CC:DD:EE:01',
            'status': True,  # Available
        },
        {
            'name': 'Prof. Maria Garcia',
            'department': 'Mathematics',
            'email': 'maria.garcia@university.edu',
            'ble_id': 'AA:BB:CC:DD:EE:02',
            'status': False,  # Unavailable
        },
        {
            'name': 'Dr. James Wilson',
            'department': 'Physics',
            'email': 'james.wilson@university.edu',
            'ble_id': 'AA:BB:CC:DD:EE:03',
            'status': True,  # Available
        },
        {
            'name': 'Prof. Sarah Johnson',
            'department': 'Chemistry',
            'email': 'sarah.johnson@university.edu',
            'ble_id': 'AA:BB:CC:DD:EE:04',
            'status': False,  # Unavailable
        },
        {
            'name': 'Dr. Michael Brown',
            'department': 'Engineering',
            'email': 'michael.brown@university.edu',
            'ble_id': 'AA:BB:CC:DD:EE:05',
            'status': True,  # Available
        }
    ]
    
    created_count = 0
    
    for faculty_data in test_faculty:
        try:
            # Check if faculty already exists
            db = get_db()
            existing = db.query(Faculty).filter(Faculty.email == faculty_data['email']).first()
            
            if existing:
                print(f"⚠️  Faculty {faculty_data['name']} already exists, skipping...")
                continue
            
            # Create faculty using the controller
            faculty, errors = faculty_controller.add_faculty(
                name=faculty_data['name'],
                department=faculty_data['department'],
                email=faculty_data['email'],
                ble_id=faculty_data['ble_id']
            )
            
            if faculty and not errors:
                # Update status directly in database since controller creates with status=False
                faculty.status = faculty_data['status']
                db.commit()
                
                print(f"✅ Created faculty: {faculty.name} - {'Available' if faculty.status else 'Unavailable'}")
                created_count += 1
            else:
                print(f"❌ Failed to create faculty {faculty_data['name']}: {errors}")
                
        except Exception as e:
            print(f"❌ Error creating faculty {faculty_data['name']}: {str(e)}")
    
    print(f"\n🎉 Successfully created {created_count} test faculty members!")
    
    # Display current faculty list
    print("\n📋 Current faculty list:")
    try:
        all_faculty = faculty_controller.get_all_faculty()
        for faculty in all_faculty:
            status_text = "Available" if faculty.status else "Unavailable"
            print(f"  - {faculty.name} ({faculty.department}) - {status_text}")
    except Exception as e:
        print(f"❌ Error retrieving faculty list: {str(e)}")

def clear_test_faculty():
    """Clear all test faculty data."""
    print("🧹 Clearing all faculty data...")
    
    try:
        db = get_db()
        faculty_count = db.query(Faculty).count()
        
        if faculty_count == 0:
            print("ℹ️  No faculty data to clear.")
            return
        
        # Delete all faculty
        db.query(Faculty).delete()
        db.commit()
        
        print(f"✅ Cleared {faculty_count} faculty records.")
        
    except Exception as e:
        print(f"❌ Error clearing faculty data: {str(e)}")

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == 'clear':
        clear_test_faculty()
    else:
        create_test_faculty()

if __name__ == '__main__':
    main()

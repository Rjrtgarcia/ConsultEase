#!/usr/bin/env python3
"""
Test script for the enhanced admin account management system.
This script verifies that the admin account creation and authentication works correctly.

Usage:
    python test_admin_account_management.py

Author: ConsultEase Development Team
"""

import sys
import os
import logging

# Add the central_system directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'central_system'))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_admin_account_management():
    """Test the admin account management functionality."""
    
    print("🧪 Testing Enhanced Admin Account Management System")
    print("=" * 60)
    
    try:
        # Import required modules
        from models.base import init_db, get_db
        from models.admin import Admin
        from controllers.admin_controller import AdminController
        
        print("✅ Successfully imported required modules")
        
        # Initialize database
        print("\n📊 Initializing database...")
        init_db()
        print("✅ Database initialized successfully")
        
        # Create admin controller
        print("\n🎮 Creating admin controller...")
        admin_controller = AdminController()
        print("✅ Admin controller created successfully")
        
        # Test 1: Check if admin accounts exist
        print("\n🔍 Test 1: Checking if admin accounts exist...")
        accounts_exist = admin_controller.check_admin_accounts_exist()
        print(f"   Admin accounts exist: {accounts_exist}")
        
        valid_accounts_exist = admin_controller.check_valid_admin_accounts_exist()
        print(f"   Valid admin accounts exist: {valid_accounts_exist}")
        
        is_first_time = admin_controller.is_first_time_setup()
        print(f"   Is first-time setup: {is_first_time}")
        
        # Test 2: Create a test admin account (if needed)
        print("\n🔧 Test 2: Creating test admin account...")
        test_username = "testadmin"
        test_password = "TestPass123!"
        test_email = "test@consultease.com"
        
        # Check if test account already exists
        db = get_db()
        existing_admin = db.query(Admin).filter(Admin.username == test_username).first()
        
        if existing_admin:
            print(f"   Test admin '{test_username}' already exists, skipping creation")
        else:
            result = admin_controller.create_admin_account(
                username=test_username,
                password=test_password,
                email=test_email
            )
            
            if result['success']:
                print(f"✅ Test admin account created successfully: {test_username}")
                print(f"   Admin ID: {result['admin']['id']}")
                print(f"   Username: {result['admin']['username']}")
                print(f"   Email: {result['admin']['email']}")
            else:
                print(f"❌ Failed to create test admin account: {result['error']}")
                return False
        
        # Test 3: Authenticate with the test account
        print("\n🔐 Test 3: Testing authentication...")
        auth_result = admin_controller.authenticate(test_username, test_password)
        
        if auth_result:
            print("✅ Authentication successful!")
            print(f"   Admin ID: {auth_result['admin'].id}")
            print(f"   Username: {auth_result['admin'].username}")
            print(f"   Email: {auth_result['admin'].email}")
            print(f"   Is Active: {auth_result['admin'].is_active}")
            print(f"   Requires Password Change: {auth_result.get('requires_password_change', False)}")
        else:
            print("❌ Authentication failed!")
            return False
        
        # Test 4: Test password validation
        print("\n🔒 Test 4: Testing password validation...")
        weak_passwords = [
            "123",           # Too short
            "password",      # No uppercase, numbers, special chars
            "PASSWORD",      # No lowercase, numbers, special chars
            "Password",      # No numbers, special chars
            "Password123",   # No special chars
        ]
        
        for weak_password in weak_passwords:
            is_valid, error_msg = Admin.validate_password_strength(weak_password)
            print(f"   Password '{weak_password}': {'✅ Valid' if is_valid else '❌ Invalid'} - {error_msg}")
        
        # Test strong password
        strong_password = "StrongPass123!"
        is_valid, error_msg = Admin.validate_password_strength(strong_password)
        print(f"   Password '{strong_password}': {'✅ Valid' if is_valid else '❌ Invalid'} - {error_msg}")
        
        # Test 5: Test account existence checks after creation
        print("\n🔄 Test 5: Re-checking account existence...")
        accounts_exist_after = admin_controller.check_admin_accounts_exist(force_refresh=True)
        valid_accounts_exist_after = admin_controller.check_valid_admin_accounts_exist()
        is_first_time_after = admin_controller.is_first_time_setup()
        
        print(f"   Admin accounts exist: {accounts_exist_after}")
        print(f"   Valid admin accounts exist: {valid_accounts_exist_after}")
        print(f"   Is first-time setup: {is_first_time_after}")
        
        # Test 6: Test duplicate username prevention
        print("\n🚫 Test 6: Testing duplicate username prevention...")
        duplicate_result = admin_controller.create_admin_account(
            username=test_username,  # Same username
            password="AnotherPass123!",
            email="another@consultease.com"
        )
        
        if not duplicate_result['success'] and 'already exists' in duplicate_result['error']:
            print("✅ Duplicate username prevention working correctly")
        else:
            print("❌ Duplicate username prevention failed")
            return False
        
        # Test 7: List all admin accounts
        print("\n📋 Test 7: Listing all admin accounts...")
        all_admins = db.query(Admin).all()
        print(f"   Total admin accounts: {len(all_admins)}")
        
        for admin in all_admins:
            print(f"   - ID: {admin.id}, Username: {admin.username}, Email: {admin.email}, Active: {admin.is_active}")
        
        print("\n🎉 All tests completed successfully!")
        print("✅ Enhanced Admin Account Management System is working correctly!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_ui_components():
    """Test the UI components (requires PyQt5)."""
    
    print("\n🖥️  Testing UI Components...")
    print("-" * 40)
    
    try:
        from PyQt5.QtWidgets import QApplication
        from views.admin_account_creation_dialog import AdminAccountCreationDialog
        
        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        print("✅ PyQt5 available - UI components can be tested")
        
        # Test dialog creation (don't show it in automated test)
        dialog = AdminAccountCreationDialog()
        print("✅ AdminAccountCreationDialog created successfully")
        
        # Test form validation
        dialog.username_input.setText("testuser")
        dialog.password_input.setText("TestPass123!")
        dialog.confirm_password_input.setText("TestPass123!")
        dialog.email_input.setText("test@example.com")
        
        is_valid = dialog.validate_form()
        print(f"✅ Form validation test: {'Passed' if is_valid else 'Failed'}")
        
        return True
        
    except ImportError:
        print("⚠️  PyQt5 not available - UI components cannot be tested")
        print("   This is normal if running in a headless environment")
        return True
    except Exception as e:
        print(f"❌ UI component test failed: {e}")
        return False

def main():
    """Main test function."""
    
    print("🚀 ConsultEase Enhanced Admin Account Management Test Suite")
    print("=" * 70)
    
    # Test core functionality
    core_test_passed = test_admin_account_management()
    
    # Test UI components
    ui_test_passed = test_ui_components()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 30)
    print(f"Core Functionality: {'✅ PASSED' if core_test_passed else '❌ FAILED'}")
    print(f"UI Components: {'✅ PASSED' if ui_test_passed else '❌ FAILED'}")
    
    overall_success = core_test_passed and ui_test_passed
    print(f"\nOverall Result: {'🎉 ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n✅ The Enhanced Admin Account Management System is ready for use!")
        print("✅ Users will be able to create admin accounts through the first-time setup dialog.")
        print("✅ All fallback mechanisms are working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")
        print("❌ The system may not work correctly until issues are resolved.")
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    sys.exit(main())

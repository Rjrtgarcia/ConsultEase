#!/usr/bin/env python3
"""
Setup Script for Localhost MQTT Configuration in ConsultEase Central System.

This script configures the central system to use localhost for MQTT broker connections
and provides guidance for updating ESP32 configurations.
"""

import os
import sys
import json
import logging
import socket
import subprocess
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LocalhostMQTTSetup:
    """Setup utility for localhost MQTT configuration."""
    
    def __init__(self):
        self.central_system_path = os.path.dirname(os.path.abspath(__file__))
        self.config_files = [
            "config.py",
            "utils/config_manager.py",
            "services/async_mqtt_service.py"
        ]
        
        # Get the Raspberry Pi's IP address for ESP32 configuration
        self.pi_ip_address = self._get_pi_ip_address()
        
    def _get_pi_ip_address(self) -> Optional[str]:
        """Get the Raspberry Pi's IP address for ESP32 configuration."""
        try:
            # Try to get IP from network interface
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Connect to a remote address to get local IP
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
                logger.info(f"Detected Raspberry Pi IP address: {ip_address}")
                return ip_address
        except Exception as e:
            logger.warning(f"Could not detect IP address: {e}")
            return None
    
    def setup_localhost_config(self):
        """Configure the central system to use localhost for MQTT."""
        print("🔧 Setting up Localhost MQTT Configuration")
        print("=" * 50)
        
        # Check if configuration files exist and are already configured
        self._verify_configuration_files()
        
        # Create environment configuration
        self._create_environment_config()
        
        # Create settings file
        self._create_settings_file()
        
        # Test MQTT broker availability
        self._test_mqtt_broker()
        
        print("\n✅ Localhost MQTT configuration completed!")
        
    def _verify_configuration_files(self):
        """Verify that configuration files are properly set for localhost."""
        print("\n1. Verifying Configuration Files...")
        
        for config_file in self.config_files:
            file_path = os.path.join(self.central_system_path, config_file)
            
            if os.path.exists(file_path):
                print(f"   ✅ Found: {config_file}")
                
                # Check if localhost is configured
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                if '"localhost"' in content or "'localhost'" in content:
                    print(f"   ✅ {config_file} configured for localhost")
                else:
                    print(f"   ⚠️ {config_file} may need localhost configuration")
            else:
                print(f"   ❌ Missing: {config_file}")
    
    def _create_environment_config(self):
        """Create environment configuration for localhost MQTT."""
        print("\n2. Creating Environment Configuration...")
        
        env_config = {
            "MQTT_BROKER_HOST": "localhost",
            "MQTT_BROKER_PORT": "1883",
            "CONSULTEASE_MQTT_HOST": "localhost",
            "CONSULTEASE_MQTT_PORT": "1883"
        }
        
        # Create .env file
        env_file_path = os.path.join(self.central_system_path, ".env")
        
        try:
            with open(env_file_path, 'w') as f:
                f.write("# ConsultEase Environment Configuration\n")
                f.write("# MQTT Broker Configuration\n")
                for key, value in env_config.items():
                    f.write(f"{key}={value}\n")
                    # Also set in current environment
                    os.environ[key] = value
            
            print(f"   ✅ Created environment configuration: {env_file_path}")
            
        except Exception as e:
            print(f"   ❌ Failed to create environment configuration: {e}")
    
    def _create_settings_file(self):
        """Create settings.ini file for the application."""
        print("\n3. Creating Settings File...")
        
        settings_file_path = os.path.join(self.central_system_path, "settings.ini")
        
        try:
            with open(settings_file_path, 'w') as f:
                f.write("[MQTT]\n")
                f.write("broker_host = localhost\n")
                f.write("broker_port = 1883\n")
                f.write("\n[System]\n")
                f.write("auto_start = true\n")
                f.write("debug = true\n")
            
            print(f"   ✅ Created settings file: {settings_file_path}")
            
        except Exception as e:
            print(f"   ❌ Failed to create settings file: {e}")
    
    def _test_mqtt_broker(self):
        """Test if MQTT broker is available on localhost."""
        print("\n4. Testing MQTT Broker Availability...")
        
        try:
            # Test socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(("localhost", 1883))
            sock.close()
            
            if result == 0:
                print("   ✅ MQTT broker is running on localhost:1883")
            else:
                print("   ⚠️ MQTT broker not detected on localhost:1883")
                self._suggest_mqtt_broker_setup()
                
        except Exception as e:
            print(f"   ❌ Error testing MQTT broker: {e}")
            self._suggest_mqtt_broker_setup()
    
    def _suggest_mqtt_broker_setup(self):
        """Provide suggestions for setting up MQTT broker."""
        print("\n   💡 MQTT Broker Setup Suggestions:")
        print("   " + "=" * 40)
        print("   If MQTT broker is not running, you can:")
        print("   1. Install Mosquitto MQTT broker:")
        print("      sudo apt update")
        print("      sudo apt install mosquitto mosquitto-clients")
        print("      sudo systemctl enable mosquitto")
        print("      sudo systemctl start mosquitto")
        print()
        print("   2. Or use the existing ConsultEase MQTT service")
        print("      (if it's part of your system setup)")
    
    def generate_esp32_config(self):
        """Generate ESP32 configuration with the correct IP address."""
        print("\n🔧 Generating ESP32 Configuration")
        print("=" * 40)
        
        if not self.pi_ip_address:
            print("   ❌ Could not detect Raspberry Pi IP address")
            print("   💡 Please manually set the IP address in ESP32 config.h")
            return
        
        esp32_config = f'''
// ESP32 Configuration for ConsultEase Faculty Desk Unit
// Updated for Central System at {self.pi_ip_address}

#define WIFI_SSID "YOUR_WIFI_SSID"        // Update with your WiFi SSID
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD" // Update with your WiFi password
#define MQTT_SERVER "{self.pi_ip_address}"  // Raspberry Pi IP address
#define MQTT_PORT 1883
#define MQTT_USERNAME ""
#define MQTT_PASSWORD ""
        '''
        
        # Save ESP32 configuration
        esp32_config_path = os.path.join(self.central_system_path, "esp32_config_template.h")
        
        try:
            with open(esp32_config_path, 'w') as f:
                f.write(esp32_config.strip())
            
            print(f"   ✅ Generated ESP32 config template: {esp32_config_path}")
            print(f"   📝 ESP32 should connect to MQTT broker at: {self.pi_ip_address}:1883")
            print()
            print("   💡 Instructions for ESP32 Configuration:")
            print("   1. Copy the settings from esp32_config_template.h")
            print("   2. Update your ESP32 config.h file with these values")
            print("   3. Update WIFI_SSID and WIFI_PASSWORD with your network credentials")
            print("   4. Flash the updated firmware to your ESP32 units")
            
        except Exception as e:
            print(f"   ❌ Failed to generate ESP32 configuration: {e}")
    
    def create_startup_script(self):
        """Create a startup script for the ConsultEase system."""
        print("\n🚀 Creating Startup Script")
        print("=" * 30)
        
        startup_script = f'''#!/bin/bash
# ConsultEase Central System Startup Script

# Set environment variables
export MQTT_BROKER_HOST=localhost
export MQTT_BROKER_PORT=1883
export CONSULTEASE_MQTT_HOST=localhost

# Change to central system directory
cd "{self.central_system_path}"

# Start the main application
python3 main.py
'''
        
        startup_script_path = os.path.join(self.central_system_path, "start_consultease.sh")
        
        try:
            with open(startup_script_path, 'w') as f:
                f.write(startup_script)
            
            # Make executable
            os.chmod(startup_script_path, 0o755)
            
            print(f"   ✅ Created startup script: {startup_script_path}")
            print("   💡 You can now start ConsultEase with: ./start_consultease.sh")
            
        except Exception as e:
            print(f"   ❌ Failed to create startup script: {e}")
    
    def run_comprehensive_test(self):
        """Run comprehensive test of localhost configuration."""
        print("\n🧪 Running Comprehensive Test")
        print("=" * 35)
        
        test_script_path = os.path.join(self.central_system_path, "test_localhost_mqtt.py")
        
        if os.path.exists(test_script_path):
            try:
                result = subprocess.run([sys.executable, test_script_path], 
                                     capture_output=True, text=True, cwd=self.central_system_path)
                
                print("   Test Results:")
                print("   " + "-" * 20)
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print("   Errors:")
                    print(result.stderr)
                
                if result.returncode == 0:
                    print("   ✅ All tests passed!")
                else:
                    print("   ⚠️ Some tests failed. Check the output above.")
                    
            except Exception as e:
                print(f"   ❌ Failed to run tests: {e}")
        else:
            print("   ⚠️ Test script not found")


def main():
    """Main setup function."""
    print("ConsultEase - Localhost MQTT Setup")
    print("=" * 40)
    print("This script configures the central system to automatically")
    print("detect the MQTT broker on localhost instead of using")
    print("hardcoded IP addresses.")
    print()
    
    setup = LocalhostMQTTSetup()
    
    try:
        # Run setup steps
        setup.setup_localhost_config()
        setup.generate_esp32_config()
        setup.create_startup_script()
        
        # Run tests
        print("\n" + "=" * 60)
        setup.run_comprehensive_test()
        
        print("\n🎉 Setup Complete!")
        print("=" * 20)
        print("✅ Central system configured for localhost MQTT")
        if setup.pi_ip_address:
            print(f"✅ ESP32 should connect to: {setup.pi_ip_address}:1883")
        print("✅ Environment configuration created")
        print("✅ Startup script created")
        
        print("\n📋 Next Steps:")
        print("1. Update ESP32 config.h with the generated template")
        print("2. Ensure MQTT broker is running on this system")
        print("3. Test the configuration with: python3 test_localhost_mqtt.py")
        print("4. Start the system with: ./start_consultease.sh")
        
        return 0
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        print(f"\n❌ Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 
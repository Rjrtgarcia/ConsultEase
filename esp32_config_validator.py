#!/usr/bin/env python3
"""
ESP32 Configuration Validator for ConsultEase System

This script helps identify configuration issues with ESP32 faculty desk units,
particularly the issue where literal "FACULTY_ID" is being sent instead of 
actual faculty ID numbers.
"""

import logging
import json
import time
import datetime
from pathlib import Path
from central_system.utils.mqtt_utils import subscribe_to_topic, publish_mqtt_message
from central_system.models import Faculty, get_db
from central_system.services.async_mqtt_service import get_async_mqtt_service

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ESP32ConfigValidator:
    """Validator to identify and help fix ESP32 configuration issues."""
    
    def __init__(self):
        self.received_messages = []
        self.problematic_messages = []
        self.valid_faculty_ids = set()
        
    def start_validation(self, duration_minutes=5):
        """
        Start validating ESP32 messages for configuration issues.
        
        Args:
            duration_minutes: How long to monitor messages
        """
        logger.info("🔧 Starting ESP32 Configuration Validation")
        logger.info(f"⏱️ Monitoring for {duration_minutes} minutes...")
        
        # Load valid faculty IDs from database
        self._load_valid_faculty_ids()
        
        # Subscribe to all faculty status topics
        self._setup_message_monitoring()
        
        # Monitor for specified duration
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        logger.info("📡 Monitoring ESP32 messages...")
        
        while time.time() < end_time:
            remaining = int(end_time - time.time())
            logger.info(f"⏳ Monitoring... {remaining} seconds remaining")
            time.sleep(30)  # Report every 30 seconds
            
        # Generate report
        self._generate_validation_report()
        
    def _load_valid_faculty_ids(self):
        """Load valid faculty IDs from database."""
        try:
            db = get_db()
            faculties = db.query(Faculty).all()
            self.valid_faculty_ids = {f.id for f in faculties}
            logger.info(f"📚 Loaded {len(self.valid_faculty_ids)} valid faculty IDs: {sorted(self.valid_faculty_ids)}")
            db.close()
        except Exception as e:
            logger.error(f"❌ Error loading faculty IDs: {e}")
            
    def _setup_message_monitoring(self):
        """Set up MQTT message monitoring for ESP32 topics."""
        
        def message_handler(topic, data):
            """Handle incoming ESP32 messages."""
            self._analyze_message(topic, data)
            
        # Subscribe to all possible ESP32 topics
        topics_to_monitor = [
            "consultease/faculty/+/status",
            "consultease/faculty/+/heartbeat", 
            "consultease/faculty/+/diagnostics",
            "consultease/faculty/+/responses",
            "faculty/+/status",  # Legacy format
        ]
        
        for topic in topics_to_monitor:
            try:
                subscribe_to_topic(topic, message_handler)
                logger.info(f"📨 Subscribed to: {topic}")
            except Exception as e:
                logger.error(f"❌ Failed to subscribe to {topic}: {e}")
                
    def _analyze_message(self, topic, data):
        """Analyze incoming message for configuration issues."""
        try:
            timestamp = datetime.datetime.now()
            
            # Store all messages
            message_record = {
                'timestamp': timestamp,
                'topic': topic,
                'data': data,
                'issues': []
            }
            
            # Extract faculty ID from topic
            faculty_id_from_topic = self._extract_faculty_id_from_topic(topic)
            
            # Extract faculty ID from payload
            faculty_id_from_payload = None
            if isinstance(data, dict):
                faculty_id_from_payload = data.get('faculty_id')
            
            # Check for issues
            issues = []
            
            # Issue 1: Literal "FACULTY_ID" in topic
            if "FACULTY_ID" in topic:
                issues.append({
                    'type': 'LITERAL_FACULTY_ID_IN_TOPIC',
                    'description': 'Topic contains literal "FACULTY_ID" instead of actual ID',
                    'topic': topic
                })
                
            # Issue 2: Literal "FACULTY_ID" in payload
            if isinstance(data, dict) and str(data.get('faculty_id', '')).upper() == 'FACULTY_ID':
                issues.append({
                    'type': 'LITERAL_FACULTY_ID_IN_PAYLOAD',
                    'description': 'Payload contains literal "FACULTY_ID" instead of actual ID',
                    'payload_faculty_id': data.get('faculty_id')
                })
                
            # Issue 3: Invalid faculty ID in topic
            if faculty_id_from_topic and faculty_id_from_topic not in self.valid_faculty_ids:
                issues.append({
                    'type': 'INVALID_FACULTY_ID_IN_TOPIC', 
                    'description': 'Faculty ID in topic not found in database',
                    'topic_faculty_id': faculty_id_from_topic,
                    'valid_ids': sorted(self.valid_faculty_ids)
                })
                
            # Issue 4: Invalid faculty ID in payload
            if isinstance(faculty_id_from_payload, (int, str)):
                try:
                    payload_id = int(faculty_id_from_payload)
                    if payload_id not in self.valid_faculty_ids:
                        issues.append({
                            'type': 'INVALID_FACULTY_ID_IN_PAYLOAD',
                            'description': 'Faculty ID in payload not found in database',
                            'payload_faculty_id': payload_id,
                            'valid_ids': sorted(self.valid_faculty_ids)
                        })
                except (ValueError, TypeError):
                    issues.append({
                        'type': 'NON_NUMERIC_FACULTY_ID_IN_PAYLOAD',
                        'description': 'Faculty ID in payload is not numeric',
                        'payload_faculty_id': faculty_id_from_payload
                    })
                    
            # Issue 5: Mismatch between topic and payload faculty IDs
            if (faculty_id_from_topic and faculty_id_from_payload and 
                faculty_id_from_topic != faculty_id_from_payload):
                issues.append({
                    'type': 'FACULTY_ID_MISMATCH',
                    'description': 'Faculty ID in topic does not match payload',
                    'topic_faculty_id': faculty_id_from_topic,
                    'payload_faculty_id': faculty_id_from_payload
                })
                
            message_record['issues'] = issues
            self.received_messages.append(message_record)
            
            if issues:
                self.problematic_messages.append(message_record)
                logger.warning(f"🚨 ISSUE DETECTED: {topic} - {len(issues)} problems found")
                for issue in issues:
                    logger.warning(f"   - {issue['type']}: {issue['description']}")
            else:
                logger.debug(f"✅ Valid message: {topic}")
                
        except Exception as e:
            logger.error(f"❌ Error analyzing message from {topic}: {e}")
            
    def _extract_faculty_id_from_topic(self, topic):
        """Extract faculty ID from MQTT topic."""
        try:
            parts = topic.split('/')
            
            # Standard format: consultease/faculty/{id}/...
            if len(parts) >= 3 and parts[0] == "consultease" and parts[1] == "faculty":
                return int(parts[2])
                
            # Legacy format: faculty/{id}/...
            elif len(parts) >= 2 and parts[0] == "faculty":
                return int(parts[1])
                
        except (ValueError, IndexError):
            pass
            
        return None
        
    def _generate_validation_report(self):
        """Generate comprehensive validation report."""
        logger.info("📊 Generating ESP32 Configuration Validation Report")
        logger.info("=" * 60)
        
        # Summary statistics
        total_messages = len(self.received_messages)
        problematic_messages = len(self.problematic_messages)
        success_rate = ((total_messages - problematic_messages) / total_messages * 100) if total_messages > 0 else 0
        
        logger.info(f"📈 SUMMARY STATISTICS:")
        logger.info(f"   Total messages received: {total_messages}")
        logger.info(f"   Problematic messages: {problematic_messages}")
        logger.info(f"   Success rate: {success_rate:.1f}%")
        logger.info("")
        
        # Issue breakdown
        issue_counts = {}
        for msg in self.problematic_messages:
            for issue in msg['issues']:
                issue_type = issue['type']
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
                
        if issue_counts:
            logger.info("🚨 ISSUE BREAKDOWN:")
            for issue_type, count in sorted(issue_counts.items()):
                logger.info(f"   {issue_type}: {count} occurrences")
        else:
            logger.info("✅ NO ISSUES DETECTED!")
            
        logger.info("")
        
        # Configuration recommendations
        self._generate_recommendations(issue_counts)
        
        # Save detailed report to file
        self._save_detailed_report()
        
    def _generate_recommendations(self, issue_counts):
        """Generate configuration fix recommendations."""
        logger.info("💡 CONFIGURATION RECOMMENDATIONS:")
        
        if 'LITERAL_FACULTY_ID_IN_TOPIC' in issue_counts or 'LITERAL_FACULTY_ID_IN_PAYLOAD' in issue_counts:
            logger.info("   🔧 ESP32 FIRMWARE COMPILATION ISSUE DETECTED:")
            logger.info("      - The ESP32 firmware is not properly compiling FACULTY_ID macro")
            logger.info("      - Check faculty_desk_unit/config.h: ensure FACULTY_ID is set to a number")
            logger.info("      - Recompile and upload firmware to ESP32")
            logger.info("      - Example: #define FACULTY_ID 1  (not #define FACULTY_ID \"FACULTY_ID\")")
            
        if 'INVALID_FACULTY_ID_IN_TOPIC' in issue_counts or 'INVALID_FACULTY_ID_IN_PAYLOAD' in issue_counts:
            logger.info("   🏢 DATABASE SYNC ISSUE DETECTED:")
            logger.info("      - ESP32 configured with faculty ID not in database")
            logger.info("      - Add missing faculty records to database, or")
            logger.info("      - Update ESP32 config.h with valid faculty ID and recompile")
            logger.info(f"      - Valid faculty IDs: {sorted(self.valid_faculty_ids)}")
            
        if 'FACULTY_ID_MISMATCH' in issue_counts:
            logger.info("   ⚡ FIRMWARE LOGIC ERROR DETECTED:")
            logger.info("      - ESP32 sending inconsistent faculty IDs in topic vs payload") 
            logger.info("      - Check ESP32 firmware for hardcoded faculty IDs")
            logger.info("      - Ensure all MQTT publishes use same FACULTY_ID macro")
            
        if not issue_counts:
            logger.info("   ✅ No configuration issues detected - ESP32 units properly configured!")
            
    def _save_detailed_report(self):
        """Save detailed report to file."""
        try:
            report_data = {
                'timestamp': datetime.datetime.now().isoformat(),
                'summary': {
                    'total_messages': len(self.received_messages),
                    'problematic_messages': len(self.problematic_messages),
                    'valid_faculty_ids': sorted(self.valid_faculty_ids)
                },
                'all_messages': [
                    {
                        'timestamp': msg['timestamp'].isoformat(),
                        'topic': msg['topic'],
                        'data': msg['data'],
                        'issues': msg['issues']
                    }
                    for msg in self.received_messages
                ],
                'problematic_messages': [
                    {
                        'timestamp': msg['timestamp'].isoformat(),
                        'topic': msg['topic'],
                        'data': msg['data'],
                        'issues': msg['issues']
                    }
                    for msg in self.problematic_messages
                ]
            }
            
            filename = f"esp32_config_validation_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
                
            logger.info(f"💾 Detailed report saved to: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Error saving detailed report: {e}")

def main():
    """Main function to run ESP32 configuration validation."""
    logger.info("🚀 ESP32 Configuration Validator for ConsultEase")
    logger.info("This tool helps identify ESP32 configuration issues")
    logger.info("")
    
    try:
        # Start MQTT service if not running
        mqtt_service = get_async_mqtt_service()
        if not mqtt_service.running:
            mqtt_service.start()
            time.sleep(2)  # Allow service to start
            
        # Run validation
        validator = ESP32ConfigValidator()
        validator.start_validation(duration_minutes=2)  # 2 minute monitoring
        
    except KeyboardInterrupt:
        logger.info("⏹️ Validation interrupted by user")
    except Exception as e:
        logger.error(f"❌ Validation error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("🏁 ESP32 Configuration Validation completed")

if __name__ == "__main__":
    main() 
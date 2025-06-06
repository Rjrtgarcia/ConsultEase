import logging
import os
import sys
import json

# Add the central_system to path
sys.path.insert(0, os.path.join(os.getcwd(), 'central_system'))

from central_system.services.mqtt_client import get_mqtt_client

def on_status_message(client, userdata, message):
    topic = message.topic
    try:
        data = json.loads(message.payload.decode())
        print(f'📨 MQTT Message Received:')
        print(f'   Topic: {topic}')
        print(f'   Data: {data}')
        print(f'   Data Type: {type(data)}')
        if isinstance(data, dict):
            print(f'   Status field: {data.get("status")} (type: {type(data.get("status"))})')
            print(f'   Faculty ID: {data.get("faculty_id")} (type: {type(data.get("faculty_id"))})')
        print('-' * 50)
    except Exception as e:
        print(f'❌ Error parsing message: {e}')
        print(f'   Raw payload: {message.payload}')
        print('-' * 50)

mqtt_client = get_mqtt_client()
mqtt_client.message_callback_add('consultease/faculty/+/status_update', on_status_message)
mqtt_client.subscribe('consultease/faculty/+/status_update')

print('🔍 Listening for faculty status updates...')
print('Move a faculty member to trigger an update!')
print('Press Ctrl+C to stop')

try:
    mqtt_client.loop_forever()
except KeyboardInterrupt:
    print('\nStopping listener...')
    mqtt_client.disconnect() 
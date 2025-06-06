// ================================
// FACULTY DESK UNIT - NETWORK CONNECTION FIXES
// ================================
// This file contains fixes to prevent consultation messages from being processed 
// when WiFi or MQTT connections are not working properly.

// ================================
// ENHANCED NETWORK STATE CHECKING
// ================================

bool isNetworkReady() {
  // Check if both WiFi and MQTT are properly connected
  bool wifiOk = WiFi.isConnected() && wifiConnected;
  bool mqttOk = mqttClient.connected() && mqttConnected;
  
  // Additional MQTT state verification
  bool mqttReallyOk = isMqttReallyConnected();
  
  DEBUG_PRINTF("🔍 Network readiness check:\n");
  DEBUG_PRINTF("   WiFi.isConnected(): %s\n", WiFi.isConnected() ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   wifiConnected flag: %s\n", wifiConnected ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   mqttClient.connected(): %s\n", mqttClient.connected() ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   mqttConnected flag: %s\n", mqttConnected ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   isMqttReallyConnected(): %s\n", mqttReallyOk ? "TRUE" : "FALSE");
  
  bool ready = wifiOk && mqttOk && mqttReallyOk;
  DEBUG_PRINTF("   ✅ Network ready: %s\n", ready ? "TRUE" : "FALSE");
  
  return ready;
}

bool canProcessConsultations() {
  // Enhanced check that includes faculty presence and network status
  bool networkReady = isNetworkReady();
  bool facultyPresent = presenceDetector.getPresence();
  
  DEBUG_PRINTF("🎯 Consultation processing check:\n");
  DEBUG_PRINTF("   Network ready: %s\n", networkReady ? "TRUE" : "FALSE");
  DEBUG_PRINTF("   Faculty present: %s\n", facultyPresent ? "TRUE" : "FALSE");
  
  bool canProcess = networkReady && facultyPresent;
  DEBUG_PRINTF("   ✅ Can process consultations: %s\n", canProcess ? "TRUE" : "FALSE");
  
  return canProcess;
}

void displayNetworkStatus() {
  // Show network status on display
  tft.fillRect(0, MAIN_AREA_Y, SCREEN_WIDTH, MAIN_AREA_HEIGHT, COLOR_WHITE);
  
  // WiFi status
  if (WiFi.isConnected() && wifiConnected) {
    drawSimpleCard(20, STATUS_CENTER_Y - 80, 280, 30, COLOR_SUCCESS);
    tft.setCursor(getCenterX("WiFi: CONNECTED", 1), STATUS_CENTER_Y - 70);
    tft.setTextSize(1);
    tft.setTextColor(COLOR_WHITE);
    tft.print("WiFi: CONNECTED");
    
    // Show signal strength
    int rssi = WiFi.RSSI();
    String signalText = "Signal: " + String(rssi) + " dBm";
    tft.setCursor(getCenterX(signalText, 1), STATUS_CENTER_Y - 55);
    tft.print(signalText);
  } else {
    drawSimpleCard(20, STATUS_CENTER_Y - 80, 280, 30, COLOR_ERROR);
    tft.setCursor(getCenterX("WiFi: DISCONNECTED", 1), STATUS_CENTER_Y - 70);
    tft.setTextSize(1);
    tft.setTextColor(COLOR_WHITE);
    tft.print("WiFi: DISCONNECTED");
  }
  
  // MQTT status
  if (isNetworkReady()) {
    drawSimpleCard(20, STATUS_CENTER_Y - 40, 280, 30, COLOR_SUCCESS);
    tft.setCursor(getCenterX("MQTT: CONNECTED", 1), STATUS_CENTER_Y - 30);
    tft.setTextSize(1);
    tft.setTextColor(COLOR_WHITE);
    tft.print("MQTT: CONNECTED");
  } else {
    drawSimpleCard(20, STATUS_CENTER_Y - 40, 280, 30, COLOR_ERROR);
    tft.setCursor(getCenterX("MQTT: DISCONNECTED", 1), STATUS_CENTER_Y - 30);
    tft.setTextSize(1);
    tft.setTextColor(COLOR_WHITE);
    tft.print("MQTT: DISCONNECTED");
    
    int mqttState = mqttClient.state();
    String stateText = "State: " + String(getMqttStateString(mqttState));
    tft.setCursor(getCenterX(stateText, 1), STATUS_CENTER_Y - 15);
    tft.print(stateText);
  }
  
  // System status
  if (canProcessConsultations()) {
    drawSimpleCard(20, STATUS_CENTER_Y, 280, 40, COLOR_SUCCESS);
    tft.setCursor(getCenterX("SYSTEM READY", 2), STATUS_CENTER_Y + 10);
    tft.setTextSize(2);
    tft.setTextColor(COLOR_WHITE);
    tft.print("SYSTEM READY");
    
    tft.setCursor(getCenterX("Ready for consultations", 1), STATUS_CENTER_Y + 35);
    tft.setTextSize(1);
    tft.print("Ready for consultations");
  } else {
    drawSimpleCard(20, STATUS_CENTER_Y, 280, 40, COLOR_WARNING);
    tft.setCursor(getCenterX("SYSTEM NOT READY", 2), STATUS_CENTER_Y + 10);
    tft.setTextSize(2);
    tft.setTextColor(COLOR_WHITE);
    tft.print("SYSTEM NOT READY");
    
    if (!isNetworkReady()) {
      tft.setCursor(getCenterX("Network disconnected", 1), STATUS_CENTER_Y + 35);
      tft.setTextSize(1);
      tft.print("Network disconnected");
    } else if (!presenceDetector.getPresence()) {
      tft.setCursor(getCenterX("Faculty not present", 1), STATUS_CENTER_Y + 35);
      tft.setTextSize(1);
      tft.print("Faculty not present");
    }
  }
}

// ================================
// ENHANCED MQTT MESSAGE HANDLER
// ================================

void onMqttMessageEnhanced(char* topic, byte* payload, unsigned int length) {
  DEBUG_PRINTF("📨 onMqttMessageEnhanced called - Topic: %s, Length: %d\n", topic, length);
  
  // CRITICAL CHECK: Only process messages if network is ready
  if (!isNetworkReady()) {
    DEBUG_PRINTLN("❌ Message ignored - Network not ready");
    DEBUG_PRINTF("   WiFi connected: %s\n", wifiConnected ? "TRUE" : "FALSE");
    DEBUG_PRINTF("   MQTT connected: %s\n", mqttConnected ? "TRUE" : "FALSE");
    return;
  }
  
  // CRITICAL CHECK: Only process if faculty is present
  if (!presenceDetector.getPresence()) {
    DEBUG_PRINTLN("❌ Message ignored - Faculty not present");
    return;
  }
  
  // Bounds checking for security
  if (length > MAX_MESSAGE_LENGTH) {
    DEBUG_PRINTF("⚠️ Message too long (%d bytes), truncating to %d\n", length, MAX_MESSAGE_LENGTH);
    length = MAX_MESSAGE_LENGTH;
  }

  String messageContent = "";
  messageContent.reserve(length + 1);  // Pre-allocate memory

  for (unsigned int i = 0; i < length; i++) {
    messageContent += (char)payload[i];
  }

  DEBUG_PRINTF("📨 Message received (%d bytes): %s\n", length, messageContent.c_str());
  
  // Check if this is a cancellation notification
  String topicStr = String(topic);
  if (topicStr.indexOf("/cancellations") != -1) {
    handleCancellationNotification(messageContent);
    return;
  }

  // Parse Consultation ID (CID) from the message
  DEBUG_PRINTLN("🔍 Starting CID parsing...");
  int cidStartIndex = messageContent.indexOf("CID:");
  DEBUG_PRINTF("   CID: search index = %d\n", cidStartIndex);
  
  String parsedConsultationId = "";

  if (cidStartIndex != -1) {
    cidStartIndex += 4; // Length of "CID:"
    int cidEndIndex = messageContent.indexOf(" ", cidStartIndex);
    
    if (cidEndIndex != -1) {
      parsedConsultationId = messageContent.substring(cidStartIndex, cidEndIndex);
    } else {
      parsedConsultationId = messageContent.substring(cidStartIndex);
    }
    DEBUG_PRINTF("🔑 Parsed Consultation ID (CID): '%s'\n", parsedConsultationId.c_str());
  } else {
    DEBUG_PRINTLN("⚠️ Consultation ID (CID:) not found in message.");
    return; // Skip messages without CID
  }
  
  // Final check before processing
  if (!canProcessConsultations()) {
    DEBUG_PRINTLN("❌ Cannot process consultation - System not ready");
    return;
  }

  // Process the consultation message
  DEBUG_PRINTLN("✅ Processing consultation message");
  
  // Store consultation ID globally for button responses
  g_receivedConsultationId = parsedConsultationId;
  
  // Create and queue the consultation message
  ConsultationMessage newMessage;
  parseConsultationMessage(messageContent, parsedConsultationId, newMessage);
  
  if (newMessage.isValid) {
    addToConsultationQueue(newMessage);
    
    // If no message is currently displayed, show this one immediately
    if (!messageDisplayed) {
      processNextQueuedConsultation();
    }
    
    DEBUG_PRINTF("✅ Consultation message processed and queued. Queue size: %d\n", consultationQueueSize);
  } else {
    DEBUG_PRINTLN("❌ Invalid consultation message format");
  }
}

// ================================
// ENHANCED BUTTON HANDLERS WITH NETWORK CHECKS
// ================================

void handleAcknowledgeButtonEnhanced() {
  DEBUG_PRINTLN("🔵 handleAcknowledgeButtonEnhanced() called!");
  
  // CRITICAL CHECK: Verify network connectivity before allowing response
  if (!isNetworkReady()) {
    DEBUG_PRINTLN("❌ Cannot send ACKNOWLEDGE: Network not ready");
    showResponseConfirmation("NO NETWORK!", COLOR_ERROR);
    displayNetworkStatus();  // Show current network status
    return;
  }
  
  // Check if faculty is present
  if (!presenceDetector.getPresence()) {
    DEBUG_PRINTLN("❌ Cannot send ACKNOWLEDGE: Faculty not present");
    showResponseConfirmation("NOT PRESENT!", COLOR_ERROR);
    return;
  }
  
  // Check if there's a message to respond to
  if (!messageDisplayed || currentMessage.isEmpty()) {
    DEBUG_PRINTLN("❌ EARLY RETURN: No message displayed or message is empty");
    showResponseConfirmation("NO MESSAGE!", COLOR_WARNING);
    return;
  }
  
  if (g_receivedConsultationId.isEmpty()) {
    DEBUG_PRINTLN("❌ Cannot send ACKNOWLEDGE: Missing Consultation ID (CID).");
    showResponseConfirmation("NO CID!", COLOR_ERROR);
    return;
  }

  DEBUG_PRINTLN("📤 Sending ACKNOWLEDGE response to central terminal");

  // Create acknowledge response
  String response = "{";
  response += "\"faculty_id\":" + String(FACULTY_ID) + ",";
  response += "\"faculty_name\":\"" + String(FACULTY_NAME) + "\",";
  response += "\"response_type\":\"ACKNOWLEDGE\",";
  response += "\"message_id\":\"" + g_receivedConsultationId + "\",";
  response += "\"timestamp\":\"" + String(millis()) + "\",";
  response += "\"faculty_present\":true,";
  response += "\"response_method\":\"physical_button\",";
  response += "\"network_status\":\"connected\",";
  response += "\"status\":\"Professor acknowledges the request and will respond accordingly\"";
  response += "}";

  DEBUG_PRINTF("📝 Response JSON (%d bytes): %s\n", response.length(), response.c_str());
  
  // Verify network is still ready before sending
  if (!isNetworkReady()) {
    DEBUG_PRINTLN("❌ Network disconnected during response preparation");
    showResponseConfirmation("NETWORK LOST!", COLOR_ERROR);
    return;
  }
  
  // Send response
  bool success = publishWithQueue(MQTT_TOPIC_RESPONSES, response.c_str(), true);
  
  if (success) {
    DEBUG_PRINTLN("✅ ACKNOWLEDGE response sent successfully");
    showResponseConfirmation("ACKNOWLEDGED", COLOR_BLUE);
  } else {
    DEBUG_PRINTLN("❌ Failed to send ACKNOWLEDGE response");
    showResponseConfirmation("SEND FAILED!", COLOR_ERROR);
  }

  // Clear message
  clearCurrentMessage();
}

void handleBusyButtonEnhanced() {
  DEBUG_PRINTLN("🔴 handleBusyButtonEnhanced() called!");
  
  // CRITICAL CHECK: Verify network connectivity before allowing response
  if (!isNetworkReady()) {
    DEBUG_PRINTLN("❌ Cannot send BUSY: Network not ready");
    showResponseConfirmation("NO NETWORK!", COLOR_ERROR);
    displayNetworkStatus();  // Show current network status
    return;
  }
  
  // Check if faculty is present
  if (!presenceDetector.getPresence()) {
    DEBUG_PRINTLN("❌ Cannot send BUSY: Faculty not present");
    showResponseConfirmation("NOT PRESENT!", COLOR_ERROR);
    return;
  }
  
  // Check if there's a message to respond to
  if (!messageDisplayed || currentMessage.isEmpty()) {
    DEBUG_PRINTLN("❌ EARLY RETURN: No message displayed or message is empty");
    showResponseConfirmation("NO MESSAGE!", COLOR_WARNING);
    return;
  }
  
  if (g_receivedConsultationId.isEmpty()) {
    DEBUG_PRINTLN("❌ Cannot send BUSY: Missing Consultation ID (CID).");
    showResponseConfirmation("NO CID!", COLOR_ERROR);
    return;
  }

  DEBUG_PRINTLN("📤 Sending BUSY response to central terminal");

  // Create busy response
  String response = "{";
  response += "\"faculty_id\":" + String(FACULTY_ID) + ",";
  response += "\"faculty_name\":\"" + String(FACULTY_NAME) + "\",";
  response += "\"response_type\":\"BUSY\",";
  response += "\"message_id\":\"" + g_receivedConsultationId + "\",";
  response += "\"timestamp\":\"" + String(millis()) + "\",";
  response += "\"faculty_present\":true,";
  response += "\"response_method\":\"physical_button\",";
  response += "\"network_status\":\"connected\",";
  response += "\"status\":\"Professor is currently busy and cannot cater to this request\"";
  response += "}";

  DEBUG_PRINTF("📝 Response JSON (%d bytes): %s\n", response.length(), response.c_str());
  
  // Verify network is still ready before sending
  if (!isNetworkReady()) {
    DEBUG_PRINTLN("❌ Network disconnected during response preparation");
    showResponseConfirmation("NETWORK LOST!", COLOR_ERROR);
    return;
  }
  
  // Send response
  bool success = publishWithQueue(MQTT_TOPIC_RESPONSES, response.c_str(), true);
  
  if (success) {
    DEBUG_PRINTLN("✅ BUSY response sent successfully");
    showResponseConfirmation("MARKED BUSY", COLOR_ERROR);
  } else {
    DEBUG_PRINTLN("❌ Failed to send BUSY response");
    showResponseConfirmation("SEND FAILED!", COLOR_ERROR);
  }

  // Clear message
  clearCurrentMessage();
}

// ================================
// ENHANCED MAIN UI UPDATE FUNCTION
// ================================

void updateSystemStatusEnhanced() {
  // Only update UI if system is fully initialized
  if (!systemFullyInitialized) return;
  
  // Clear previous status
  tft.fillRect(0, STATUS_BAR_Y, SCREEN_WIDTH, STATUS_BAR_HEIGHT, COLOR_DARK_BLUE);
  
  // Network status indicators
  int statusX = 10;
  
  // WiFi indicator
  if (WiFi.isConnected() && wifiConnected) {
    tft.setTextColor(COLOR_SUCCESS);
    tft.setCursor(statusX, STATUS_BAR_Y + 5);
    tft.setTextSize(1);
    tft.print("WiFi:OK");
  } else {
    tft.setTextColor(COLOR_ERROR);
    tft.setCursor(statusX, STATUS_BAR_Y + 5);
    tft.setTextSize(1);
    tft.print("WiFi:OFF");
  }
  
  statusX += 60;
  
  // MQTT indicator
  if (isNetworkReady()) {
    tft.setTextColor(COLOR_SUCCESS);
    tft.setCursor(statusX, STATUS_BAR_Y + 5);
    tft.setTextSize(1);
    tft.print("MQTT:OK");
  } else {
    tft.setTextColor(COLOR_ERROR);
    tft.setCursor(statusX, STATUS_BAR_Y + 5);
    tft.setTextSize(1);
    tft.print("MQTT:OFF");
  }
  
  statusX += 70;
  
  // Faculty presence indicator
  if (presenceDetector.getPresence()) {
    tft.setTextColor(COLOR_SUCCESS);
    tft.setCursor(statusX, STATUS_BAR_Y + 5);
    tft.setTextSize(1);
    tft.print("FACULTY:YES");
  } else {
    tft.setTextColor(COLOR_WARNING);
    tft.setCursor(statusX, STATUS_BAR_Y + 5);
    tft.setTextSize(1);
    tft.print("FACULTY:NO");
  }
  
  // Overall system status
  if (!canProcessConsultations()) {
    // Show network status screen if system is not ready
    if (!messageDisplayed) {
      displayNetworkStatus();
    }
  }
}

// ================================
// ENHANCED MAIN LOOP INTEGRATION
// ================================

void loopNetworkEnhanced() {
  // Enhanced network connection checking with user feedback
  static unsigned long lastNetworkCheck = 0;
  static bool lastNetworkState = false;
  static bool lastCanProcess = false;
  
  if (millis() - lastNetworkCheck > 2000) {  // Check every 2 seconds
    bool currentNetworkState = isNetworkReady();
    bool currentCanProcess = canProcessConsultations();
    
    // Network state changed - update UI
    if (currentNetworkState != lastNetworkState || currentCanProcess != lastCanProcess) {
      DEBUG_PRINTF("🔄 Network state changed:\n");
      DEBUG_PRINTF("   Network ready: %s -> %s\n", 
                   lastNetworkState ? "TRUE" : "FALSE",
                   currentNetworkState ? "TRUE" : "FALSE");
      DEBUG_PRINTF("   Can process: %s -> %s\n",
                   lastCanProcess ? "TRUE" : "FALSE", 
                   currentCanProcess ? "TRUE" : "FALSE");
      
      updateSystemStatusEnhanced();
      
      // If network was restored, process any queued consultations
      if (!lastCanProcess && currentCanProcess) {
        DEBUG_PRINTLN("✅ System ready - processing queued consultations");
        if (!messageDisplayed && consultationQueueSize > 0) {
          processNextQueuedConsultation();
        }
      }
      
      // If network was lost, clear current message to prevent stuck states
      if (lastCanProcess && !currentCanProcess && messageDisplayed) {
        DEBUG_PRINTLN("⚠️ Network lost - clearing current message");
        clearCurrentMessage();
      }
    }
    
    lastNetworkState = currentNetworkState;
    lastCanProcess = currentCanProcess;
    lastNetworkCheck = millis();
  }
  
  // Continue with original network checks
  checkWiFiConnection();
  checkMQTTConnection();
}

// ================================
// INTEGRATION INSTRUCTIONS
// ================================

/*
To integrate these fixes into your existing faculty_desk_unit.ino:

1. Replace the onMqttMessage function with onMqttMessageEnhanced
2. Replace handleAcknowledgeButton with handleAcknowledgeButtonEnhanced  
3. Replace handleBusyButton with handleBusyButtonEnhanced
4. Replace updateSystemStatus with updateSystemStatusEnhanced
5. Add loopNetworkEnhanced() call in your main loop
6. Update your MQTT callback registration:
   mqttClient.setCallback(onMqttMessageEnhanced);

These changes will ensure:
- No consultation messages are processed when network is down
- Clear feedback about network status on the display
- Proper error messages when trying to respond without network
- Automatic recovery when network is restored
*/ 
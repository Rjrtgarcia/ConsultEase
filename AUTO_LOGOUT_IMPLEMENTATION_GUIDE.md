# ConsultEase Auto-Logout Feature Implementation

## Overview

This document describes the implementation of the automatic logout feature for student users in the ConsultEase application. The feature monitors user inactivity and automatically logs out students after 2 minutes of no interaction, with a 30-second warning at the 1.5-minute mark.

## 🎯 Requirements Implemented

✅ **Inactivity Detection**: Monitors mouse movements, clicks, keyboard input, and scrolling  
✅ **Timeout Duration**: Exactly 2 minutes (120 seconds) of inactivity  
✅ **Warning System**: Shows warning dialog at 1.5 minutes (90 seconds) with option to stay logged in  
✅ **Auto-logout Behavior**: Clears session, redirects to login, shows expiration message  
✅ **Activity Reset**: Any user interaction resets the timer back to 0  
✅ **Student-Only Scope**: Only applies to student accounts, not admin users  
✅ **Cross-Page Persistence**: Works across all dashboard tabs and panels  
✅ **Clean Implementation**: Uses PyQt5 event system for proper integration  

## 📁 Files Created/Modified

### New Files

#### `central_system/utils/inactivity_monitor.py`
- **InactivityMonitor Class**: Main monitoring logic with QTimer and event filtering
- **InactivityWarningDialog Class**: Warning dialog with "Stay Logged In" and "Logout Now" options
- **Global Instance Management**: Singleton pattern for application-wide access

### Modified Files

#### `central_system/views/dashboard_window.py`
- Added inactivity monitor setup in `__init__()`
- Integrated auto-logout handling with existing logout mechanism
- Added proper cleanup in `closeEvent()`
- Enhanced logout method to handle both manual and automatic logout

#### `central_system/main.py`
- Added inactivity monitor restart when switching students
- Added monitor cleanup when returning to login screen
- Integrated with existing window management system

## 🏗️ Technical Architecture

### Activity Detection
```python
# Events monitored for user activity
activity_events = [
    QEvent.MouseMove,
    QEvent.MouseButtonPress,
    QEvent.MouseButtonRelease,
    QEvent.KeyPress,
    QEvent.KeyRelease,
    QEvent.Wheel,
    QEvent.TouchBegin,
    QEvent.TouchUpdate,
    QEvent.TabletMove,
    QEvent.TabletPress
]
```

### Timer Management
- **Warning Timer**: 90 seconds (1.5 minutes) - Single shot timer
- **Logout Timer**: 120 seconds (2 minutes) - Single shot timer
- **Reset Logic**: Both timers restart on any detected activity

### Event Flow
1. **Student Login** → Inactivity monitor starts automatically
2. **User Activity** → Timers reset to 0, warning dialog closes if open
3. **90 seconds** → Warning dialog appears with options
4. **"Stay Logged In"** → Timers reset, dialog closes
5. **120 seconds** → Automatic logout, session cleared, redirect to login
6. **Manual Logout** → Monitor stops, normal logout flow

## 🎨 User Interface

### Warning Dialog
- **Title**: "Session Timeout Warning"
- **Message**: Clear explanation of 30-second remaining time
- **Buttons**: 
  - "Stay Logged In" (Green) - Resets timer
  - "Logout Now" (Red) - Immediate logout
- **Modal**: Prevents interaction with main application
- **Centered**: Positioned in center of screen

### Session Expired Message
- **Standard QMessageBox**: "Your session has expired due to inactivity"
- **Informational**: Not an error, just a notification
- **Automatic**: Shown before redirect to login

## 🔄 Integration Points

### Dashboard Window Integration
```python
def __init__(self, student=None, parent=None):
    # ... existing code ...
    
    # Set up inactivity monitor for automatic logout (student users only)
    self.inactivity_monitor = None
    if student:  # Only enable for students, not admin users
        self.setup_inactivity_monitor()
```

### Main Application Integration
```python
def show_dashboard_window(self, student_data=None):
    # ... existing code ...
    
    # Restart inactivity monitor for the new student
    if hasattr(self.dashboard_window, 'inactivity_monitor') and self.dashboard_window.inactivity_monitor:
        if self.dashboard_window.inactivity_monitor.is_monitoring():
            self.dashboard_window.inactivity_monitor.stop_monitoring()
        self.dashboard_window.inactivity_monitor.start_monitoring()
```

## 🧪 Testing Instructions

### Manual Testing Steps

1. **Setup**: Ensure ConsultEase is running on the Raspberry Pi
2. **Student Login**: Use RFID scan to log in as a student
3. **Monitor Start**: Verify logs show "Inactivity monitor set up for student dashboard"
4. **Wait for Warning**: 
   - Wait 1.5 minutes without any interaction
   - Warning dialog should appear
   - Test both "Stay Logged In" and "Logout Now" buttons
5. **Auto-Logout Test**:
   - Wait full 2 minutes without interaction
   - Should automatically logout and show session expired message
6. **Activity Reset Test**:
   - Start timer, move mouse before warning
   - Timer should reset and no warning should appear

### Test Script
Run `python test_auto_logout_functionality.py` to validate implementation:
- Tests component imports
- Validates configuration
- Shows usage instructions
- Displays technical details

## 🛡️ Security Considerations

### Session Management
- **Clean Logout**: Properly clears all session data
- **No Sensitive Data**: Warning dialog doesn't expose user information
- **Immediate Effect**: Auto-logout is immediate and cannot be bypassed

### User Experience
- **Clear Communication**: Users understand why logout occurred
- **Fair Warning**: 30-second warning provides opportunity to continue
- **Non-Intrusive**: Only affects student sessions, not admin workflow

## 🚀 Deployment Notes

### Requirements
- **PyQt5**: Event filtering and timer functionality
- **Existing Session System**: Integrates with current authentication
- **No External Dependencies**: Uses only built-in PyQt5 features

### Configuration
```python
# Timeout settings (in milliseconds)
TOTAL_TIMEOUT = 120000    # 2 minutes
WARNING_TIMEOUT = 90000   # 1.5 minutes (30 seconds before logout)
```

### Logging
All activities are logged with appropriate levels:
- **INFO**: Monitor start/stop, logout events
- **DEBUG**: Timer resets, activity detection
- **ERROR**: Any implementation errors

## 🔧 Maintenance

### Adjusting Timeouts
To modify timeout periods, edit `InactivityMonitor.__init__()`:
```python
self.TOTAL_TIMEOUT = 120000    # Change this value
self.WARNING_TIMEOUT = 90000   # And this value accordingly
```

### Adding Activity Types
To monitor additional events, add to the `activity_events` list in `eventFilter()`:
```python
activity_events.append(QEvent.NewEventType)
```

### Customizing Warning Dialog
Modify `InactivityWarningDialog.init_ui()` to change:
- Dialog appearance
- Button text/styling
- Message content
- Dialog size/position

## 📝 Code Quality

### Design Patterns
- **Singleton**: Global inactivity monitor instance
- **Observer**: Signal-slot connections for event handling
- **State Management**: Clean start/stop/reset state transitions

### Error Handling
- **Graceful Degradation**: System works even if monitor fails to initialize
- **Comprehensive Logging**: All errors are logged with context
- **Safe Cleanup**: Resources properly released on errors

### Performance
- **Minimal Overhead**: Event filtering is lightweight
- **Efficient Timers**: Single-shot timers prevent unnecessary processing
- **Resource Management**: Proper cleanup prevents memory leaks

## ✅ Verification Checklist

- [ ] Student login automatically starts inactivity monitoring
- [ ] Admin login does NOT start inactivity monitoring
- [ ] Mouse movement resets the timer
- [ ] Keyboard input resets the timer
- [ ] Scrolling resets the timer
- [ ] Warning appears at exactly 1.5 minutes
- [ ] "Stay Logged In" button resets the timer
- [ ] "Logout Now" button performs immediate logout
- [ ] Auto-logout occurs at exactly 2 minutes
- [ ] Session expired message is displayed
- [ ] User is redirected to login screen
- [ ] Monitor stops when user manually logs out
- [ ] Monitor restarts when new student logs in
- [ ] Monitor stops when switching to admin interface
- [ ] No memory leaks or resource issues
- [ ] Logging provides appropriate information

## 🎉 Summary

The automatic logout feature has been successfully implemented with all requirements met:

- **Robust Activity Detection**: Monitors all relevant user interactions
- **Precise Timing**: Exactly 2-minute timeout with 30-second warning
- **User-Friendly Interface**: Clear warnings and intuitive options
- **Seamless Integration**: Works with existing authentication system
- **Student-Only Scope**: Doesn't interfere with admin workflows
- **Clean Architecture**: Follows PyQt5 best practices and patterns

The feature enhances security by ensuring student sessions don't remain active indefinitely while providing a smooth user experience through clear communication and reasonable timeout periods. 
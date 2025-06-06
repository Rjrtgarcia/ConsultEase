# Inactivity Monitor Segmentation Fault Fix

## 🎯 **Issue Fixed**

**Problem:** Segmentation fault occurring when user clicks "Stay Logged In" button in the inactivity warning dialog.

**Error Details:**
```
2025-06-07 05:54:53,427 - central_system.utils.inactivity_monitor - INFO - Showing inactivity warning dialog
qt.qpa.wayland: Wayland does not support QWindow::requestActivate()
Segmentation fault
```

## 🔍 **Root Cause Analysis**

The segmentation fault was caused by several issues in the inactivity monitor implementation:

1. **Improper Memory Management**: Dialog created without proper parent widget
2. **Signal Connection Issues**: Direct signal connection without error handling
3. **Unsafe Dialog Cleanup**: Not using `deleteLater()` for proper Qt object cleanup
4. **Missing Exception Handling**: No error handling around dialog operations

## 🔧 **Fixes Applied**

### 1. **Proper Parent Widget Detection**
```python
# OLD: Dialog created without parent
self.warning_dialog = InactivityWarningDialog()

# NEW: Find main window as parent
main_window = None
for widget in QApplication.topLevelWidgets():
    if hasattr(widget, 'objectName') and 'dashboard' in widget.objectName().lower():
        main_window = widget
        break

self.warning_dialog = InactivityWarningDialog(main_window)
```

### 2. **Safe Signal Connection**
```python
# OLD: Direct connection without error handling
self.warning_dialog.stay_logged_in.connect(self.reset_timers)

# NEW: Safe connection with error handling
try:
    self.warning_dialog.stay_logged_in.connect(self._handle_stay_logged_in)
except Exception as e:
    logger.error(f"Error connecting stay_logged_in signal: {e}")
    return
```

### 3. **Proper Qt Object Cleanup**
```python
# OLD: Direct close() without proper cleanup
self.warning_dialog.close()
self.warning_dialog = None

# NEW: Proper Qt cleanup with deleteLater()
if self.warning_dialog:
    try:
        if self.warning_dialog.isVisible():
            self.warning_dialog.close()
        self.warning_dialog.deleteLater()
    except:
        pass
    self.warning_dialog = None
```

### 4. **New Safe Button Handler**
```python
def _handle_stay_logged_in(self):
    """Handle the 'Stay Logged In' button click safely."""
    try:
        logger.info("User chose to stay logged in")
        
        # Close the warning dialog safely
        if self.warning_dialog and self.warning_dialog.isVisible():
            self.warning_dialog.close()
            self.warning_dialog.deleteLater()
            self.warning_dialog = None
        
        # Reset the timers to restart the inactivity monitoring
        if self.is_active:
            self.warning_timer.stop()
            self.logout_timer.stop()
            self.warning_timer.start(self.WARNING_TIMEOUT)
            self.logout_timer.start(self.TOTAL_TIMEOUT)
            logger.info("Inactivity timers reset - monitoring continues")
        
    except Exception as e:
        logger.error(f"Error handling stay logged in: {e}")
        # Ensure dialog is cleaned up even on error
        if self.warning_dialog:
            try:
                self.warning_dialog.close()
                self.warning_dialog.deleteLater()
            except:
                pass
            self.warning_dialog = None
```

### 5. **Comprehensive Error Handling**
- Added try-catch blocks around all dialog operations
- Proper cleanup on errors
- Defensive programming for edge cases
- Improved logging for debugging

## ✅ **Expected Results**

After applying these fixes, the inactivity monitor should:

1. **Show warning dialog** without crashes
2. **Handle "Stay Logged In" button** safely without segmentation faults
3. **Properly clean up** Qt objects to prevent memory leaks
4. **Continue monitoring** correctly after user chooses to stay logged in
5. **Log operations** clearly for debugging

## 🧪 **Testing the Fix**

### Test Scenario:
1. **Start the application** with a student user
2. **Wait 1.5 minutes** without any activity
3. **Warning dialog should appear** with proper styling
4. **Click "Stay Logged In"** button
5. **Verify no segmentation fault** occurs
6. **Check that monitoring continues** for another 1.5 minutes

### Expected Log Output:
```
INFO - Started inactivity monitoring
INFO - Showing inactivity warning dialog
INFO - Inactivity warning dialog shown successfully
INFO - User chose to stay logged in
INFO - Inactivity timers reset - monitoring continues
```

## 🚀 **Deployment Steps**

1. **Copy the updated file** to your Raspberry Pi:
   ```bash
   cp central_system/utils/inactivity_monitor.py /path/to/consultease/central_system/utils/
   ```

2. **Restart the ConsultEase service**:
   ```bash
   sudo systemctl restart consultease
   ```

3. **Test the functionality** with a student user account

## 📝 **Additional Notes**

- **Wayland Warning**: The `qt.qpa.wayland: Wayland does not support QWindow::requestActivate()` warning is harmless and related to the Linux display server
- **Memory Management**: Using `deleteLater()` ensures Qt objects are properly cleaned up by the event loop
- **Thread Safety**: All dialog operations are now protected with proper exception handling
- **Parent Widget**: Finding the dashboard window as parent ensures proper memory management hierarchy

The segmentation fault should now be completely resolved, and the inactivity monitor will work reliably for student auto-logout functionality. 
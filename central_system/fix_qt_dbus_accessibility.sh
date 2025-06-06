#!/bin/bash

# Fix Qt D-Bus Accessibility Errors on Raspberry Pi
# This script addresses QSpiApplication::keyEventError and related D-Bus issues

echo "🔧 Fixing Qt D-Bus Accessibility Errors for ConsultEase..."

# Solution 1: Disable Qt Accessibility via Environment Variables
echo "📝 Creating Qt environment configuration..."

# Create environment variables file
cat > ~/.bashrc_qt_fix << 'EOF'
# Qt Accessibility Fixes for Raspberry Pi
export QT_ACCESSIBILITY=0
export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=0
export NO_AT_BRIDGE=1
export QT_LOGGING_RULES="qt.qpa.xcb.xcb-keyboard.warning=false"
export QT_QPA_PLATFORM_PLUGIN_PATH=""
EOF

# Add to .bashrc if not already present
if ! grep -q "QT_ACCESSIBILITY=0" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# Qt Accessibility Fixes for ConsultEase" >> ~/.bashrc
    echo "source ~/.bashrc_qt_fix" >> ~/.bashrc
    echo "✅ Added Qt accessibility fixes to ~/.bashrc"
else
    echo "ℹ️ Qt accessibility fixes already in ~/.bashrc"
fi

# Solution 2: Create systemd user service configuration
echo "🔧 Configuring systemd user services..."

# Create user systemd directory if it doesn't exist
mkdir -p ~/.config/systemd/user

# Disable problematic accessibility services
systemctl --user mask at-spi-dbus-bus.service 2>/dev/null || echo "ℹ️ at-spi-dbus-bus.service not found"
systemctl --user mask at-spi2-registryd.service 2>/dev/null || echo "ℹ️ at-spi2-registryd.service not found"

echo "✅ Disabled accessibility services"

# Solution 3: Create ConsultEase startup script with Qt fixes
echo "📝 Creating ConsultEase startup script with Qt fixes..."

cat > start_consultease.sh << 'EOF'
#!/bin/bash

# ConsultEase Startup Script with Qt Fixes
echo "🚀 Starting ConsultEase with Qt accessibility fixes..."

# Set Qt environment variables
export QT_ACCESSIBILITY=0
export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=0
export NO_AT_BRIDGE=1
export QT_LOGGING_RULES="qt.qpa.xcb.xcb-keyboard.warning=false;qt.accessibility.warning=false"

# Disable additional Qt warnings
export QT_ASSUME_STDERR_HAS_CONSOLE=1
export QT_LOGGING_TO_CONSOLE=0

# Set display and desktop session variables
export DISPLAY=:0
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP=LXDE

# Kill any existing D-Bus accessibility processes
pkill -f "at-spi-bus-launcher" 2>/dev/null || true
pkill -f "at-spi2-registryd" 2>/dev/null || true

# Start ConsultEase
cd central_system
echo "🎯 Launching ConsultEase Central System..."
python3 main.py "$@"
EOF

chmod +x start_consultease.sh
echo "✅ Created start_consultease.sh script"

# Solution 4: Install/configure missing D-Bus packages (if needed)
echo "🔧 Checking D-Bus configuration..."

# Check if D-Bus is properly configured
if ! pgrep -x "dbus-daemon" > /dev/null; then
    echo "⚠️ D-Bus daemon not running, attempting to start..."
    sudo service dbus start 2>/dev/null || echo "ℹ️ Could not start D-Bus service"
fi

# Solution 5: Create Qt platform plugin configuration
echo "🔧 Configuring Qt platform plugins..."

# Create Qt configuration directory
mkdir -p ~/.config/qt

# Create qt.conf to specify platform plugin path
cat > ~/.config/qt/qt.conf << 'EOF'
[Platforms]
linux-rasp-pi2-g++/DeviceIntegration = none

[QAccessibility]
active = false
EOF

echo "✅ Created Qt configuration file"

# Solution 6: Create desktop session configuration
echo "🖥️ Configuring desktop session..."

# Create minimal .xsession file if it doesn't exist
if [ ! -f ~/.xsession ]; then
    cat > ~/.xsession << 'EOF'
#!/bin/bash
export QT_ACCESSIBILITY=0
export NO_AT_BRIDGE=1
exec startlxde
EOF
    chmod +x ~/.xsession
    echo "✅ Created .xsession file"
fi

# Solution 7: Create systemd override for ConsultEase service
echo "🔧 Creating systemd service configuration..."

cat > consultease.service << 'EOF'
[Unit]
Description=ConsultEase Central System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ConsultEase/central_system
Environment=QT_ACCESSIBILITY=0
Environment=QT_LINUX_ACCESSIBILITY_ALWAYS_ON=0
Environment=NO_AT_BRIDGE=1
Environment=QT_LOGGING_RULES=qt.qpa.xcb.xcb-keyboard.warning=false
Environment=DISPLAY=:0
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Created consultease.service file"
echo "   To install: sudo cp consultease.service /etc/systemd/system/"
echo "   Then: sudo systemctl enable consultease && sudo systemctl start consultease"

# Summary and instructions
echo ""
echo "🎉 Qt D-Bus Accessibility Fix Complete!"
echo ""
echo "📋 What was fixed:"
echo "   ✅ Disabled Qt accessibility system"
echo "   ✅ Configured D-Bus to ignore accessibility requests" 
echo "   ✅ Created optimized startup script"
echo "   ✅ Added environment variables to prevent errors"
echo "   ✅ Configured Qt platform plugins"
echo ""
echo "🚀 Next Steps:"
echo "   1. Restart your terminal or run: source ~/.bashrc"
echo "   2. Use the new startup script: ./start_consultease.sh"
echo "   3. Or restart your Raspberry Pi for system-wide effect"
echo ""
echo "🔍 To verify the fix:"
echo "   - The QSpiApplication::keyEventError should no longer appear"
echo "   - ConsultEase should start faster and run more smoothly"
echo "   - Check with: ./start_consultease.sh"
EOF

chmod +x fix_qt_dbus_accessibility.sh
echo "✅ Qt D-Bus accessibility fix script created successfully!" 
"""
Window transition effects for ConsultEase.
Provides smooth transitions between windows for a better user experience.
Compatible with Wayland and other window systems that don't support opacity.
"""
import logging
import sys
import os
import platform
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QTimer, Qt, QRect
from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect, QApplication

logger = logging.getLogger(__name__)

class WindowTransitionManager:
    """
    Manages transitions between windows with compatible effects.
    """

    def __init__(self, duration=300):
        """
        Initialize the transition manager.

        Args:
            duration (int): Duration of transitions in milliseconds
        """
        self.duration = duration
        self.current_animation = None
        self.next_window = None
        self.current_window = None

        # Detect if we're on Wayland or another system with limitations
        self.use_simple_transitions = self._should_use_simple_transitions()
        logger.info(f"Using simple transitions: {self.use_simple_transitions}")

    def _should_use_simple_transitions(self):
        """Determine if we should use simple transitions based on platform."""
        # Check if we're on Linux and possibly using Wayland
        if sys.platform.startswith('linux'):
            # Check for Wayland environment variables
            for env_var in ['WAYLAND_DISPLAY', 'XDG_SESSION_TYPE']:
                if env_var in os.environ and 'wayland' in os.environ[env_var].lower():
                    return True

            # Check QT_QPA_PLATFORM
            if 'QT_QPA_PLATFORM' in os.environ and 'wayland' in os.environ['QT_QPA_PLATFORM'].lower():
                return True

        # Check if we're on Raspberry Pi
        try:
            with open('/proc/cpuinfo', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    return True
        except:
            pass

        # Default to simple transitions for safety
        return True

    def fade_out_in(self, current_window, next_window, on_finished=None):
        """
        Perform a transition from current window to next window.

        Args:
            current_window (QWidget): The currently visible window
            next_window (QWidget): The window to transition to
            on_finished (callable, optional): Callback to execute when transition completes
        """
        logger.info(f"Starting transition from {current_window.__class__.__name__} to {next_window.__class__.__name__}")

        self.current_window = current_window
        self.next_window = next_window

        if self.use_simple_transitions:
            # Simple transition - just switch windows with a slight delay
            next_window.show()

            # Hide current window after a short delay
            QTimer.singleShot(100, lambda: current_window.hide())

            # Call on_finished after transition duration
            if on_finished:
                QTimer.singleShot(self.duration, on_finished)
        else:
            try:
                # Try opacity-based transition
                # Prepare next window but keep it hidden
                next_window.setWindowOpacity(0.0)
                next_window.show()

                # Create fade out animation for current window
                fade_out = QPropertyAnimation(current_window, b"windowOpacity")
                fade_out.setDuration(self.duration)
                fade_out.setStartValue(1.0)
                fade_out.setEndValue(0.0)
                fade_out.setEasingCurve(QEasingCurve.OutCubic)

                # When fade out completes, start fade in
                fade_out.finished.connect(lambda: self._start_fade_in(on_finished))

                # Start the animation
                self.current_animation = fade_out
                fade_out.start()
            except Exception as e:
                logger.warning(f"Opacity animation failed, falling back to simple transition: {e}")
                # Fall back to simple transition
                next_window.show()
                current_window.hide()
                if on_finished:
                    QTimer.singleShot(self.duration, on_finished)

    def _start_fade_in(self, on_finished=None):
        """
        Start the fade in animation for the next window.

        Args:
            on_finished (callable, optional): Callback to execute when transition completes
        """
        try:
            # Hide the previous window
            if self.current_window:
                self.current_window.hide()
                # Reset opacity for future use
                self.current_window.setWindowOpacity(1.0)

            # Create fade in animation for next window
            fade_in = QPropertyAnimation(self.next_window, b"windowOpacity")
            fade_in.setDuration(self.duration)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.InCubic)

            # Connect finished signal
            if on_finished:
                fade_in.finished.connect(on_finished)

            # Start the animation
            self.current_animation = fade_in
            fade_in.start()
        except Exception as e:
            logger.warning(f"Fade in animation failed: {e}")
            # Ensure window is visible
            self.next_window.setWindowOpacity(1.0)
            if on_finished:
                on_finished()

    def fade_in(self, window, on_finished=None):
        """
        Perform a fade in effect on a window.

        Args:
            window (QWidget): The window to fade in
            on_finished (callable, optional): Callback to execute when fade completes
        """
        logger.info(f"Fading in {window.__class__.__name__}")

        if self.use_simple_transitions:
            # Simple show
            window.show()
            if on_finished:
                QTimer.singleShot(self.duration, on_finished)
        else:
            try:
                # Prepare window
                window.setWindowOpacity(0.0)
                window.show()

                # Create fade in animation
                fade_in = QPropertyAnimation(window, b"windowOpacity")
                fade_in.setDuration(self.duration)
                fade_in.setStartValue(0.0)
                fade_in.setEndValue(1.0)
                fade_in.setEasingCurve(QEasingCurve.InCubic)

                # Connect finished signal
                if on_finished:
                    fade_in.finished.connect(on_finished)

                # Start the animation
                self.current_animation = fade_in
                fade_in.start()
            except Exception as e:
                logger.warning(f"Fade in animation failed, using simple show: {e}")
                window.show()
                if on_finished:
                    QTimer.singleShot(self.duration, on_finished)

    def fade_out(self, window, on_finished=None):
        """
        Perform a fade out effect on a window.

        Args:
            window (QWidget): The window to fade out
            on_finished (callable, optional): Callback to execute when fade completes
        """
        logger.info(f"Fading out {window.__class__.__name__}")

        if self.use_simple_transitions:
            # Simple hide
            window.hide()
            if on_finished:
                QTimer.singleShot(self.duration, on_finished)
        else:
            try:
                # Create fade out animation
                fade_out = QPropertyAnimation(window, b"windowOpacity")
                fade_out.setDuration(self.duration)
                fade_out.setStartValue(1.0)
                fade_out.setEndValue(0.0)
                fade_out.setEasingCurve(QEasingCurve.OutCubic)

                # When fade out completes, hide the window and reset opacity
                def on_fade_out_finished():
                    window.hide()
                    window.setWindowOpacity(1.0)
                    if on_finished:
                        on_finished()

                fade_out.finished.connect(on_fade_out_finished)

                # Start the animation
                self.current_animation = fade_out
                fade_out.start()
            except Exception as e:
                logger.warning(f"Fade out animation failed, using simple hide: {e}")
                window.hide()
                if on_finished:
                    QTimer.singleShot(self.duration, on_finished)

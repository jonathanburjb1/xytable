"""
Movement controller for the X-Y Table Control System.

Handles high-level movement logic and coordination between axes.
"""

import logging
import time
from typing import Optional

from src.utils.logging import log_movement_event
from src.hardware.mesa_driver import MesaDriver


class MovementController:
    """Controls movement operations for the X-Y table."""
    
    def __init__(self, config_manager):
        """
        Initialize the movement controller.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Movement state
        self._emergency_stop_active = False
        self._movement_in_progress = False
        
        self.mesa_driver = MesaDriver(config_manager)
        
        self.logger.info("Movement controller initialized")
    
    def move_single_axis(self, axis: str, distance: Optional[float] = None, speed: Optional[float] = None) -> None:
        """
        Move a single axis by the specified distance in inches.
        Args:
            axis: Axis name ('x' or 'y')
            distance: Distance to move in inches (positive = forward, negative = backward)
            speed: Movement speed in inches per second (optional)
        """
        if self._emergency_stop_active:
            raise RuntimeError("Emergency stop is active - movement blocked")
        if distance is None:
            distance = 0.0
        distance = float(distance)
        if speed is None:
            speed = float(self.config.get('movement.default_speed', 1.0))
        else:
            speed = float(speed)
        self._validate_movement(axis, distance, speed)
        self.logger.info(f"Starting {axis} axis movement: {distance} inches at {speed} inches/sec")
        log_movement_event(self.logger, axis, "started", distance, speed)
        try:
            self._movement_in_progress = True
            if not self.mesa_driver.is_connected():
                self.mesa_driver.connect()
            if not self.mesa_driver.move_axis(axis, distance, speed):
                raise RuntimeError(f"MesaDriver failed to move {axis} axis")
            log_movement_event(self.logger, axis, "completed", distance, speed)
            self.logger.info(f"{axis} axis movement completed")
        except Exception as e:
            log_movement_event(self.logger, axis, "failed", distance, speed)
            self.logger.error(f"{axis} axis movement failed: {e}")
            raise
        finally:
            self._movement_in_progress = False
    def move_absolute(self, x_position: Optional[float] = None, y_position: Optional[float] = None, speed: Optional[float] = None) -> None:
        """
        Move both axes to the specified absolute positions in inches.
        Args:
            x_position: Absolute X position in inches
            y_position: Absolute Y position in inches
            speed: Movement speed in inches per second (optional)
        """
        if self._emergency_stop_active:
            raise RuntimeError("Emergency stop is active - movement blocked")
        if x_position is None:
            x_position = 0.0
        if y_position is None:
            y_position = 0.0
        x_position = float(x_position)
        y_position = float(y_position)
        if speed is None:
            speed = float(self.config.get('movement.default_speed', 1.0))
        else:
            speed = float(speed)
        self._validate_movement('x', x_position, speed)
        self._validate_movement('y', y_position, speed)
        self.logger.info(f"Starting absolute movement: X={x_position} in, Y={y_position} in at {speed} in/sec")
        log_movement_event(self.logger, 'x', "started (absolute)", x_position, speed)
        log_movement_event(self.logger, 'y', "started (absolute)", y_position, speed)
        try:
            self._movement_in_progress = True
            if not self.mesa_driver.is_connected():
                self.mesa_driver.connect()
            self.mesa_driver.move_absolute(x_position, y_position)
            log_movement_event(self.logger, 'x', "completed (absolute)", x_position, speed)
            log_movement_event(self.logger, 'y', "completed (absolute)", y_position, speed)
            self.logger.info("Absolute movement completed")
        except Exception as e:
            log_movement_event(self.logger, 'x', "failed (absolute)", x_position, speed)
            log_movement_event(self.logger, 'y', "failed (absolute)", y_position, speed)
            self.logger.error(f"Absolute movement failed: {e}")
            raise
        finally:
            self._movement_in_progress = False
    
    def move_coordinated(self, x_distance: Optional[float] = None, y_distance: Optional[float] = None, speed: Optional[float] = None) -> None:
        """
        Move both axes simultaneously in a coordinated manner (in inches).
        Args:
            x_distance: Distance to move X axis (inches)
            y_distance: Distance to move Y axis (inches)
            speed: Movement speed in inches per second (optional)
        """
        if self._emergency_stop_active:
            raise RuntimeError("Emergency stop is active - movement blocked")
        if x_distance is None:
            x_distance = 0.0
        if y_distance is None:
            y_distance = 0.0
        x_distance = float(x_distance)
        y_distance = float(y_distance)
        if speed is None:
            speed = float(self.config.get('movement.default_speed', 1.0))
        else:
            speed = float(speed)
        self._validate_movement('x', x_distance, speed)
        self._validate_movement('y', y_distance, speed)
        self.logger.info(f"Starting coordinated movement: X={x_distance} in, Y={y_distance} in at {speed} in/sec")
        log_movement_event(self.logger, 'x', "started (coordinated)", x_distance, speed)
        log_movement_event(self.logger, 'y', "started (coordinated)", y_distance, speed)
        try:
            self._movement_in_progress = True
            if not self.mesa_driver.is_connected():
                self.mesa_driver.connect()
            if not self.mesa_driver.move_axis('x', x_distance, speed):
                raise RuntimeError("MesaDriver failed to move x axis")
            if not self.mesa_driver.move_axis('y', y_distance, speed):
                raise RuntimeError("MesaDriver failed to move y axis")
            log_movement_event(self.logger, 'x', "completed (coordinated)", x_distance, speed)
            log_movement_event(self.logger, 'y', "completed (coordinated)", y_distance, speed)
            self.logger.info("Coordinated movement completed")
        except Exception as e:
            log_movement_event(self.logger, 'x', "failed (coordinated)", x_distance, speed)
            log_movement_event(self.logger, 'y', "failed (coordinated)", y_distance, speed)
            self.logger.error(f"Coordinated movement failed: {e}")
            raise
        finally:
            self._movement_in_progress = False
    
    def home_axes(self, speed: float = 0.0) -> None:
        """
        Home both axes to their reference positions using MesaDriver.
        Args:
            speed: Homing speed in inches per second (optional, not used by LinuxCNC home)
        """
        if speed is None:
            speed = 0.0
        else:
            speed = float(speed)
        self.logger.info("Starting homing sequence")
        try:
            self._movement_in_progress = True
            if not self.mesa_driver.is_connected():
                self.mesa_driver.connect()
            if not self.mesa_driver.home_all_axes():
                raise RuntimeError("MesaDriver failed to home all axes")
            self.logger.info("Homing sequence completed")
        except Exception as e:
            self.logger.error(f"Homing sequence failed: {e}")
            raise
        finally:
            self._movement_in_progress = False
    
    def emergency_stop(self) -> None:
        """Emergency stop - halt all movement immediately using MesaDriver."""
        self.logger.warning("Emergency stop activated")
        self._emergency_stop_active = True
        try:
            if not self.mesa_driver.is_connected():
                self.mesa_driver.connect()
            self.mesa_driver.emergency_stop()
            self.logger.info("Emergency stop completed")
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")
            raise
    
    def clear_emergency_stop(self) -> None:
        """Clear the emergency stop state using MesaDriver."""
        self.logger.info("Clearing emergency stop")
        self._emergency_stop_active = False
        try:
            if not self.mesa_driver.is_connected():
                self.mesa_driver.connect()
            self.mesa_driver.clear_emergency_stop()
        except Exception as e:
            self.logger.error(f"Clear emergency stop failed: {e}")
            raise
    
    def _validate_movement(self, axis: str, distance: float, speed: float) -> None:
        """
        Validate movement parameters (in inches and inches/sec).
        Args:
            axis: Axis name
            distance: Distance in inches
            speed: Movement speed in inches/sec
        """
        max_speed = self.config.get(f'hardware.{axis}_axis.motor.max_speed', 10.0)
        if speed > max_speed:
            raise ValueError(f"Speed {speed} exceeds maximum {max_speed} for {axis} axis")
        # TODO: Implement position limit checking if needed
    
    @property
    def emergency_stop_active(self) -> bool:
        """Check if emergency stop is active."""
        return self._emergency_stop_active
    
    def get_emergency_stop_status(self) -> bool:
        """Get the actual emergency stop status from the Mesa driver."""
        try:
            if not self.mesa_driver.is_connected():
                self.mesa_driver.connect()
            mesa_status = self.mesa_driver.read_status()
            if mesa_status.get('connected', False):
                self._emergency_stop_active = mesa_status.get('emergency_stop', False)
                return self._emergency_stop_active
            else:
                return self._emergency_stop_active
        except Exception as e:
            self.logger.error(f"Error getting emergency stop status: {e}")
            return self._emergency_stop_active
    
    @property
    def movement_in_progress(self) -> bool:
        """Check if movement is currently in progress."""
        return self._movement_in_progress

    def start_jog(self, axis: str, direction: int, speed: float) -> None:
        """
        Start continuous jog movement on the specified axis.
        Args:
            axis: 'x' or 'y'
            direction: +1 for positive, -1 for negative
            speed: inches per second (positive float)
        """
        if self._emergency_stop_active:
            raise RuntimeError("Emergency stop is active - jog blocked")
        self.logger.info(f"Starting jog: axis={axis}, direction={direction}, speed={speed}")
        try:
            if not self.mesa_driver.is_connected():
                self.mesa_driver.connect()
            if not self.mesa_driver.start_jog(axis, direction, speed):
                raise RuntimeError(f"MesaDriver failed to start jog on {axis} axis")
        except Exception as e:
            self.logger.error(f"Jog start failed: {e}")
            raise

    def stop_jog(self, axis: str) -> None:
        """
        Stop jog movement on the specified axis using MesaDriver.
        Args:
            axis: 'x' or 'y'
        """
        self.logger.info(f"Stopping jog: axis={axis}")
        try:
            if not self.mesa_driver.is_connected():
                self.mesa_driver.connect()
            if not self.mesa_driver.stop_jog(axis):
                raise RuntimeError(f"MesaDriver failed to stop jog on {axis} axis")
        except Exception as e:
            self.logger.error(f"Failed to stop jog on {axis} axis: {e}")
            raise

    def set_io(self, io_name: str, state: bool) -> None:
        """
        Set the state of an IO output using MesaDriver.
        Args:
            io_name: IO name ('down' for mist/coolant, 'start' for flood)
            state: True to turn on, False to turn off
        """
        if io_name not in ['down', 'start']:
            raise ValueError(f"Invalid IO name: {io_name}. Use 'down' for mist or 'start' for flood")
        
        # Map IO names to channel numbers
        io_channel = 0 if io_name == 'down' else 1  # down=mist=0, start=flood=1
        
        self.logger.info(f"Setting {io_name} (channel {io_channel}) to {'ON' if state else 'OFF'}")
        try:
            if not self.mesa_driver.is_connected():
                self.mesa_driver.connect()
            if not self.mesa_driver.set_io(io_channel, state):
                raise RuntimeError(f"MesaDriver failed to set {io_name} to {state}")
            self.logger.info(f"{io_name} set to {'ON' if state else 'OFF'}")
        except Exception as e:
            self.logger.error(f"Failed to set {io_name}: {e}")
            raise

"""
Mesa 7I96S driver for X-Y Table Control System.

This module provides a driver interface for Mesa 7I96S boards using LinuxCNC.
"""

import logging
import struct
import importlib
from typing import Dict, Any, Optional
from enum import Enum

try:
    import linuxcnc
except ImportError:
    linuxcnc = None


class MesaDriver:
    """
    Driver for Mesa 7I96S board using LinuxCNC.
    
    This driver provides a high-level interface for controlling stepper motors
    and reading I/O through the Mesa 7I96S board using LinuxCNC's hostmot2 driver.
    """
    
    def __init__(self, config_manager):
        """
        Initialize the Mesa driver.
        
        Args:
            config_manager: Configuration manager instance
        """
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),  # Log to console
                logging.FileHandler('mesa_driver.log')  # Log to file
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Get Mesa configuration
        mesa_config = config_manager.get_mesa_config()
        self.ip = mesa_config['ip_address']
        self.port = mesa_config['port']
        self.timeout = mesa_config['timeout']
        
        # Connection state
        self._connected = False
        self._emergency_stop = False
        
        # Limit switch states
        self._limit_switches = {
            'x_min': False,
            'x_max': False,
            'y_min': False,
            'y_max': False
        }
        
        # LinuxCNC components (to be initialized)
        self.command = None
        self.status = None
        self.error = None
        
        self.logger.info(f"Mesa driver initialized for {self.ip}:{self.port}")
    
    def connect(self) -> bool:
        """
        Connect to the Mesa board via LinuxCNC.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to Mesa 7I96S at {self.ip}:{self.port}")

            if linuxcnc is None:
                raise RuntimeError("linuxcnc Python module not available")
            
            importlib.reload(linuxcnc)

            # Initialize LinuxCNC components
            self.status = linuxcnc.stat()
            self.command = linuxcnc.command()
            self.error = linuxcnc.error_channel()
            
            # Test if we can actually communicate with LinuxCNC
            self.status.poll()
            
            self._connected = True
            self.logger.info("Successfully connected to Mesa board via LinuxCNC")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Mesa board: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the Mesa board."""
        self.logger.info("Disconnecting from Mesa 7I96S")
        self._connected = False
        self.status = None
        self.command = None
        self.error = None
    
    def is_connected(self) -> bool:
        """Check if connected to the Mesa board."""
        return self._connected
    
    def read_status(self):
        """
        Request and parse the status packet from the Mesa board.
        
        Returns:
            Parsed status information
        """
        self.logger.debug("Reading status via LinuxCNC")
        if not self.is_connected():
            return {
                'connected': False,
                'error': 'Not connected'
            }
        
        try:
            if self.status is None:
                return {
                    'connected': False,
                    'error': 'Status object not available'
                }
            
            self.status.poll()
            
            # Machine state - only use available constants
            if linuxcnc is not None:
                state_map = {
                    linuxcnc.RCS_DONE: 'done',
                    linuxcnc.RCS_EXEC: 'exec',
                    linuxcnc.RCS_ERROR: 'error',
                }
            else:
                state_map = {}
                
            task_state = getattr(self.status, 'task_state', None)
            machine_state = state_map.get(task_state, str(task_state) if task_state is not None else 'unknown')
            
            # Axis status
            x_axis = self.status.axis[0]
            y_axis = self.status.axis[1]
            axis_positions = [self.status.position[i] for i in range(2)]
            
            # TODO: Read actual limit switches from Mesa board via HAL pins
            # This requires mapping the limit switch inputs to HAL pins in the configuration
            limit_switches = self._limit_switches.copy()
            
            # Emergency stop
            estop = self.status.estop
            self.logger.info(f"Estop: {estop}")
            
            return {
                'connected': True,
                'machine_state': machine_state,
                'x_axis': {
                    'velocity': x_axis.get('velocity'),
                    'min_position_limit': x_axis.get('min_position_limit'),
                    'max_position_limit': x_axis.get('max_position_limit'),
                    'position': axis_positions[0],
                },
                'y_axis': {
                    'velocity': y_axis.get('velocity'),
                    'min_position_limit': y_axis.get('min_position_limit'),
                    'max_position_limit': y_axis.get('max_position_limit'),
                    'position': axis_positions[1],
                },
                'limit_switches': limit_switches,
                'emergency_stop': estop,
                'error': None
            }
            
        except Exception as e:
            self.logger.error(f"Error reading status: {e}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def disable_axis(self, axis: str) -> bool:
        """
        Disable the specified axis using LinuxCNC.
        """
        if axis not in ['x', 'y']:
            self.logger.error(f"Invalid axis: {axis}")
            return False
        if not self.is_connected():
            self.logger.error("Cannot disable axis - not connected")
            return False
        try:
            axis_index = 0 if axis == 'x' else 1
            if self.command is None:
                self.logger.error("LinuxCNC command object not available")
                return False
            self.command.disable(axis_index)
            self.logger.info(f"Disabled {axis} axis via LinuxCNC")
            return True
        except Exception as e:
            self.logger.error(f"Failed to disable {axis} axis: {e}")
            return False

    def move_axis(self, axis: str, distance: float, speed: float) -> bool:
        """
        Move the specified axis by a distance in inches at a given speed using LinuxCNC.
        """
        if axis not in ['x', 'y']:
            self.logger.error(f"Invalid axis: {axis}")
            return False
        if not self.is_connected():
            self.logger.error("Cannot move axis - not connected")
            return False
        if linuxcnc is None:
            self.logger.error("linuxcnc Python module not available")
            return False
        try:
            axis_index = 0 if axis == 'x' else 1
            if self.command is None or self.status is None:
                self.logger.error("LinuxCNC command or status object not available")
                return False
            
            # Check if machine is in the right state
            self.status.poll()
            if self.status.task_state != linuxcnc.RCS_DONE:
                self.logger.warning(f"Machine not ready, task_state: {self.status.task_state}")
                # Try to abort any current operation
                try:
                    self.command.abort()
                except:
                    pass
            
            # Use jog command with distance in inches and speed in inches/sec
            # Set teleop mode and send jog command
            self.command.teleop_enable(0)  # Enable teleop mode
            self.command.jog(linuxcnc.JOG_INCREMENT, True, axis_index, speed, distance)
            
            # Don't wait for completion - return immediately
            self.logger.info(f"Jog command sent for {axis} axis: {distance} inches at {speed} inches/sec")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to move {axis} axis: {e}")
            return False

    def get_position(self, axis: str) -> float:
        """
        Get current position of a specific axis from LinuxCNC status in inches.
        """
        if axis not in ['x', 'y']:
            self.logger.error(f"Invalid axis: {axis}")
            return 0.0
        if not self.is_connected() or self.status is None:
            self.logger.error("Cannot get position - not connected or status unavailable")
            return 0.0
        try:
            self.status.poll()
            axis_index = 0 if axis == 'x' else 1
            # Get position directly in machine units (inches)
            position_inches = self.status.position[axis_index]
            self.logger.debug(f"{axis} axis position: {position_inches} inches")
            return position_inches
        except Exception as e:
            self.logger.error(f"Failed to get {axis} axis position: {e}")
            return 0.0
    
    def emergency_stop(self) -> bool:
        """
        Emergency stop - halt all movement immediately.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            self.logger.error("Cannot send emergency stop - not connected")
            return False
        
        try:
            if self.command is not None:
                #self.command.abort()
                self.command.state(linuxcnc.STATE_ESTOP)

            self.logger.warning("Emergency stop command sent via LinuxCNC")
            self._emergency_stop = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to send emergency stop command: {e}")
            return False
    
    def clear_emergency_stop(self) -> bool:
        """
        Clear emergency stop state using LinuxCNC.
        """
        if not self.is_connected():
            self.logger.error("Cannot clear emergency stop - not connected")
            return False
        try:
            if self.command is not None:
                #self.command.estop_reset()
                self.command.state(linuxcnc.STATE_ESTOP_RESET)
                self.command.wait_complete()
                self.command.state(linuxcnc.STATE_ON)
                self.command.wait_complete()

            self._emergency_stop = False
            self.logger.info("Emergency stop cleared via LinuxCNC")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear emergency stop: {e}")
            return False
    
    def get_limit_switches(self) -> Dict[str, bool]:
        """
        Get the current state of all limit switches from LinuxCNC status/HAL pins.
        """
        if not self.is_connected():
            self.logger.error("Cannot read limit switches - not connected")
            return self._limit_switches.copy()
        try:
            if self.status is not None:
                self.status.poll()
                # Example: Assume limit switches are mapped to status.aux_input or similar
                # This will need to be adapted to your HAL configuration
                # For demonstration, we use dummy values
                # Replace with actual HAL pin reading logic
                limit_switches = {
                    'x_min': getattr(self.status, 'x_min_limit', False),
                    'x_max': getattr(self.status, 'x_max_limit', False),
                    'y_min': getattr(self.status, 'y_min_limit', False),
                    'y_max': getattr(self.status, 'y_max_limit', False),
                }
                self.logger.debug(f"Limit switch states: {limit_switches}")
                return limit_switches
            else:
                return self._limit_switches.copy()
        except Exception as e:
            self.logger.error(f"Error reading limit switches: {e}")
            return self._limit_switches.copy()
    
    def home_axis(self, axis: str) -> bool:
        """
        Home the specified axis to its reference position.
        
        Args:
            axis: Axis to home ('x' or 'y')
            
        Returns:
            True if homing command sent successfully, False otherwise
        """
        if not self.is_connected():
            self.logger.error(f"Cannot home {axis} axis - not connected")
            return False
        
        if axis not in ['x', 'y']:
            self.logger.error(f"Invalid axis: {axis}. Must be 'x' or 'y'")
            return False
        
        try:
            self.logger.info(f"Homing {axis} axis")
            
            # Use LinuxCNC command to home the axis
            if self.command is None:
                self.logger.error("LinuxCNC command object not available")
                return False
            
            # Send homing command to LinuxCNC
            # The axis index is 0 for X, 1 for Y
            axis_index = 0 if axis == 'x' else 1
            
            # Home the specific axis
            self.command.home(axis_index)
            
            self.logger.info(f"Homing command sent for {axis} axis")
            return True
            
        except Exception as e:
            self.logger.error(f"Error homing {axis} axis: {e}")
            return False
    
    def home_all_axes(self) -> bool:
        """
        Home all axes to their reference positions.
        Only run on startup. Error is thown if homing has already been performed.

        Returns:
            True if homing command sent successfully, False otherwise
        """
        if not self.is_connected():
            self.logger.error("Cannot home axes - not connected")
            return False
        
        try:
            self.logger.info("Homing all axes")
            
            if self.command is None:
                self.logger.error("LinuxCNC command object not available")
                return False
            
            # Home all axes
            self.command.home(-1)  # -1 means home all axes
            self.command.wait_complete()
            
            self.logger.info("Homing command sent for all axes")
            return True
            
        except Exception as e:
            self.logger.error(f"Error homing all axes: {e}")
            return False
    
    def is_axis_homed(self, axis: str) -> bool:
        """
        Check if the specified axis is homed.
        
        Args:
            axis: Axis to check ('x' or 'y')
            
        Returns:
            True if axis is homed, False otherwise
        """
        if not self.is_connected():
            self.logger.error(f"Cannot check homing status for {axis} axis - not connected")
            return False
        
        if axis not in ['x', 'y']:
            self.logger.error(f"Invalid axis: {axis}. Must be 'x' or 'y'")
            return False
        
        try:
            if self.status is None:
                self.logger.error("LinuxCNC status object not available")
                return False
            
            self.status.poll()
            
            # Check homing status for the specific axis
            axis_index = 0 if axis == 'x' else 1
            is_homed = self.status.axis[axis_index]['homed']
            
            self.logger.debug(f"{axis} axis homed: {is_homed}")
            return is_homed
            
        except Exception as e:
            self.logger.error(f"Error checking homing status for {axis} axis: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get overall board status.
        
        Returns:
            Dictionary containing board status information
        """
        if not self.is_connected():
            return {
                'connected': False,
                'emergency_stop': self._emergency_stop,
                'limit_switches': self._limit_switches.copy(),
                'error_state': True
            }
        
        try:
            response = self.read_status()
            
            if response.get('connected', False):
                status_data = {
                    'connected': True,
                    'emergency_stop': self._emergency_stop,
                    'limit_switches': self.get_limit_switches(),
                    'error_state': False
                }
                return status_data
            else:
                return {
                    'connected': False,
                    'emergency_stop': self._emergency_stop,
                    'limit_switches': self._limit_switches.copy(),
                    'error_state': True
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            return {
                'connected': False,
                'emergency_stop': self._emergency_stop,
                'limit_switches': self._limit_switches.copy(),
                'error_state': True
            }
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def move_absolute(self, x: float = 0.0, y: float = 0.0) -> bool:
        """
        Move to an absolute X/Y position in inches using MDI mode and a G0 command.
        Args:
            x: Absolute X position in inches
            y: Absolute Y position in inches
        Returns:
            True if the command was sent successfully, False otherwise
        """
        if not self.is_connected():
            self.logger.error("Cannot move absolute - not connected")
            return False
        if self.command is None:
            self.logger.error("LinuxCNC command object not available")
            return False
        if linuxcnc is None:
            self.logger.error("linuxcnc Python module not available")
            return False
        try:
            # Put LinuxCNC in MDI mode
            self.command.mode(linuxcnc.MODE_MDI)
            self.command.wait_complete()
            # Build G0 command string
            cmd = f"G0 X{x:.4f} Y{y:.4f}"
            self.logger.info(f"Sending MDI command: {cmd}")
            self.command.mdi(cmd)
            self.command.wait_complete()
            self.logger.info(f"Absolute move to X={x} Y={y} completed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to move absolute: {e}")
            return False

    def set_io(self, io_channel: int, state: bool) -> bool:
        """
        Set the state of the flood (1) or mist (0) output using LinuxCNC.
        Args:
            io_channel: 1 for flood, 0 for mist
            state: True to turn on, False to turn off
        Returns:
            True if the command was sent successfully, False otherwise
        """
        if not self.is_connected():
            self.logger.error("Cannot set IO - not connected")
            return False
        if self.command is None:
            self.logger.error("LinuxCNC command object not available")
            return False
        if linuxcnc is None:
            self.logger.error("linuxcnc Python module not available")
            return False
        try:
            if io_channel == 1:
                # Flood
                self.logger.info(f"Setting flood to {'ON' if state else 'OFF'}")
                self.command.flood(state)
            elif io_channel == 0:
                # Mist
                self.logger.info(f"Setting mist to {'ON' if state else 'OFF'}")
                self.command.mist(state)
            else:
                self.logger.error(f"Invalid IO channel: {io_channel}. Use 1 for flood, 0 for mist.")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Failed to set IO channel {io_channel}: {e}")
            return False

    def start_jog(self, axis: str, direction: int, speed: float) -> bool:
        """
        Start continuous jog movement on the specified axis using LinuxCNC.
        Args:
            axis: 'x' or 'y'
            direction: +1 for positive, -1 for negative
            speed: inches per second (positive float)
        Returns:
            True if jog command sent successfully, False otherwise
        Note:
            Uses joint jog mode (jjogmode=True, teleop_enable(0)).
        """
        if axis not in ['x', 'y']:
            self.logger.error(f"Invalid axis: {axis}")
            return False
        if direction not in [1, -1]:
            self.logger.error(f"Invalid direction: {direction}")
            return False
        if not self.is_connected():
            self.logger.error("Cannot jog axis - not connected")
            return False
        if self.command is None or self.status is None:
            self.logger.error("LinuxCNC command or status object not available")
            return False
        if linuxcnc is None:
            self.logger.error("linuxcnc Python module not available")
            return False
        try:
            axis_index = 0 if axis == 'x' else 1
            self.status.poll()
            # Enable joint jog mode
            self.command.teleop_enable(0)
            self.command.jog(linuxcnc.JOG_CONTINUOUS, True, axis_index, abs(speed) * direction)
            self.logger.info(f"Started continuous jog on {axis} axis at {speed} in/s, direction {direction}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start jog on {axis} axis: {e}")
            return False

    def stop_jog(self, axis: str) -> bool:
        """
        Stop continuous jog movement on the specified axis using LinuxCNC.
        Args:
            axis: 'x' or 'y'
        Returns:
            True if jog stop command sent successfully, False otherwise
        Note:
            Uses joint jog mode (jjogmode=True, teleop_enable(0)).
        """
        if axis not in ['x', 'y']:
            self.logger.error(f"Invalid axis: {axis}")
            return False
        if not self.is_connected():
            self.logger.error("Cannot stop jog - not connected")
            return False
        if self.command is None or self.status is None:
            self.logger.error("LinuxCNC command or status object not available")
            return False
        if linuxcnc is None:
            self.logger.error("linuxcnc Python module not available")
            return False
        try:
            axis_index = 0 if axis == 'x' else 1
            self.status.poll()
            # Enable joint jog mode
            self.command.teleop_enable(0)
            # Stop jog (jjogmode=True)
            self.command.jog(linuxcnc.JOG_STOP, True, axis_index)
            self.logger.info(f"Stopped continuous jog on {axis} axis")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop jog on {axis} axis: {e}")
            return False

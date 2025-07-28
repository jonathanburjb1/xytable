"""
Command implementations for the X-Y Table Control System CLI.

This module contains the actual implementations of movement and status commands.
"""

import logging
from typing import Dict, Any, Optional

from src.core.movement import MovementController
from src.hardware.axis_manager import AxisManager
from src.hardware.mesa_driver import MesaDriver


class MovementCommands:
    """Handles movement-related commands for the CLI."""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize hardware components
        try:
            self.axis_manager = AxisManager(config_manager)
            self.movement_controller = MovementController(config_manager, self.axis_manager)
        except Exception as e:
            self.logger.error(f"Failed to initialize movement components: {e}")
            raise
    
    def move_x(self, distance: float, speed: Optional[float] = None) -> None:
        """
        Move X axis by specified distance in inches.
        Args:
            distance: Distance to move (inches)
            speed: Movement speed in inches per second (optional)
        """
        self.logger.info(f"Moving X axis by {distance} inches")
        if speed is None:
            speed = float(self.config.get('movement.default_speed', 1.0))
        else:
            speed = float(speed)
        try:
            self.movement_controller.move_single_axis('x', distance, speed)
            self.logger.info(f"X axis movement completed: {distance} inches")
        except Exception as e:
            self.logger.error(f"X axis movement failed: {e}")
            raise
    
    def move_y(self, distance: float, speed: Optional[float] = None) -> None:
        """
        Move Y axis by specified distance in inches.
        Args:
            distance: Distance to move (inches)
            speed: Movement speed in inches per second (optional)
        """
        self.logger.info(f"Moving Y axis by {distance} inches")
        if speed is None:
            speed = float(self.config.get('movement.default_speed', 1.0))
        else:
            speed = float(speed)
        try:
            self.movement_controller.move_single_axis('y', distance, speed)
            self.logger.info(f"Y axis movement completed: {distance} inches")
        except Exception as e:
            self.logger.error(f"Y axis movement failed: {e}")
            raise
    
    def move_xy(self, x_distance: float, y_distance: float, speed: Optional[float] = None) -> None:
        """
        Move both X and Y axes simultaneously by specified distances in inches.
        Args:
            x_distance: Distance to move X axis (inches)
            y_distance: Distance to move Y axis (inches)
            speed: Movement speed in inches per second (optional)
        """
        self.logger.info(f"Moving X axis by {x_distance} inches, Y axis by {y_distance} inches")
        if speed is None:
            speed = float(self.config.get('movement.default_speed', 1.0))
        else:
            speed = float(speed)
        try:
            self.movement_controller.move_coordinated(x_distance, y_distance, speed)
            self.logger.info(f"Coordinated movement completed: X={x_distance}, Y={y_distance} inches")
        except Exception as e:
            self.logger.error(f"Coordinated movement failed: {e}")
            raise
    
    def home_all(self) -> None:
        """Home both axes to their reference positions."""
        self.logger.info("Starting homing sequence for both axes")
        
        try:
            homing_speed = self.config.get('movement.homing_speed', 200)
            self.movement_controller.home_axes(homing_speed)
            self.logger.info("Homing sequence completed successfully")
        except Exception as e:
            self.logger.error(f"Homing sequence failed: {e}")
            raise
    
    def home_axis(self, axis: str) -> None:
        """
        Home a specific axis to its reference position.
        
        Args:
            axis: Axis to home ('x' or 'y')
        """
        if axis not in ['x', 'y']:
            raise ValueError(f"Invalid axis: {axis}. Must be 'x' or 'y'")
        
        self.logger.info(f"Starting homing sequence for {axis} axis")
        
        try:
            # Use Mesa driver directly for homing
            mesa_driver = MesaDriver(self.config)
            if not mesa_driver.connect():
                raise RuntimeError("Failed to connect to Mesa board")
            
            try:
                if not mesa_driver.home_axis(axis):
                    raise RuntimeError(f"Failed to home {axis} axis")
                
                self.logger.info(f"{axis} axis homing command sent successfully")
                
                # Wait for homing to complete (this would need to be implemented based on your setup)
                # For now, we just report that the command was sent
                
            finally:
                mesa_driver.disconnect()
                
        except Exception as e:
            self.logger.error(f"Homing sequence for {axis} axis failed: {e}")
            raise
    
    def emergency_stop(self) -> None:
        """Emergency stop - halt all movement immediately."""
        self.logger.warning("Emergency stop activated")
        
        try:
            self.movement_controller.emergency_stop()
            self.logger.info("Emergency stop completed")
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")
            raise
    
    def move_absolute(self, x: float = 0.0, y: float = 0.0) -> None:
        """
        Move to an absolute X/Y position in inches using MesaDriver (MDI G0).
        Args:
            x: Absolute X position in inches
            y: Absolute Y position in inches
        """
        self.logger.info(f"Moving to absolute position X={x}, Y={y} (inches)")
        mesa_driver = MesaDriver(self.config)
        if not mesa_driver.connect():
            raise RuntimeError("Failed to connect to Mesa board")
        try:
            if not mesa_driver.move_absolute(x, y):
                raise RuntimeError(f"MesaDriver failed to move to absolute position X={x}, Y={y}")
            self.logger.info(f"Absolute move to X={x}, Y={y} completed")
        finally:
            mesa_driver.disconnect()
    
    def set_io(self, io_channel: int, state: bool) -> None:
        """
        Set the state of the flood (1) or mist (0) output using MesaDriver.
        Args:
            io_channel: 1 for flood, 0 for mist
            state: True to turn on, False to turn off
        """
        self.logger.info(f"Setting IO channel {io_channel} to {'ON' if state else 'OFF'} (1=flood, 0=mist)")
        mesa_driver = MesaDriver(self.config)
        if not mesa_driver.connect():
            raise RuntimeError("Failed to connect to Mesa board")
        try:
            if not mesa_driver.set_io(io_channel, state):
                raise RuntimeError(f"MesaDriver failed to set IO channel {io_channel} to {state}")
            self.logger.info(f"IO channel {io_channel} set to {state}")
        finally:
            mesa_driver.disconnect()


class StatusCommands:
    """Handles status-related commands for the CLI."""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize hardware components
        try:
            self.axis_manager = AxisManager(config_manager)
        except Exception as e:
            self.logger.error(f"Failed to initialize status components: {e}")
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status and position of both axes.
        
        Returns:
            Dictionary containing status information for X axis, Y axis, and system
        """
        self.logger.debug("Getting system status")
        
        try:
            # Get axis status
            x_status = self.axis_manager.get_axis_status('x')
            y_status = self.axis_manager.get_axis_status('y')
            
            # Get system status
            system_status = self.axis_manager.get_system_status()
            
            status_info = {
                'x_axis': {
                    'position': x_status.get('position', 'Unknown'),
                    'status': x_status.get('status', 'Unknown'),
                    'enabled': x_status.get('enabled', False),
                    'in_position': x_status.get('in_position', False)
                },
                'y_axis': {
                    'position': y_status.get('position', 'Unknown'),
                    'status': y_status.get('status', 'Unknown'),
                    'enabled': y_status.get('enabled', False),
                    'in_position': y_status.get('in_position', False)
                },
                'system': {
                    'connected': system_status.get('connected', False),
                    'emergency_stop': system_status.get('emergency_stop', False),
                    'limit_switches': system_status.get('limit_switches', {}),
                    'error_state': system_status.get('error_state', False)
                }
            }
            
            self.logger.debug("Status retrieved successfully")
            return status_info
            
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            # Return basic status with error information
            return {
                'x_axis': {'position': 'Error', 'status': 'Error', 'enabled': False, 'in_position': False},
                'y_axis': {'position': 'Error', 'status': 'Error', 'enabled': False, 'in_position': False},
                'system': {'connected': False, 'emergency_stop': False, 'limit_switches': {}, 'error_state': True}
            }


class MesaTestCommands:
    """Handles Mesa driver testing commands for the CLI."""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize Mesa driver with config manager
        self.mesa_driver = MesaDriver(config_manager)
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test Mesa board connection.
        
        Returns:
            Dictionary with connection test results
        """
        self.logger.info("Testing Mesa board connection")
        
        try:
            # Try to connect
            connected = self.mesa_driver.connect()
            
            if connected:
                # Try to read status
                status = self.mesa_driver.read_status()
                self.mesa_driver.disconnect()
                
                return {
                    'success': True,
                    'connected': True,
                    'status_response': status,
                    'message': 'Mesa board connection successful'
                }
            else:
                return {
                    'success': False,
                    'connected': False,
                    'message': 'Failed to connect to Mesa board'
                }
                
        except Exception as e:
            self.logger.error(f"Mesa connection test failed: {e}")
            return {
                'success': False,
                'connected': False,
                'error': str(e),
                'message': f'Connection test failed: {e}'
            }
    
    def test_axis_control(self, axis: str) -> Dict[str, Any]:
        """
        Test axis enable/disable functionality.
        
        Args:
            axis: 'x' or 'y'
            
        Returns:
            Dictionary with test results
        """
        self.logger.info(f"Testing {axis} axis control")
        
        if axis not in ['x', 'y']:
            return {
                'success': False,
                'message': f'Invalid axis: {axis}'
            }
        
        try:
            # Connect to Mesa board
            if not self.mesa_driver.connect():
                return {
                    'success': False,
                    'message': 'Failed to connect to Mesa board'
                }
            
            # Test disable
            disable_result = self.mesa_driver.disable_axis(axis)
            
            self.mesa_driver.disconnect()
            
            return {
                'success': disable_result,
                'disable_result': disable_result,
                'message': f'{axis} axis control test completed'
            }
            
        except Exception as e:
            self.logger.error(f"Axis control test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Axis control test failed: {e}'
            }
    
    def test_movement(self, axis: str, steps: int, speed: int) -> Dict[str, Any]:
        """
        Test movement command functionality.
        
        Args:
            axis: 'x' or 'y'
            steps: Number of steps to move
            speed: Movement speed
            
        Returns:
            Dictionary with test results
        """
        self.logger.info(f"Testing {axis} axis movement: {steps} steps at {speed} steps/sec")
        
        if axis not in ['x', 'y']:
            return {
                'success': False,
                'message': f'Invalid axis: {axis}'
            }
        
        try:
            # Connect to Mesa board
            if not self.mesa_driver.connect():
                return {
                    'success': False,
                    'message': 'Failed to connect to Mesa board'
                }
            
            # Send movement command
            move_result = self.mesa_driver.move_axis(axis, steps, speed)
            
            self.mesa_driver.disconnect()
            
            return {
                'success': move_result,
                'message': f'{axis} axis movement test completed'
            }
            
        except Exception as e:
            self.logger.error(f"Movement test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Movement test failed: {e}'
            }

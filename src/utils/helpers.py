"""
Helper utilities for the X-Y Table Control System.

Common utility functions used across the project.
"""

import time
from typing import Tuple, Optional


def validate_ip_address(ip_address: str) -> bool:
    """
    Validate an IP address format.
    
    Args:
        ip_address: IP address string to validate
        
    Returns:
        True if valid IP address, False otherwise
    """
    try:
        parts = ip_address.split('.')
        if len(parts) != 4:
            return False
        
        for part in parts:
            if not part.isdigit():
                return False
            num = int(part)
            if num < 0 or num > 255:
                return False
        
        return True
    except (ValueError, AttributeError):
        return False


def validate_port(port: int) -> bool:
    """
    Validate a port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if valid port number, False otherwise
    """
    return isinstance(port, int) and 1 <= port <= 65535


def calculate_movement_time(steps: int, speed: int) -> float:
    """
    Calculate movement time based on steps and speed.
    
    Args:
        steps: Number of steps to move
        speed: Movement speed in steps per second
        
    Returns:
        Movement time in seconds
    """
    if speed <= 0:
        raise ValueError("Speed must be positive")
    
    return abs(steps) / speed


def calculate_coordinated_movement_time(x_steps: int, y_steps: int, speed: int) -> float:
    """
    Calculate coordinated movement time for both axes.
    
    Args:
        x_steps: X axis steps
        y_steps: Y axis steps
        speed: Movement speed in steps per second
        
    Returns:
        Movement time in seconds (uses the longer axis)
    """
    x_time = calculate_movement_time(x_steps, speed)
    y_time = calculate_movement_time(y_steps, speed)
    return max(x_time, y_time)


def steps_to_distance(steps: int, steps_per_revolution: int, lead_screw_pitch: float) -> float:
    """
    Convert steps to linear distance.
    
    Args:
        steps: Number of steps
        steps_per_revolution: Steps per motor revolution
        lead_screw_pitch: Lead screw pitch in mm per revolution
        
    Returns:
        Distance in mm
    """
    if steps_per_revolution <= 0:
        raise ValueError("Steps per revolution must be positive")
    
    revolutions = steps / steps_per_revolution
    distance = revolutions * lead_screw_pitch
    return distance


def distance_to_steps(distance: float, steps_per_revolution: int, lead_screw_pitch: float) -> int:
    """
    Convert linear distance to steps.
    
    Args:
        distance: Distance in mm
        steps_per_revolution: Steps per motor revolution
        lead_screw_pitch: Lead screw pitch in mm per revolution
        
    Returns:
        Number of steps
    """
    if lead_screw_pitch <= 0:
        raise ValueError("Lead screw pitch must be positive")
    
    revolutions = distance / lead_screw_pitch
    steps = int(revolutions * steps_per_revolution)
    return steps


def format_position(position: int, steps_per_revolution: int, lead_screw_pitch: float) -> str:
    """
    Format position as both steps and mm.
    
    Args:
        position: Position in steps
        steps_per_revolution: Steps per motor revolution
        lead_screw_pitch: Lead screw pitch in mm per revolution
        
    Returns:
        Formatted position string
    """
    try:
        distance_mm = steps_to_distance(position, steps_per_revolution, lead_screw_pitch)
        return f"{position} steps ({distance_mm:.3f} mm)"
    except (ValueError, ZeroDivisionError):
        return f"{position} steps"


def format_speed(speed: int, steps_per_revolution: int, lead_screw_pitch: float) -> str:
    """
    Format speed as both steps/sec and mm/sec.
    
    Args:
        speed: Speed in steps per second
        steps_per_revolution: Steps per motor revolution
        lead_screw_pitch: Lead screw pitch in mm per revolution
        
    Returns:
        Formatted speed string
    """
    try:
        speed_mm_per_sec = speed * lead_screw_pitch / steps_per_revolution
        return f"{speed} steps/sec ({speed_mm_per_sec:.2f} mm/sec)"
    except (ValueError, ZeroDivisionError):
        return f"{speed} steps/sec"


def retry_operation(operation, max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry an operation with exponential backoff.
    
    Args:
        operation: Function to retry
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff: Backoff multiplier
        
    Returns:
        Result of the operation
        
    Raises:
        Exception: Last exception if all attempts fail
    """
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return operation()
        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                time.sleep(delay * (backoff ** attempt))
    
    if last_exception is not None:
        raise last_exception
    else:
        raise RuntimeError("Operation failed after all attempts")


def clamp(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp a value between minimum and maximum bounds.
    
    Args:
        value: Value to clamp
        min_val: Minimum bound
        max_val: Maximum bound
        
    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


def is_within_bounds(value: float, min_val: float, max_val: float) -> bool:
    """
    Check if a value is within bounds.
    
    Args:
        value: Value to check
        min_val: Minimum bound
        max_val: Maximum bound
        
    Returns:
        True if value is within bounds, False otherwise
    """
    return min_val <= value <= max_val

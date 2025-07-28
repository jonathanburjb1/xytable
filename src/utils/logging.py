"""
Logging configuration for the X-Y Table Control System.

Provides centralized logging setup and configuration.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logging(level: str = 'INFO', log_file: Optional[str] = None) -> None:
    """
    Setup logging configuration for the X-Y table system.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        
        # Create log directory if it doesn't exist
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use RotatingFileHandler for log rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('src.hardware').setLevel(logging.DEBUG)
    logging.getLogger('src.core').setLevel(logging.DEBUG)
    logging.getLogger('src.cli').setLevel(logging.INFO)
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_hardware_event(logger: logging.Logger, event: str, details: dict = None) -> None:
    """
    Log hardware-related events with consistent formatting.
    
    Args:
        logger: Logger instance
        event: Event description
        details: Additional details dictionary
    """
    if details:
        logger.info(f"HARDWARE EVENT: {event} - {details}")
    else:
        logger.info(f"HARDWARE EVENT: {event}")


def log_movement_event(logger: logging.Logger, axis: str, action: str, distance: float, speed: float = None) -> None:
    """
    Log movement events with consistent formatting (in inches).
    Args:
        logger: Logger instance
        axis: Axis name ('x', 'y', or 'xy')
        action: Action description
        distance: Distance in inches
        speed: Movement speed in inches/sec (optional)
    """
    if speed is not None:
        logger.info(f"MOVEMENT: {axis.upper()} axis {action} - {distance:.4f} inches at {speed:.4f} inches/sec")
    else:
        logger.info(f"MOVEMENT: {axis.upper()} axis {action} - {distance:.4f} inches")


def log_safety_event(logger: logging.Logger, event: str, severity: str = 'WARNING') -> None:
    """
    Log safety-related events with consistent formatting.
    
    Args:
        logger: Logger instance
        event: Safety event description
        severity: Event severity ('INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    log_method = getattr(logger, severity.lower(), logger.warning)
    log_method(f"SAFETY EVENT: {event}")

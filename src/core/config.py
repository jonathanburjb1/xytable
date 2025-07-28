"""
Configuration management for the X-Y Table Control System.

Handles loading, validation, and access to configuration settings.
"""

import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages configuration loading and access for the X-Y table system."""
    
    def __init__(self, config_path: str):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(config_path)
        self._config = {}
        
        self._load_config()
        self._validate_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(self.config_path, 'r') as file:
                self._config = yaml.safe_load(file)
            
            self.logger.info(f"Configuration loaded from {self.config_path}")
            
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise
    
    def _validate_config(self) -> None:
        """Validate the loaded configuration."""
        required_sections = ['mesa', 'table', 'movement', 'logging']
        
        for section in required_sections:
            if section not in self._config:
                self.logger.warning(f"Missing configuration section: {section}")
        
        # Validate Mesa configuration
        if 'mesa' in self._config:
            mesa = self._config['mesa']
            required_mesa_fields = ['ip', 'port', 'timeout']
            for field in required_mesa_fields:
                if field not in mesa:
                    self.logger.warning(f"Missing Mesa configuration field: {field}")
        
        # Validate table configuration
        if 'table' in self._config:
            table = self._config['table']
            for axis in ['x_axis', 'y_axis']:
                if axis not in table:
                    self.logger.warning(f"Missing {axis} configuration")
                else:
                    axis_config = table[axis]
                    required_axis_fields = ['max_travel', 'min_position', 'max_position', 'default_speed', 'max_speed']
                    for field in required_axis_fields:
                        if field not in axis_config:
                            self.logger.warning(f"Missing {field} configuration for {axis}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'mesa.ip')
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_mesa_config(self) -> Dict[str, Any]:
        """Get Mesa board configuration."""
        mesa_config = self._config.get('mesa', {})
        # Convert new structure to old structure for backward compatibility
        return {
            'ip_address': mesa_config.get('ip'),
            'port': mesa_config.get('port'),
            'timeout': mesa_config.get('timeout')
        }
    
    def get_table_config(self) -> Dict[str, Any]:
        """Get table configuration section."""
        return self._config.get('table', {})
    
    def get_axis_config(self, axis: str) -> Dict[str, Any]:
        """
        Get configuration for a specific axis.
        
        Args:
            axis: Axis name ('x' or 'y')
            
        Returns:
            Axis configuration dictionary
        """
        axis_key = f"{axis}_axis"
        return self._config.get('table', {}).get(axis_key, {})
    
    def get_movement_config(self) -> Dict[str, Any]:
        """Get movement configuration."""
        return self._config.get('movement', {})
    
    def get_network_config(self) -> Dict[str, Any]:
        """Get network configuration."""
        return self._config.get('network', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self._config.get('logging', {})
    
    # Backward compatibility methods
    def get_hardware_config(self) -> Dict[str, Any]:
        """Get hardware configuration section (backward compatibility)."""
        return {
            'mesa_board': self.get_mesa_config(),
            'x_axis': self.get_axis_config('x'),
            'y_axis': self.get_axis_config('y')
        }
    
    def get_safety_config(self) -> Dict[str, Any]:
        """Get safety configuration (backward compatibility)."""
        return {
            'emergency_stop_enabled': True,
            'limit_switches_enabled': True,
            'soft_limits_enabled': True,
            'max_velocity': 2000
        }
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self.logger.info("Reloading configuration")
        self._load_config()
        self._validate_config()
    
    def get_all(self) -> Dict[str, Any]:
        """Get the complete configuration dictionary."""
        return self._config.copy()

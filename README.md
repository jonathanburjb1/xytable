# X-Y Table Control System

A Python-based control system for X-Y tables using Mesa 7I96S boards and servo motors, designed to work with LinuxCNC's HAL (Hardware Abstraction Layer).

## Features

- **Dual-axis control**: Independent X and Y axis movement
- **Step-based movement**: Precise control with configurable step sizes
- **Command-line interface**: Easy-to-use CLI for movement commands
- **Safety features**: Limit switch support and emergency stop functionality
- **Configuration management**: YAML-based configuration system
- **Logging**: Comprehensive logging for debugging and operation tracking

## Hardware Requirements

- Mesa 7I96S board
- Two servo motors (X and Y axes)
- Raspberry Pi (networked with Mesa board)
- Limit switches (optional but recommended)
- Emergency stop button (optional but recommended)

## Installation

### Prerequisites

1. **LinuxCNC**: Install LinuxCNC on your Raspberry Pi
2. **Python 3.8+**: Ensure Python 3.8 or higher is installed
3. **HAL Python Bindings**: Install LinuxCNC's Python HAL bindings

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd xytable
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the system:
   ```bash
   cp config/settings.yaml.example config/settings.yaml
   # Edit config/settings.yaml with your hardware settings
   ```

## Usage

### Basic Movement Commands

Move X axis by 100 steps:
```bash
python3 -m src.cli.main move x 100
```

Move Y axis by -50 steps (use -- to handle negative numbers):
```bash
python3 -m src.cli.main move y -- -50
```

Move both axes simultaneously:
```bash
python3 -m src.cli.main move xy 100 200
```

### Movement with Custom Speed

Move X axis with custom speed (options must come before arguments):
```bash
python3 -m src.cli.main move x --speed 800 100
```

Move Y axis backward with custom speed:
```bash
python3 -m src.cli.main move y --speed 600 -- -75
```

### Status and Information

Check current position:
```bash
python3 -m src.cli.main status
```

Get help:
```bash
python3 -m src.cli.main --help
```

## Configuration

The system uses YAML configuration files located in the `config/` directory. Key settings include:

- **Motor parameters**: Steps per revolution, maximum speed
- **Axis limits**: Travel limits and soft limits
- **Hardware settings**: Mesa board configuration
- **Safety settings**: Emergency stop and limit switch configuration

## Development

### Project Structure

```
xytable/
├── src/
│   ├── hardware/          # Hardware interface layer
│   ├── cli/              # Command-line interface
│   ├── core/             # Core business logic
│   └── utils/            # Utility functions
├── tests/                # Test suite
├── config/               # Configuration files
└── docs/                 # Documentation
```

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/ tests/
flake8 src/ tests/
```

## Safety Considerations

- Always ensure the work area is clear before movement
- Test movements at low speeds first
- Keep emergency stop accessible
- Verify limit switch functionality regularly
- Monitor for unusual sounds or behavior

## Troubleshooting

### Common Issues

1. **HAL connection failed**: Check LinuxCNC installation and HAL Python bindings
2. **Motor not responding**: Verify Mesa board connection and power
3. **Position drift**: Check encoder feedback and calibration

### Logging

Logs are written to `logs/` directory. Check these files for detailed error information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions, please open an issue on the project repository.

# Web Development Setup

This document describes the web development setup for the X-Y Table Control System, including the FastAPI backend and React frontend.

## Overview

The web interface consists of:
- **FastAPI Backend**: REST API for controlling the X-Y table
- **React Frontend**: Modern web interface with three main modes:
  - **Manual Control**: Direct movement and axis control
  - **Program Builder**: Create and execute movement programs
  - **Visual Control**: Interactive X-Y table visualization

## Architecture

```
┌─────────────────┐    HTTP/JSON    ┌─────────────────┐
│   React App     │ ──────────────► │   FastAPI       │
│   (Port 3000)   │                 │   (Port 8000)   │
│                 │                 │                 │
│ ┌─────────────┐ │                 │                 │
│ │Manual Control│ │                 │                 │
│ └─────────────┘ │                 │                 │
│ ┌─────────────┐ │                 │                 │
│ │Program Builder│ │                 │                 │
│ └─────────────┘ │                 │                 │
│ ┌─────────────┐ │                 │                 │
│ │Visual Control│ │                 │                 │
│ └─────────────┘ │                 │                 │
└─────────────────┘                 └─────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │   X-Y Table     │
                                    │   Control       │
                                    │   System        │
                                    └─────────────────┘
```

## Quick Start

### Option 1: Automated Startup (Recommended)

Use the provided script to start both servers:

```bash
./scripts/start_web.sh
```

This script will:
- Install dependencies if needed
- Start the FastAPI backend on port 8000
- Start the React frontend on port 3000
- Provide status information

### Option 2: Manual Startup

#### Backend (FastAPI)

```bash
cd webapi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend (React)

```bash
cd frontend
npm install --legacy-peer-deps
npm start
```

## Frontend Features

### 1. Manual Control Tab
- **Status Display**: Real-time connection status and system messages
- **Movement Controls**: Axis selection, distance input, speed control
- **Quick Movement**: Predefined movement buttons (+/- 10mm)
- **Axis Management**: Enable/disable individual axes
- **Emergency Stop**: Large, prominent emergency stop button

### 2. Program Builder Tab
- **Command Creation**: Add movement commands with parameters
- **Program List**: Visual list of all commands in the program
- **Command Management**: Reorder, remove, and edit commands
- **Program Execution**: Execute entire programs sequentially
- **Save/Load**: Save programs to localStorage and load them later
- **Features**:
  - Move commands (X/Y axis, distance, speed)
  - Wait commands (delay in seconds)
  - Command reordering (up/down arrows)
  - Program validation and error handling

### 3. Visual Control Tab
- **Interactive Canvas**: Click to set X-Y table position
- **Real-time Visualization**: See current position and hover coordinates
- **Grid System**: Configurable grid with coordinate labels
- **Position Tracking**: Real-time position updates
- **Features**:
  - Click anywhere to move to that position
  - Drag to continuously update position
  - Visual feedback with blue dot (current) and green circle (hover)
  - Coordinate display in millimeters
  - Configurable table dimensions and grid size

## API Endpoints

The FastAPI backend provides the following endpoints:

### Status
- `GET /` - API health check
- `GET /status` - System status (TODO: integrate with Mesa driver)

### Movement Control
- `POST /move` - Move axis by specified distance
  ```json
  {
    "axis": "x",
    "distance": 10.5,
    "speed": 100
  }
  ```

### Axis Control
- `POST /enable_axis` - Enable specified axis
  ```json
  {
    "axis": "x"
  }
  ```
- `POST /disable_axis` - Disable specified axis
  ```json
  {
    "axis": "x"
  }
  ```

### Emergency Control
- `POST /emergency_stop` - Emergency stop all movement

## Component Architecture

### Program Builder Component
- **Location**: `frontend/src/components/ProgramBuilder.js`
- **Features**:
  - State management for program commands
  - Form validation and error handling
  - Local storage for program persistence
  - Real-time command execution
  - Responsive design for mobile devices

### XY Visualizer Component
- **Location**: `frontend/src/components/XYVisualizer.js`
- **Features**:
  - HTML5 Canvas for drawing
  - Mouse event handling for position selection
  - Coordinate conversion (canvas ↔ table coordinates)
  - Real-time position updates
  - Configurable grid and dimensions

## Development

### Backend Development

The FastAPI backend is located in `webapi/`:

```
webapi/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
└── venv/               # Virtual environment (created automatically)
```

Key features:
- CORS enabled for frontend communication
- Pydantic models for request validation
- Automatic API documentation at `/docs`
- Hot reload during development

### Frontend Development

The React frontend is located in `frontend/`:

```
frontend/
├── src/
│   ├── App.js              # Main application component
│   ├── App.css             # Main styling
│   ├── components/
│   │   ├── ProgramBuilder.js    # Program creation component
│   │   ├── ProgramBuilder.css   # Program builder styling
│   │   ├── XYVisualizer.js      # Visual control component
│   │   └── XYVisualizer.css     # Visualizer styling
│   └── index.js            # Application entry point
├── package.json           # Node.js dependencies
└── public/               # Static assets
```

Key features:
- Modern React with hooks
- Tab-based navigation
- Component-based architecture
- Responsive design
- Real-time status updates
- Professional UI/UX

## Configuration

### API Base URL

The frontend connects to the backend via the `API_BASE_URL` constant in `frontend/src/App.js`. By default, it's set to:

```javascript
const API_BASE_URL = 'http://localhost:8000';
```

### CORS Settings

The backend allows CORS from any origin during development. For production, update the CORS settings in `webapi/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Table Dimensions

The XY Visualizer uses configurable table dimensions. Default settings:

```javascript
tableDimensions={{ width: 200, height: 200 }}  // mm
gridSize={10}                                   // mm
```

## Usage Examples

### Creating a Movement Program

1. Navigate to the "Program Builder" tab
2. Select "Move" command type
3. Choose axis (X or Y)
4. Enter distance and speed
5. Add optional delay
6. Click "Add Command"
7. Repeat for additional commands
8. Click "Execute Program" to run

### Using Visual Control

1. Navigate to the "Visual Control" tab
2. Click anywhere on the grid to move to that position
3. Drag to continuously update position
4. Monitor current position in the info panel
5. Use hover feedback to preview positions

### Saving and Loading Programs

1. In Program Builder, create your program
2. Click "Save" and enter a program name
3. Programs are stored in browser localStorage
4. Click "Load" to see available programs
5. Select a program name to load it

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   lsof -i :8000
   lsof -i :3000
   
   # Kill the process
   kill -9 <PID>
   ```

2. **Dependencies Not Installed**
   ```bash
   # Backend
   cd webapi
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Frontend
   cd frontend
   npm install --legacy-peer-deps
   ```

3. **React Build Errors**
   - Use `--legacy-peer-deps` flag for npm install
   - Check Node.js version compatibility

4. **API Connection Issues**
   - Verify backend is running on port 8000
   - Check firewall settings
   - Ensure CORS is properly configured

5. **Canvas Not Rendering**
   - Check browser console for JavaScript errors
   - Ensure canvas element is properly mounted
   - Verify mouse event handlers are working

### Logs

- **Backend logs**: Check terminal where uvicorn is running
- **Frontend logs**: Check browser console (F12)
- **Network logs**: Check browser Network tab for API calls

## Next Steps

### Integration with Mesa Driver

The current API endpoints return placeholder responses. To integrate with the actual X-Y table:

1. Import the Mesa driver in `webapi/main.py`
2. Replace placeholder responses with actual driver calls
3. Add error handling for hardware communication
4. Implement proper status reporting
5. Add real-time position feedback

### Production Deployment

For production deployment:

1. Build the React app: `npm run build`
2. Serve static files from FastAPI
3. Configure proper CORS settings
4. Set up reverse proxy (nginx)
5. Use production WSGI server (gunicorn)

### Additional Features

Potential enhancements:
- **Real-time position tracking** from hardware
- **Movement history** and logging
- **Configuration management** for table settings
- **User authentication** and access control
- **Advanced program features** (loops, conditions)
- **Path visualization** in the visualizer
- **G-code import/export** for programs
- **Multi-table support** for complex setups 
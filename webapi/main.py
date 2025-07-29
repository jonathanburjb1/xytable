import sys
import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import asyncio
import json

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


from src.core.movement import MovementController
from src.core.config import ConfigManager

# Configure logging
# Ensure logs directory exists
os.makedirs('./logs', exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        #logging.StreamHandler(),  # Log to console
        logging.FileHandler('./logs/backend.log')  # Log to file
    ]
)

# After logging.basicConfig(...)


logger = logging.getLogger(__name__)

app = FastAPI(title="XY Table Control API", version="0.1.0")

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
movement_controller: Optional[MovementController] = None

config_manager: Optional[ConfigManager] = None
is_connected = False

# Program storage
PROGRAMS_DIR = Path("./programs")
PROGRAMS_DIR.mkdir(exist_ok=True)

# --- Models ---
class MoveRequest(BaseModel):
    axis: str
    distance: float
    speed: Optional[float] = None

    @validator('axis')
    def validate_axis(cls, v):
        if v not in ['x', 'y']:
            raise ValueError('Axis must be "x" or "y"')
        return v

    @validator('distance')
    def validate_distance(cls, v):
        if abs(v) > 10:  # Reasonable limit in inches
            raise ValueError('Distance too large (max 10 inches)')
        return v

    @validator('speed')
    def validate_speed(cls, v):
        if v is not None and (v <= 0 or v > 10):  # Speed in inches/sec
            raise ValueError('Speed must be between 0 and 20 inches/sec')
        return v



class PositionRequest(BaseModel):
    x: float
    y: float
    speed: Optional[float] = None

    @validator('x', 'y')
    def validate_position(cls, v):
        if v < 0 or v > 10:  # Position in inches
            raise ValueError('Position out of range (0-10 inches)')
        return v

class ProgramCommand(BaseModel):
    id: Optional[str] = None
    step: int
    type: str
    axis: Optional[str] = None
    distance: Optional[float] = None
    speed: Optional[float] = None
    delay: Optional[float] = None
    position: Optional[float] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    loop_count: Optional[int] = None
    message_text: Optional[str] = None

    class Config:
        extra = "allow"  # Allow extra fields for flexibility

class Program(BaseModel):
    name: str
    program: list[ProgramCommand]
    created: Optional[str] = None
    modified: Optional[str] = None
    description: Optional[str] = None

class ProgramListResponse(BaseModel):
    programs: list[dict]
    total: int

# --- Startup and Shutdown Events ---
@app.on_event("startup")
async def startup_event():
    global movement_controller, config_manager, is_connected
    
    try:
        # Load configuration
        config_path = project_root / "config" / "settings.yaml"
        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            return
        
        config_manager = ConfigManager(str(config_path))
        logger.info("Configuration loaded successfully")
        
        # Initialize MovementController
        movement_controller = MovementController(config_manager)
        
        # Try to connect
        try:
            if movement_controller.mesa_driver.connect():
                is_connected = True
                logger.info("Connected to Mesa board successfully")
            else:
                is_connected = False
                logger.warning("Could not connect to Mesa board")
        except Exception as e:
            logger.warning(f"Could not connect to Mesa board: {e}")
            is_connected = False
            
    except Exception as e:
        logger.error(f"Error during startup: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    global movement_controller, is_connected
    
    if movement_controller and is_connected:
        try:
            movement_controller.mesa_driver.disconnect()
            logger.info("Disconnected from Mesa board")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# --- Helper Functions ---
def validate_position(axis: str, position: float) -> bool:
    """Validate position against table limits (in inches)"""
    if not config_manager:
        return False
    
    if axis == 'x':
        max_pos = config_manager.get('table.x_axis.max_position', 4.25)  # 4.25 inches
        return 0 <= position <= max_pos
    elif axis == 'y':
        max_pos = config_manager.get('table.y_axis.max_position', 3.125)  # 3.125 inches
        return 0 <= position <= max_pos
    return False

def get_axis_limits(axis: str) -> Dict[str, float]:
    """Get axis limits from configuration (in inches)"""
    if not config_manager:
        return {}
    
    if axis == 'x':
        return {
            'min': config_manager.get('table.x_axis.min_position', 0.0),
            'max': config_manager.get('table.x_axis.max_position', 4.25),  # 4.25 inches
            'max_speed': config_manager.get('table.x_axis.max_speed', 10.0)  # 10 in/s
        }
    elif axis == 'y':
        return {
            'min': config_manager.get('table.y_axis.min_position', 0.0),
            'max': config_manager.get('table.y_axis.max_position', 3.125),  # 3.125 inches
            'max_speed': config_manager.get('table.y_axis.max_speed', 10.0)  # 10 in/s
        }
    return {}

async def move_to_position(target_x: float, target_y: float, speed: Optional[float] = None):
    """Move to absolute position"""
    
    if not is_connected or not movement_controller:
        raise HTTPException(status_code=503, detail="Mesa board not connected")
    
    # Validate positions
    if not validate_position('x', target_x):
        raise HTTPException(status_code=400, detail=f"X position {target_x} out of range")
    if not validate_position('y', target_y):
        raise HTTPException(status_code=400, detail=f"Y position {target_y} out of range")
    
    # Use default speed if not specified
    if speed is None:
        speed = config_manager.get('movement.default_speed', 10.0) if config_manager else 10.0
    
    # Ensure speed is a float
    speed = float(speed)
    
    # Get current position from hardware
    current_pos = get_current_position()
    
    # Calculate movements
    delta_x = target_x - current_pos['x']
    delta_y = target_y - current_pos['y']
    
    # Move X axis if needed
    tolerance = config_manager.get('movement.position_tolerance', 0.1) if config_manager else 0.1
    if abs(delta_x) > tolerance or abs(delta_y) > tolerance:
        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, movement_controller.move_absolute, target_x, target_y, speed),
                timeout=15.0
            )
        except asyncio.TimeoutError:
            logger.error(f"Movement timeout for move_to_position")
            raise HTTPException(status_code=408, detail=f"Movement timeout - operation took too long")
        except Exception as e:
            logger.error(f"Error moving to position: {e}")
            raise HTTPException(status_code=500, detail=f"Movement failed: {e}")

def get_current_position() -> Dict[str, float]:
    """Get current position from MovementController"""
    if not is_connected or not movement_controller:
        return {"x": 0.0, "y": 0.0}
    
    try:
        mesa_status = movement_controller.mesa_driver.read_status()
        if mesa_status.get('connected') and 'x_axis' in mesa_status and 'y_axis' in mesa_status:
            return {
                "x": mesa_status['x_axis'].get('position', 0.0),
                "y": mesa_status['y_axis'].get('position', 0.0)
            }
    except Exception as e:
        logger.error(f"Error getting current position: {e}")
    
    return {"x": 0.0, "y": 0.0}

# --- Endpoints ---
@app.get("/")
def read_root():
    return {
        "message": "XY Table Control API is running!",
        "version": "0.1.0",
        "connected": is_connected
    }

@app.get("/status")
async def get_status():
    """Get system status and current position"""
    global is_connected
    
    try:

        status_data = {
            "status": "ok" if is_connected else "error",
            "connected": is_connected,
            "emergency_stop": movement_controller.get_emergency_stop_status() if movement_controller else False,
            "current_position": get_current_position(),
            "table_limits": {
                "x_axis": get_axis_limits('x'),
                "y_axis": get_axis_limits('y')
            }
        }
        
        is_connected = movement_controller.mesa_driver.is_connected() if movement_controller else False
        if not is_connected:
            movement_controller.mesa_driver.connect()
            is_connected = movement_controller.mesa_driver.is_connected() if movement_controller else False

        if is_connected and movement_controller:
            try:
                # Try to get actual status from Mesa board
                mesa_status = movement_controller.mesa_driver.read_status()
                status_data["mesa_status"] = mesa_status
            except Exception as e:
                logger.warning(f"Could not read Mesa status: {e}")
                status_data["mesa_status"] = "unavailable"
        
        return status_data
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=f"Status error: {e}")

@app.post("/move")
async def move_axis(req: MoveRequest):
    """Move axis by relative distance"""
    print(f"Move request received: axis={req.axis}, distance={req.distance}, speed={req.speed}")
    logger.info(f"Move request received: axis={req.axis}, distance={req.distance}, speed={req.speed}")
    
    if not is_connected or not movement_controller:
        logger.error("Move request failed: Mesa board not connected")
        raise HTTPException(status_code=503, detail="Mesa board not connected")
    
    try:
        # Get current position from hardware
        current_pos = get_current_position()
        logger.debug(f"Current position: {current_pos}")
        
        # Calculate new position
        new_position = current_pos[req.axis] + req.distance
        logger.debug(f"Calculated new position for {req.axis}: {new_position}")
        
        # Validate new position
        if not validate_position(req.axis, new_position):
            limits = get_axis_limits(req.axis)
            logger.warning(f"Move validation failed: {req.axis} axis would exceed limits {limits}")
            raise HTTPException(
                status_code=400, 
                detail=f"Movement would exceed {req.axis.upper()} axis limits ({limits['min']} to {limits['max']} inches)"
            )
        
        # Use default speed if not specified
        if req.speed is None:
            speed = config_manager.get('movement.default_speed', 10.0) if config_manager else 10.0
            logger.debug(f"Using default speed: {speed}")
        else:
            speed = req.speed
            logger.debug(f"Using requested speed: {speed}")
        
        # Ensure speed is a float
        speed = float(speed)
        
        logger.info(f"Executing movement: {req.axis} axis, distance={req.distance}, speed={speed}")
        
        # Execute movement with timeout
        import asyncio
        try:
            # Run the movement in a thread with timeout
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, movement_controller.move_single_axis, req.axis, req.distance, speed),
                timeout=5.0  # 5 second timeout
            )
            
            updated_position = get_current_position()
            logger.info(f"Movement successful. New position: {updated_position}")
            
            return {
                "status": "ok",
                "message": f"Moved {req.axis.upper()} axis by {req.distance} inches at {speed} inches/s",
                "new_position": updated_position
            }
        except asyncio.TimeoutError:
            logger.error(f"Movement timeout for {req.axis} axis")
            raise HTTPException(status_code=408, detail=f"Movement timeout - operation took too long")
        except Exception as e:
            logger.error(f"Error during movement: {e}")
            raise HTTPException(status_code=500, detail=f"Movement failed: {e}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving {req.axis} axis: {e}")
        raise HTTPException(status_code=500, detail=f"Movement failed: {e}")

@app.post("/move_to")
async def move_to_absolute_position(req: PositionRequest):
    """Move to absolute position"""
    try:
        if not is_connected or not movement_controller:
            raise HTTPException(status_code=503, detail="Mesa board not connected")
        await move_to_position(req.x, req.y, req.speed)
        
        return {
            "status": "ok",
            "message": f"Moved to position ({req.x}, {req.y})",
            "current_position": get_current_position()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving to position: {e}")
        raise HTTPException(status_code=500, detail=f"Movement failed: {e}")

@app.post("/emergency_stop")
async def emergency_stop():
    """Emergency stop all movement"""
    if not is_connected or not movement_controller:
        raise HTTPException(status_code=503, detail="Mesa board not connected")
    
    try:
        movement_controller.emergency_stop()
        return {
            "status": "ok",
            "message": "Emergency stop executed",
            "current_position": get_current_position()
        }
    except Exception as e:
        logger.error(f"Error during emergency stop: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency stop failed: {e}")

@app.post("/clear_emergency_stop")
async def clear_emergency_stop():
    """Clear emergency stop and repower the machine"""
    if not is_connected or not movement_controller:
        raise HTTPException(status_code=503, detail="Mesa board not connected")
    
    try:
        movement_controller.clear_emergency_stop()
        return {
            "status": "ok",
            "message": "Emergency stop cleared and machine repowered",
            "current_position": get_current_position()
        }
    except Exception as e:
        logger.error(f"Error clearing emergency stop: {e}")
        raise HTTPException(status_code=500, detail=f"Clear emergency stop failed: {e}")

@app.get("/limits")
def get_table_limits():
    """Get table limits and configuration"""
    if not config_manager:
        raise HTTPException(status_code=503, detail="Configuration not loaded")
    
    return {
        "x_axis": get_axis_limits('x'),
        "y_axis": get_axis_limits('y'),
        "movement": {
            "default_speed": config_manager.get('movement.default_speed', 10.0),
            "position_tolerance": config_manager.get('movement.position_tolerance', 0.1)
        }
    }

@app.get("/position")
def get_current_position_endpoint():
    """Get current position"""
    return {
        "position": get_current_position(),
        "connected": is_connected
    }

# --- WebSocket Jog Control Endpoint ---
@app.websocket("/ws/jog")
async def websocket_jog(websocket: WebSocket):
    await websocket.accept()
    jog_active = {"x": False, "y": False}
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action")
                axis = msg.get("axis")
                direction = msg.get("direction")
                speed = msg.get("speed")
                if action == "start":
                    if axis in ["x", "y"] and direction in [1, -1] and speed is not None:
                        try:
                            movement_controller.start_jog(axis, direction, float(speed))
                            jog_active[axis] = True
                            await websocket.send_json({"status": "ok", "message": f"Started jog {axis} {direction} at {speed}"})
                        except Exception as e:
                            await websocket.send_json({"status": "error", "message": str(e)})
                    else:
                        await websocket.send_json({"status": "error", "message": "Invalid start jog parameters"})
                elif action == "stop":
                    if axis in ["x", "y"]:
                        try:
                            movement_controller.stop_jog(axis)
                            jog_active[axis] = False
                            await websocket.send_json({"status": "ok", "message": f"Stopped jog {axis}"})
                        except Exception as e:
                            await websocket.send_json({"status": "error", "message": str(e)})
                    else:
                        await websocket.send_json({"status": "error", "message": "Invalid stop jog parameters"})
                else:
                    await websocket.send_json({"status": "error", "message": "Unknown action"})
            except Exception as e:
                await websocket.send_json({"status": "error", "message": f"Malformed message: {e}"})
    except WebSocketDisconnect:
        # On disconnect, stop any active jogs for safety
        for axis in ["x", "y"]:
            if jog_active[axis]:
                try:
                    movement_controller.stop_jog(axis)
                except Exception:
                    pass

# --- Program Storage Endpoints ---

def sanitize_filename(name: str) -> str:
    """Convert program name to safe filename"""
    import re
    # Remove or replace invalid characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Limit length
    return safe_name[:50]

@app.get("/programs")
async def list_programs():
    """List all saved programs"""
    try:
        programs = []
        for file_path in PROGRAMS_DIR.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    program_data = json.load(f)
                    programs.append({
                        "name": program_data.get("name", file_path.stem),
                        "created": program_data.get("created"),
                        "modified": program_data.get("modified"),
                        "description": program_data.get("description", ""),
                        "command_count": len(program_data.get("program", [])),
                        "filename": file_path.name
                    })
            except Exception as e:
                logger.warning(f"Error reading program file {file_path}: {e}")
                continue
        
        # Sort by modified date (newest first)
        programs.sort(key=lambda x: x.get("modified", ""), reverse=True)
        
        return ProgramListResponse(
            programs=programs,
            total=len(programs)
        )
    except Exception as e:
        logger.error(f"Error listing programs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list programs: {e}")

@app.get("/programs/{program_name}")
async def get_program(program_name: str):
    """Get a specific program by name"""
    try:
        safe_name = sanitize_filename(program_name)
        file_path = PROGRAMS_DIR / f"{safe_name}.json"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Program '{program_name}' not found")
        
        with open(file_path, 'r') as f:
            program_data = json.load(f)
        
        return program_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting program {program_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get program: {e}")

@app.post("/programs")
async def save_program(program: Program):
    """Save a new program"""
    try:
        safe_name = sanitize_filename(program.name)
        file_path = PROGRAMS_DIR / f"{safe_name}.json"
        
        # Check if program already exists
        if file_path.exists():
            #overwrite existing file
            file_path.unlink()
        
        # Add timestamps
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        program_data = program.dict()
        program_data["created"] = now
        program_data["modified"] = now
        
        # Save to file
        with open(file_path, 'w') as f:
            json.dump(program_data, f, indent=2)
        
        logger.info(f"Saved program: {program.name}")
        return {
            "status": "ok",
            "message": f"Program '{program.name}' saved successfully",
            "filename": file_path.name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving program {program.name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save program: {e}")

@app.put("/programs/{program_name}")
async def update_program(program_name: str, program: Program):
    """Update an existing program"""
    try:
        safe_name = sanitize_filename(program_name)
        file_path = PROGRAMS_DIR / f"{safe_name}.json"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Program '{program_name}' not found")
        
        # Load existing program to preserve created date
        with open(file_path, 'r') as f:
            existing_data = json.load(f)
        
        # Update with new data
        from datetime import datetime
        program_data = program.dict()
        program_data["created"] = existing_data.get("created")
        program_data["modified"] = datetime.utcnow().isoformat()
        
        # Save updated program
        with open(file_path, 'w') as f:
            json.dump(program_data, f, indent=2)
        
        logger.info(f"Updated program: {program.name}")
        return {
            "status": "ok",
            "message": f"Program '{program.name}' updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating program {program_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update program: {e}")

@app.delete("/programs/{program_name}")
async def delete_program(program_name: str):
    """Delete a program"""
    try:
        safe_name = sanitize_filename(program_name)
        file_path = PROGRAMS_DIR / f"{safe_name}.json"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Program '{program_name}' not found")
        
        file_path.unlink()
        logger.info(f"Deleted program: {program_name}")
        return {
            "status": "ok",
            "message": f"Program '{program_name}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting program {program_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete program: {e}")

@app.post('/api/home')
def home_axes():
    global movement_controller
    if movement_controller is None:
        logger.error('MovementController is not initialized')
        raise HTTPException(status_code=500, detail='Movement controller not initialized')
    try:
        movement_controller.home_axes()
    except Exception as e:
        logger.error(f'Error during homing: {e}')
    return {
        "status": "ok",
        "detail": "Homing started"
    }

# --- IO Control Endpoint ---
class SetIORequest(BaseModel):
    io_name: str
    state: bool

    @validator('io_name')
    def validate_io_name(cls, v):
        if v not in ['down', 'start']:
            raise ValueError('IO name must be "down" (mist) or "start" (flood)')
        return v

@app.post("/set_io")
async def set_io_endpoint(req: SetIORequest):
    """Set the state of an IO output (mist or flood coolant)"""
    if not is_connected or not movement_controller:
        raise HTTPException(status_code=503, detail="Mesa board not connected")
    
    try:
        movement_controller.set_io(req.io_name, req.state)
        
        state_description = "ON" if req.state else "OFF"
        
        return {
            "status": "ok",
            "message": f"{req.io_name} set to {state_description}",
            "io_name": req.io_name,
            "state": req.state
        }
    except Exception as e:
        logger.error(f"Error setting IO {req.io_name} to {req.state}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set IO: {e}") 
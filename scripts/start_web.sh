#!/bin/bash
# Start Web Development Servers
# This script starts both the FastAPI backend and React frontend
# Usage: ./start_web.sh [release] [port]
#   release: set to 'release' for production mode
#   port: optional port number (default: 8000)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Parse command line arguments
RELEASE_MODE=${1:-""}
PORT=${2:-8000}

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    print_status $RED "Error: Please run this script from the project root directory"
    exit 1
fi

if [ "$RELEASE_MODE" = "release" ]; then
    print_status $BLUE "Starting X-Y Table Web Servers in RELEASE MODE"
    echo "=================================================="
else
    print_status $BLUE "Starting X-Y Table Web Development Servers"
    echo "=================================================="
fi

# Function to cleanup background processes on exit
cleanup() {
    print_status $YELLOW "Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if required directories exist
if [ ! -d "webapi" ]; then
    print_status $RED "Error: webapi directory not found"
    exit 1
fi

if [ ! -d "frontend" ]; then
    print_status $RED "Error: frontend directory not found"
    exit 1
fi

# Check if linuxcnc module is available in system Python
print_status $BLUE "Checking LinuxCNC module availability..."
if ! python3 -c "import linuxcnc" 2>/dev/null; then
    print_status $RED "Error: LinuxCNC module not available in system Python"
    print_status $YELLOW "Please ensure LinuxCNC is properly installed"
    exit 1
fi
print_status $GREEN "✓ LinuxCNC module available"

# Install backend dependencies if needed (using system Python)
print_status $BLUE "Checking backend dependencies..."
cd webapi

# Check if required packages are installed in system Python
MISSING_DEPS=()
for dep in fastapi uvicorn pydantic; do
    if ! python3 -c "import $dep" 2>/dev/null; then
        MISSING_DEPS+=($dep)
    fi
done

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    print_status $YELLOW "Installing missing backend dependencies: ${MISSING_DEPS[*]}"
    sudo apt update
    for dep in "${MISSING_DEPS[@]}"; do
        case $dep in
            fastapi)
                sudo apt install -y python3-fastapi
                ;;
            uvicorn)
                sudo apt install -y python3-uvicorn
                ;;
            pydantic)
                sudo apt install -y python3-pydantic
                ;;
        esac
    done
fi

cd ..

# Install frontend dependencies if needed
print_status $BLUE "Checking frontend dependencies..."
cd frontend
if [ ! -d "node_modules" ]; then
    print_status $YELLOW "Installing frontend dependencies..."
    npm install --legacy-peer-deps
fi
cd ..

# Start backend server with system Python
if [ "$RELEASE_MODE" = "release" ]; then
    print_status $BLUE "Starting FastAPI backend server in PRODUCTION mode (using system Python)..."
    python3 -m uvicorn webapi.main:app --host 0.0.0.0 --port $PORT &
else
    print_status $BLUE "Starting FastAPI backend server in DEVELOPMENT mode (using system Python)..."
    python3 -m uvicorn webapi.main:app --host 0.0.0.0 --port $PORT --reload &
fi
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Check if backend started successfully
if kill -0 $BACKEND_PID 2>/dev/null; then
    print_status $GREEN "✓ Backend server started on http://localhost:$PORT"
else
    print_status $RED "✗ Failed to start backend server"
    exit 1
fi

# Start frontend server
if [ "$RELEASE_MODE" = "release" ]; then
    print_status $BLUE "Starting React frontend server in PRODUCTION mode..."
    cd frontend/
    # Build the production version
    npm run build
    # Serve the built files
    npx serve -s build -l 3000 &
    FRONTEND_PID=$!
    cd ..
else
    print_status $BLUE "Starting React frontend server in DEVELOPMENT mode..."
    cd frontend/
    npm start &
    FRONTEND_PID=$!
    cd ..
fi

# Wait a moment for frontend to start
sleep 3

# Check if frontend started successfully
if kill -0 $FRONTEND_PID 2>/dev/null; then
    print_status $GREEN "✓ Frontend server started on http://localhost:3000"
else
    print_status $RED "✗ Failed to start frontend server"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

print_status $GREEN "=================================================="
print_status $GREEN "Both servers are running!"
print_status $BLUE "Backend API:  http://localhost:$PORT"
print_status $BLUE "Frontend UI:  http://localhost:3000"
print_status $BLUE "API Docs:     http://localhost:$PORT/docs"
if [ "$RELEASE_MODE" = "release" ]; then
    print_status $YELLOW "Running in PRODUCTION mode"
else
    print_status $YELLOW "Running in DEVELOPMENT mode"
fi
print_status $YELLOW "Press Ctrl+C to stop both servers"
echo ""

# Wait for user to stop
wait 

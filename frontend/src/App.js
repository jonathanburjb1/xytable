import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import ProgramBuilder from './components/ProgramBuilder';
import XYVisualizer from './components/XYVisualizer';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [status, setStatus] = useState({ connected: false, current_position: { x: 0, y: 0 } });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tableLimits, setTableLimits] = useState({
    x_axis: { min: 0, max: 107.95, max_speed: 500 },
    y_axis: { min: 0, max: 79.375, max_speed: 500 }
  });
  const [reconnecting, setReconnecting] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [lastReconnectTime, setLastReconnectTime] = useState(null);
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);
  const [quickMoveIncrement, setQuickMoveIncrement] = useState(0.1);
  const [jogging, setJogging] = useState({ x: false, y: false });
  const jogSocketRef = useRef(null);
  const jogKeyTimers = useRef({}); // { x: timer, y: timer }
  const jogActiveAxis = useRef({ x: false, y: false });
  const [homing, setHoming] = useState(false);
  const [ioStates, setIoStates] = useState({ down: false, start: false });

  // Reconnection settings
  const RECONNECT_INTERVAL = 2000; // 2 seconds
  const MAX_RECONNECT_ATTEMPTS = 12; // 1 minute of attempts
  const RECONNECT_COOLDOWN = 30000; // 30 seconds cooldown after max attempts

  // Fetch status and limits on component mount
  useEffect(() => {
    fetchStatus();
    fetchLimits();
    
    // Set up periodic status updates
    const statusInterval = setInterval(fetchStatus, 5000);
    return () => clearInterval(statusInterval);
  }, []);

  // Set up reconnection logic
  useEffect(() => {
    let reconnectInterval = null;

    const shouldAttemptReconnect = () => {
      const now = Date.now();
      
      // Don't reconnect if already connected
      if (status.connected) {
        setReconnecting(false);
        setReconnectAttempts(0);
        return false;
      }

      // Don't reconnect if we're in cooldown period
      if (lastReconnectTime && (now - lastReconnectTime) < RECONNECT_COOLDOWN) {
        return false;
      }

      // Don't reconnect if we've exceeded max attempts
      if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        return false;
      }

      return true;
    };

    const attemptReconnect = async () => {
      if (!shouldAttemptReconnect()) return;

      setReconnecting(true);
      setReconnectAttempts(prev => prev + 1);
      setLastReconnectTime(Date.now());

      try {
        // Fetch status to check if connection was established
        await fetchStatus();
        
        if (status.connected) {
          setReconnecting(false);
          setReconnectAttempts(0);
          setError(null);
          console.log('Successfully reconnected to LinuxCNC');
        }
      } catch (err) {
        console.log(`Reconnection attempt ${reconnectAttempts + 1} failed:`, err.message);
      } finally {
        setReconnecting(false);
      }
    };

    // Set up reconnection interval
    if (!status.connected && !reconnecting) {
      reconnectInterval = setInterval(attemptReconnect, RECONNECT_INTERVAL);
    }

    return () => {
      if (reconnectInterval) {
        clearInterval(reconnectInterval);
      }
    };
  }, [status.connected, reconnecting, reconnectAttempts, lastReconnectTime]);

  // Setup WebSocket for jog control
  useEffect(() => {
    // Only create WebSocket when backend is connected
    if (!status.connected) {
      // Close existing WebSocket if backend is not connected
      if (jogSocketRef.current) {
        jogSocketRef.current.close();
        jogSocketRef.current = null;
      }
      return;
    }

    // Don't create multiple WebSockets
    if (jogSocketRef.current && jogSocketRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    console.log('Creating jog WebSocket connection...');
    const ws = new window.WebSocket('ws://10.200.0.142:8000/ws/jog');
    jogSocketRef.current = ws;
    
    ws.onopen = () => {
      console.log('Jog WebSocket connected');
    };
    
    ws.onclose = (event) => {
      console.log('Jog WebSocket closed', event.code, event.reason);
      setJogging({ x: false, y: false });
      jogSocketRef.current = null;
      
      // Only attempt reconnection if backend is still connected
      if (status.connected) {
        console.log('Attempting to reconnect jog WebSocket in 2 seconds...');
        setTimeout(() => {
          if (status.connected) {
            // Trigger reconnection by updating a dependency
            setJogging(prev => ({ ...prev }));
          }
        }, 2000);
      }
    };
    
    ws.onerror = (e) => {
      console.error('Jog WebSocket error', e);
      setJogging({ x: false, y: false });
    };
    
    ws.onmessage = (event) => {
      // Optionally handle jog status/ack
      try {
        const msg = JSON.parse(event.data);
        console.log('Jog WS:', msg);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };
    
    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [status.connected]); // Re-run when backend connection status changes

  // Helper to send jog command
  const sendJogCommand = (action, axis, direction = 1, speed = 0.1) => {
    const ws = jogSocketRef.current;
    console.log('sendJogCommand Called');
    if (ws && ws.readyState === 1) {
      console.log('sendJogCommand Sending', { action, axis, direction, speed });
      ws.send(JSON.stringify({ action, axis, direction, speed }));
    }
  };

  // Keyboard event handling with jog logic
  useEffect(() => {
    const keyMap = {
      ArrowUp: { axis: 'y', dir: 1 },
      ArrowDown: { axis: 'y', dir: -1 },
      ArrowLeft: { axis: 'x', dir: -1 },
      ArrowRight: { axis: 'x', dir: 1 },
      w: { axis: 'y', dir: 1 },
      W: { axis: 'y', dir: 1 },
      s: { axis: 'y', dir: -1 },
      S: { axis: 'y', dir: -1 },
      a: { axis: 'x', dir: -1 },
      A: { axis: 'x', dir: -1 },
      d: { axis: 'x', dir: 1 },
      D: { axis: 'x', dir: 1 },
    };

    const handleKeyDown = (event) => {
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
      const key = event.key;
      if (keyMap[key]) {
        const { axis, dir } = keyMap[key];
        if (jogActiveAxis.current[axis]) return; // Already jogging this axis
        
        if (!event.repeat) {
          // First keydown - do quick move and start timer
          console.log(`Key down for ${axis} axis at ${Date.now()}`);
          handleQuickMove(axis + (dir > 0 ? '+' : '-'));
          console.log(`Starting 400ms timer for ${axis} axis`);
          jogKeyTimers.current[axis] = setTimeout(() => {
            console.log(`Timer fired for ${axis} axis - starting jog at ${Date.now()}`);
            sendJogCommand('start', axis, dir, quickMoveIncrement);
            jogActiveAxis.current[axis] = true;
            setJogging((prev) => ({ ...prev, [axis]: true }));
          }, 400);
        } else {
          // Key repeat - if we're not jogging yet, start jogging immediately
          console.log(`Key repeat for ${axis} axis at ${Date.now()}`);
          if (!jogActiveAxis.current[axis] && jogKeyTimers.current[axis]) {
            console.log(`Key repeat detected - starting jog immediately for ${axis} axis`);
            clearTimeout(jogKeyTimers.current[axis]);
            jogKeyTimers.current[axis] = null;
            sendJogCommand('start', axis, dir, quickMoveIncrement);
            jogActiveAxis.current[axis] = true;
            setJogging((prev) => ({ ...prev, [axis]: true }));
          }
        }
      } else {
        switch (key) {
          case '.':
            setIO('down', true);
            break;
          case ',':
            setIO('down', false);
            break;
        }
      }
    };

    const handleKeyUp = (event) => {
      const key = event.key;
      if (keyMap[key]) {
        const { axis } = keyMap[key];
        console.log(`Key up for ${axis} axis at ${Date.now()}`);
        // Clear timer if running
        if (jogKeyTimers.current[axis]) {
          console.log(`Clearing timer for ${axis} axis`);
          clearTimeout(jogKeyTimers.current[axis]);
          jogKeyTimers.current[axis] = null;
        }
        // If jogging, stop jog
        if (jogActiveAxis.current[axis]) {
          console.log(`Stopping jog for ${axis} axis`);
          sendJogCommand('stop', axis);
          jogActiveAxis.current[axis] = false;
          setJogging((prev) => ({ ...prev, [axis]: false }));
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown, true);
    document.addEventListener('keyup', handleKeyUp, true);
    return () => {
      document.removeEventListener('keydown', handleKeyDown, true);
      document.removeEventListener('keyup', handleKeyUp, true);
      // Cleanup timers
      Object.values(jogKeyTimers.current).forEach((timer) => timer && clearTimeout(timer));
    };
  }, [quickMoveIncrement, loading, status.connected]);

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/status`);
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
        
        // Clear error if we're now connected
        if (data.connected) {
          setError(null);
        }
      } else {
        console.error('Failed to fetch status:', response.status);
      }
    } catch (err) {
      console.error('Error fetching status:', err);
      // Only set error if we're not in reconnection mode
      if (!reconnecting) {
        setError('Failed to connect to backend');
      }
    }
  };

  const fetchLimits = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/limits`);
      if (response.ok) {
        const data = await response.json();
        setTableLimits(data);
      }
    } catch (err) {
      console.error('Error fetching limits:', err);
    }
  };

  const moveAxis = async (axis, distance, speed = null) => {
    setLoading(true);
    setError(null);
    
    try {
      const payload = { axis, distance: parseFloat(distance) };
      if (speed) payload.speed = parseFloat(speed);
      
      const response = await fetch(`${API_BASE_URL}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Movement successful:', data);
        await fetchStatus(); // Refresh status
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Movement failed');
      }
    } catch (err) {
      console.error('Movement error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const moveToPosition = async (x, y, speed = null) => {
    setLoading(true);
    setError(null);
    
    try {
      const payload = { x: parseFloat(x), y: parseFloat(y) };
      if (speed) payload.speed = parseFloat(speed);
      
      const response = await fetch(`${API_BASE_URL}/move_to`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Position movement successful:', data);
        await fetchStatus(); // Refresh status
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Position movement failed');
      }
    } catch (err) {
      console.error('Position movement error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const emergencyStop = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/emergency_stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Emergency stop executed:', data);
        await fetchStatus(); // Refresh status
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Emergency stop failed');
      }
    } catch (err) {
      console.error('Emergency stop error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const clearEmergencyStop = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/clear_emergency_stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Emergency stop cleared:', data);
        await fetchStatus(); // Refresh status
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Clear emergency stop failed');
      }
    } catch (err) {
      console.error('Clear emergency stop error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickMove = (direction) => {
    const distance = quickMoveIncrement;
    switch (direction) {
      case 'x+':
        moveAxis('x', distance);
        break;
      case 'x-':
        moveAxis('x', -distance);
        break;
      case 'y+':
        moveAxis('y', distance);
        break;
      case 'y-':
        moveAxis('y', -distance);
        break;
      default:
        break;
    }
  };
  
  const getConnectionStatus = () => {
    if (status.connected) {
      return { text: 'Connected', className: 'connected' };
    } else if (reconnecting) {
      return { text: `Reconnecting... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`, className: 'reconnecting' };
    } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      return { text: 'Connection Failed - Retry in 30s', className: 'failed' };
    } else {
      return { text: 'Disconnected', className: 'disconnected' };
    }
  };

  const connectionStatus = getConnectionStatus();

  const isEstop = !!status.emergency_stop;

  const homeAxes = async () => {
    if (!window.confirm('Are you sure you want to home all axes?')) return;
    setHoming(true);
    try {
      const response = await fetch('http://localhost:8000/api/home', { method: 'POST' });
      if (!response.ok) {
        const error = await response.json();
        alert('Failed to start homing: ' + (error.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('Error starting homing: ' + err.message);
    } finally {
      setHoming(false);
    }
  };

  const setIO = async (io_name, state) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/set_io`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ io_name, state })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Set IO successful:', data);
        // Update local state to reflect the change
        setIoStates(prev => ({ ...prev, [io_name]: state }));
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Set IO failed');
      }
    } catch (err) {
      console.error('Set IO error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>X-Y Table Control System</h1>
        <div className="status-indicator">
          <span className={`status-dot ${connectionStatus.className}`}></span>
          <span className={connectionStatus.className}>{connectionStatus.text}</span>
          {Boolean(status.emergency_stop) && (
            <span 
              className="estop-indicator clickable" 
              onClick={clearEmergencyStop}
              title="Click to clear emergency stop and repower machine"
            >
              <span className="estop-dot"></span>
              <span className="estop-text">E-STOP</span>
            </span>
          )}
        </div>
      </header>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
          <button onClick={() => setError(null)}></button>
        </div>
      )}

      {showKeyboardHelp && (
        <div className="keyboard-help-panel">
          <div className="help-content">
            <h3>Keyboard Shortcuts</h3>
            <div className="shortcuts-grid">
              <div className="shortcut-item">
                <kbd>Esc</kbd>
                <span>Emergency Stop</span>
              </div>
              <div className="shortcut-item">
                <kbd>Space</kbd>
                <span>Toggle Help</span>
              </div>
              <div className="shortcut-item">
                <kbd>R</kbd>
                <span>Refresh Status</span>
              </div>
              <div className="shortcut-item">
                <kbd>U</kbd>
                <span>Move Y+</span>
              </div>
              <div className="shortcut-item">
                <kbd>D</kbd>
                <span>Move Y-</span>
              </div>
              <div className="shortcut-item">
                <kbd>↑</kbd>
                <span>Move Y+</span>
              </div>
              <div className="shortcut-item">
                <kbd>↓</kbd>
                <span>Move Y-</span>
              </div>
              <div className="shortcut-item">
                <kbd>←</kbd>
                <span>Move X-</span>
              </div>
              <div className="shortcut-item">
                <kbd>→</kbd>
                <span>Move X+</span>
              </div>
            </div>
            <div className="help-note">
              <p><strong>Note:</strong> Click the E-STOP indicator to clear emergency stop and repower the machine.</p>
            </div>
            <button 
              className="close-help-btn" 
              onClick={() => setShowKeyboardHelp(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {!status.connected && (
        <div className="connection-info">
          <div className="info-panel">
            <h3>Connection Status</h3>
            <p>The system is attempting to connect to LinuxCNC automatically.</p>
            <ul>
              <li>Reconnection attempts: {reconnectAttempts}/{MAX_RECONNECT_ATTEMPTS}</li>
              <li>Attempt interval: {RECONNECT_INTERVAL/1000} seconds</li>
              <li>Cooldown period: {RECONNECT_COOLDOWN/1000} seconds after max attempts</li>
            </ul>
            {reconnectAttempts >= MAX_RECONNECT_ATTEMPTS && (
              <div className="cooldown-info">
                <p>Maximum reconnection attempts reached. The system will retry in 30 seconds.</p>
                <p>Please check:</p>
                <ul>
                  <li>LinuxCNC is running and properly configured</li>
                  <li>Mesa 7I96S board is connected and powered</li>
                  <li>Network connection to the board is established</li>
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="main-layout">
        {/* Left Column - Status and Manual Controls */}
        <div className="left-column">
          <div className="status-panel">
            <h3>Current Status</h3>
            <div className="status-grid">
              <div className="status-item">
                <label>X Position:</label>
                <span>{status.current_position?.x?.toFixed(3) || '0.000'} inches</span>
              </div>
              <div className="status-item">
                <label>Y Position:</label>
                <span>{status.current_position?.y?.toFixed(3) || '0.000'} inches</span>
              </div>
              <div className="status-item">
                <label>Connection:</label>
                <span className={status.connected ? 'connected' : 'disconnected'}>
                  {status.connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>

          <div className="manual-controls">
            <h3>Manual Controls</h3>
            
            <div className="quick-moves">
              {/* Quick Move Increment Buttons */}
              <div className="quick-move-increments" style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', justifyContent: 'center' }}>
                {[0.1, 0.01, 0.001, 0.0001].map((inc) => (
                  <button
                    key={inc}
                    type="button"
                    className={`quick-move-increment-btn${quickMoveIncrement === inc ? ' active' : ''}`}
                    style={{
                      padding: '0.3rem 0.8rem',
                      background: quickMoveIncrement === inc ? '#fff' : '#222',
                      color: quickMoveIncrement === inc ? '#cc0000' : '#fff',
                      border: quickMoveIncrement === inc ? '2px solid #cc0000' : '1px solid #444',
                      borderRadius: '4px',
                      fontWeight: 700,
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      outline: quickMoveIncrement === inc ? '2px solid #cc0000' : 'none',
                      boxShadow: quickMoveIncrement === inc ? '0 0 6px #cc000088' : 'none',
                      transition: 'all 0.2s',
                    }}
                    onClick={() => setQuickMoveIncrement(inc)}
                  >
                    {inc}
                  </button>
                ))}
              </div>
              {/* Remove the label 'Quick Movement (0.1 inches)' */}
              <div className="quick-move-buttons">
                <button onClick={() => handleQuickMove('x-')} disabled={loading || !status.connected || isEstop}>X-</button>
                <button onClick={() => handleQuickMove('x+')} disabled={loading || !status.connected || isEstop}>X+</button>
                <button onClick={() => handleQuickMove('y-')} disabled={loading || !status.connected || isEstop}>Y-</button>
                <button onClick={() => handleQuickMove('y+')} disabled={loading || !status.connected || isEstop}>Y+</button>
              </div>
            </div>

            <div className="manual-moves">
              <h4>Manual Movement</h4>
              <div className="move-controls">
                <div className="move-group">
                  <label>X Axis:</label>
                  <input type="number" id="x-distance" placeholder="Distance (inches)" step="0.01" />
                  <button onClick={() => {
                    const distance = document.getElementById('x-distance').value;
                    if (distance) moveAxis('x', distance, 10);
                  }} disabled={loading || !status.connected || isEstop}>Move X</button>
                </div>
                
                <div className="move-group">
                  <label>Y Axis:</label>
                  <input type="number" id="y-distance" placeholder="Distance (inches)" step="0.01" />
                  <button onClick={() => {
                    const distance = document.getElementById('y-distance').value;
                    if (distance) moveAxis('y', distance, 10);
                  }} disabled={loading || !status.connected || isEstop}>Move Y</button>
                </div>
              </div>
            </div>

            <div className="absolute-position">
              <h4>Move to Position</h4>
              <div className="position-controls">
                <input type="number" id="target-x" placeholder="X Position (in.)" step="0.01" />
                <input type="number" id="target-y" placeholder="Y Position (in.)" step="0.01" />
                <button onClick={() => {
                  const x = document.getElementById('target-x').value;
                  const y = document.getElementById('target-y').value;
                  if (x && y) moveToPosition(x, y, 10);
                }} disabled={loading || !status.connected || isEstop}>Move To Position</button>
              </div>
            </div>

            <div className="emergency-stop">
              <button 
                className="emergency-stop-btn" 
                onClick={emergencyStop}
                disabled={loading || !status.connected}
              >
                EMERGENCY STOP
              </button>
            </div>

            <div className="io-controls">
              <h4>IO Controls</h4>
              <div className="io-buttons">
                <button 
                  className={`io-btn ${ioStates.down ? 'active' : ''}`}
                  onClick={() => setIO('down', !ioStates.down)}
                  disabled={loading || !status.connected || isEstop}
                >
                  {ioStates.down ? 'DOWN ON' : 'DOWN OFF'}
                </button>
                <button 
                  className={`io-btn ${ioStates.start ? 'active' : ''}`}
                  onClick={() => setIO('start', !ioStates.start)}
                  disabled={loading || !status.connected || isEstop}
                >
                  {ioStates.start ? 'START ON' : 'START OFF'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Center Column - Program Builder */}
        <div className="center-column">
          <ProgramBuilder 
            onExecuteMove={moveAxis}
            onExecuteMoveTo={moveToPosition}
            onExecuteSetIO={setIO}
            currentPosition={status.current_position}
            tableLimits={tableLimits}
            connected={status.connected}
            loading={loading}
            estop={isEstop}
          />
        </div>

        {/* Right Column - Visualizer and Future Space */}
        <div className="right-column">
          <div className="visualizer-section">
            <XYVisualizer 
              onMoveTo={moveToPosition}
              currentPosition={status.current_position}
              tableLimits={tableLimits}
              connected={status.connected}
              loading={loading}
            />
          </div>
          
          <div className="future-section">
            <div className="future-placeholder">
              <button
                onClick={homeAxes}
                disabled={homing || loading || !status.connected || isEstop || status.movement_in_progress}
                style={{
                  marginTop: '1rem',
                  padding: '0.6rem 1.2rem',
                  background: '#cc0000',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '0.9rem',
                  fontWeight: 700,
                  cursor: homing || loading || !status.connected || isEstop || status.movement_in_progress ? 'not-allowed' : 'pointer',
                  opacity: homing || loading || !status.connected || isEstop || status.movement_in_progress ? 0.6 : 1,
                  transition: 'all 0.3s ease',
                }}
              >
                {homing ? 'Homing...' : 'Home All Axes'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

import React, { useState, useEffect, useRef } from 'react';
import './ProgramBuilder.css';

const API_BASE_URL = 'http://localhost:8000';

const ProgramBuilder = ({ 
  onExecuteMove, 
  onExecuteMoveTo, 
  onExecuteSetIO,
  currentPosition, 
  tableLimits, 
  connected, 
  loading, 
  estop 
}) => {
  const [program, setProgram] = useState([]);
  const [newCommand, setNewCommand] = useState({
    type: 'move_to',
    axis: 'xy',
    x_position: 0,
    y_position: 0,
    speed: 2.0,
    delay: 0,
    position: 0,
    loop_count: 1,
    message_text: '',
    io_name: 'down',
    io_state: false
  });
  const [executing, setExecuting] = useState(false);
  const [programStatus, setProgramStatus] = useState('idle'); // idle, running, paused, completed, error
  const [messageModal, setMessageModal] = useState({ show: false, message: '', onContinue: null, onPause: null });
  const [selectedLine, setSelectedLine] = useState(null); // Index of selected line (0-based), also used for execution tracking
  const [loadModal, setLoadModal] = useState({ show: false, programs: [], selected: null, loading: false, error: null });
  
  // Ref to track current programStatus for async operations
  const programStatusRef = useRef(programStatus);
  
  // Update ref whenever programStatus changes
  useEffect(() => {
    programStatusRef.current = programStatus;
  }, [programStatus]);

  // Update absolute position fields with current machine position when creating new commands
  useEffect(() => {
    if (currentPosition && selectedLine === null && newCommand.type === 'move_to') {
      // Only update if we're not editing an existing command and the form is set to absolute movement
      if (newCommand.axis === 'xy') {
        setNewCommand(prev => ({
          ...prev,
          x_position: currentPosition.x.toFixed(3) || 0,
          y_position: currentPosition.y.toFixed(3) || 0
        }));
      } else if (newCommand.axis === 'x') {
        setNewCommand(prev => ({
          ...prev,
          position: currentPosition.x.toFixed(3) || 0
        }));
      } else if (newCommand.axis === 'y') {
        setNewCommand(prev => ({
          ...prev,
          position: currentPosition.y.toFixed(3) || 0
        }));
      }
    }
  }, [currentPosition, selectedLine, newCommand.type, newCommand.axis]);

  // Reset program status when program changes
  useEffect(() => {
    setProgramStatus('idle');
    //setSelectedLine(null);
  }, [program]);

  // Keyboard event handling for spacebar execution
  useEffect(() => {
    const handleKeyDown = (event) => {
      // Only handle spacebar when not in input fields and program is not running
      if (event.code === 'Space' && 
          event.target.tagName !== 'INPUT' && 
          event.target.tagName !== 'TEXTAREA' &&
          programStatus !== 'running' && 
          programStatus !== 'paused' &&
          !executing) {
        event.preventDefault();
        
        // Execute selected line if one is selected, otherwise do nothing
        if (selectedLine !== null) {
          executeSingleLine(selectedLine);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedLine, programStatus, executing, connected, estop, program]);

  const addOrUpdateCommand = () => {
    if (newCommand.type === 'move' && newCommand.distance === 0) {
      alert('Please enter a non-zero distance for move commands.');
      return;
    }
    if (newCommand.type === 'move_to') {
      if ((newCommand.axis === 'x' || newCommand.axis === 'y') && (newCommand.position === null || newCommand.position === undefined)) {
        alert('Please enter a valid position for absolute move commands.');
        return;
      }
      if (newCommand.axis === 'xy' && (newCommand.x_position === null || newCommand.x_position === undefined || newCommand.y_position === null || newCommand.y_position === undefined)) {
        alert('Please enter both X and Y positions for absolute move commands.');
        return;
      }
    }
    if (newCommand.type === 'wait' && newCommand.delay === 0) {
      alert('Please enter a non-zero delay for wait commands.');
      return;
    }
    if (newCommand.type === 'loop' && (!newCommand.loop_count || newCommand.loop_count < 1)) {
      alert('Please enter a valid loop count (minimum 1).');
      return;
    }
    if (newCommand.type === 'message' && (!newCommand.message_text || newCommand.message_text.trim() === '')) {
      alert('Please enter a message to display.');
      return;
    }
    if (newCommand.type === 'set_io' && (!newCommand.io_name || newCommand.io_state === undefined)) {
      alert('Please select both IO type and state for set_io commands.');
      return;
    }
    if (selectedLine !== null) {
      // Update existing command
      const updatedProgram = [...program];
      updatedProgram[selectedLine] = {
        ...updatedProgram[selectedLine],
        ...newCommand
      };
      setProgram(updatedProgram);
      setSelectedLine(null);
      setNewCommand({
        type: 'move',
        axis: 'x',
        distance: 0,
        speed: 2.0,
        delay: 0,
        position: 0,
        x_position: 0,
        y_position: 0,
        loop_count: 1,
        message_text: '',
        io_name: 'down',
        io_state: false
      });
    } else {
      // Add new command
      const command = {
        ...newCommand,
        id: Date.now() + Math.random(), // Ensure unique IDs
        step: program.length + 1
      };
      setProgram([...program, command]);
      setNewCommand({
        type: 'move',
        axis: 'x',
        distance: 0,
        speed: 2.0,
        delay: 0,
        position: 0,
        x_position: 0,
        y_position: 0,
        loop_count: 1,
        message_text: '',
        io_name: 'down',
        io_state: false
      });
    }
  };

  const insertCommand = () => {
    console.log('insertCommand', selectedLine);

    if (selectedLine === null) {
      alert('Please select a line to insert above.');
      return;
    }
    const command = {
      type: null,
      axis: null,
      distance: null,
      speed: null,
      delay: null,
      position: null,
      x_position: null,
      id: Date.now() + Math.random(),
      step: selectedLine - 1
    };

    setProgram(prevProgram => {
      const newProgram = [
        ...prevProgram.slice(0, selectedLine),
        command,
        ...prevProgram.slice(selectedLine)
      ];
      // Optionally update step numbers
      newProgram.forEach((cmd, idx) => { cmd.step = idx + 1; });
      return newProgram;
    });
    
    setSelectedLine(selectedLine); // Select the newly inserted command

  };

  const removeCommand = () => {
    setProgram(program.filter((_, idx) => idx !== selectedLine));
    if (selectedLine === program.length) {
      setSelectedLine(selectedLine - 1);
    }
  };

  const moveCommand = (direction) => {
    if(selectedLine === null) {
      return;
    }
    
    setProgram(program => {
      const newProgram = [...program];
      if (direction === 'up' && selectedLine > 0) {
        [newProgram[selectedLine], newProgram[selectedLine - 1]] = [newProgram[selectedLine - 1], newProgram[selectedLine]];
        setSelectedLine(selectedLine - 1);
      } else if (direction === 'down' && selectedLine < newProgram.length - 1) {
        [newProgram[selectedLine], newProgram[selectedLine + 1]] = [newProgram[selectedLine + 1], newProgram[selectedLine]];
        setSelectedLine(selectedLine + 1);
      }
      newProgram.forEach((cmd, idx) => { cmd.step = idx + 1; });
      return newProgram;
    });
  };

  const executeProgram = async () => {
    if (program.length === 0 || !connected || executing || estop) return;
    setExecuting(true);
    setProgramStatus('running');
    // Start from selected line if one is selected, otherwise start from beginning
    let startIndex = selectedLine !== null ? selectedLine : 0;
    setSelectedLine(startIndex);
    try {
      await executeCommands(startIndex, program.length);
      setProgramStatus('completed');
    } catch (error) {
      console.error('Error executing program:', error);
      setProgramStatus('error');
      alert(`Program execution failed: ${error.message}`);
    } finally {
      setExecuting(false);
    }
  };

  const executeCommands = async (startIndex, endIndex, loopCount = 1) => {
    for (let loop = 0; loop < loopCount; loop++) {
      for (let i = startIndex; i < endIndex; i++) {
        // Use ref to get current programStatus (not stale closure value)
        if (programStatusRef.current === 'paused') {
          console.log('Program paused - waiting for resume');
          while (programStatusRef.current === 'paused') {
            await new Promise(resolve => setTimeout(resolve, 100));
          }
        }
        
        const command = program[i];
        setSelectedLine(i);
        
        if (command.type === 'move') {
          // Execute relative movement
          await onExecuteMove(command.axis, command.distance, 10);
        } else if (command.type === 'move_to') {
          // Execute absolute movement
          if (command.axis === 'xy') {
            // Both X and Y movement
            await onExecuteMoveTo(command.x_position, command.y_position, 10);
          } else {
            // Single axis movement
            const targetX = command.axis === 'x' ? command.position : currentPosition.x;
            const targetY = command.axis === 'y' ? command.position : currentPosition.y;
            await onExecuteMoveTo(targetX, targetY, 10);
          }
        } else if (command.type === 'wait') {
          // Wait for specified time
          await new Promise(resolve => setTimeout(resolve, command.delay * 1000));
        } else if (command.type === 'loop') {
          // Find the corresponding endloop
          const endLoopIndex = findEndLoopIndex(i + 1);
          if (endLoopIndex !== -1) {
            // Execute the loop body
            await executeCommands(i + 1, endLoopIndex, command.loop_count);
            // Skip to after the endloop
            i = endLoopIndex;
          }
        } else if (command.type === 'endloop') {
          // End of loop - continue to next command
          continue;
        } else if (command.type === 'message') {
          // Show message modal
          await showMessageModal(command.message_text);
        } else if (command.type === 'set_io') {
          // Handle set_io command
          const ioDisplayName = command.io_name;
          await onExecuteSetIO(command.io_name, command.io_state);
        }
        
        // Add delay after command if specified
        if (command.delay > 0) {
          await new Promise(resolve => setTimeout(resolve, command.delay * 1000));
        }
      }
    }
  };

  const findEndLoopIndex = (startIndex) => {
    let loopDepth = 1;
    for (let i = startIndex; i < program.length; i++) {
      if (program[i].type === 'loop') {
        loopDepth++;
      } else if (program[i].type === 'endloop') {
        loopDepth--;
        if (loopDepth === 0) {
          return i;
        }
      }
    }
    return -1; // No matching endloop found
  };

  const showMessageModal = (message) => {
    return new Promise((resolve) => {
      setMessageModal({
        show: true,
        message: message,
        onContinue: () => {
          setMessageModal({ show: false, message: '', onContinue: null, onPause: null });
          resolve();
        },
        onPause: () => {
          setMessageModal({ show: false, message: '', onContinue: null, onPause: null });
          setProgramStatus('paused');
          resolve();
        }
      });
    });
  };

  const pauseProgram = () => {
    setProgramStatus('paused');
    setExecuting(false);
  };

  const resumeProgram = () => {
    if (programStatus === 'paused') {
      executeProgram();
    }
  };

  const stopProgram = () => {
    setExecuting(false);
    setProgramStatus('idle');
    setSelectedLine(null);
  };

  const clearProgram = () => {
    setProgram([]);
    setProgramStatus('idle');
    setSelectedLine(null);
  };

  const handleLineSelect = (index) => {
    if (programStatus === 'running' || programStatus === 'paused') {
      return; // Don't allow selection while program is running
    }
    setSelectedLine(index);
    // Auto-populate form with selected command
    const command = program[index];
    if (!command.type) {
      // Blank line: default to absolute XY movement with current position
      setNewCommand({
        type: 'move_to',
        axis: 'xy',
        x_position: currentPosition?.x.toFixed(3) || 0,
        y_position: currentPosition?.y.toFixed(3) || 0,
        speed: 2.0,
        distance: 0,
        delay: 0,
        position: 0,
        loop_count: 1,
        message_text: '',
        io_name: 'down',
        io_state: false
      });
    } else {
      setNewCommand({
        type: command.type,
        axis: command.axis || 'x',
        distance: command.distance || 0,
        speed: command.speed || 2.0,
        delay: command.delay || 0,
        position: command.position || 0,
        x_position: command.x_position || 0,
        y_position: command.y_position || 0,
        loop_count: command.loop_count || 1,
        message_text: command.message_text || '',
        io_name: command.io_name || 'down',
        io_state: command.io_state || false
      });
    }
  };

  const executeSingleLine = async (index) => {
    if (!connected || executing || estop || index < 0 || index >= program.length) {
      return;
    }
    const command = program[index];
    setExecuting(true);
    setSelectedLine(index);
    try {
      if (command.type === 'move') {
        await onExecuteMove(command.axis, command.distance, 10);
      } else if (command.type === 'move_to') {
        if (command.axis === 'xy') {
          await onExecuteMoveTo(command.x_position, command.y_position, 10);
        } else {
          // For single axis move_to, we need current position for the other axis
          const currentX = currentPosition?.x || 0;
          const currentY = currentPosition?.y || 0;
          const targetX = command.axis === 'x' ? command.position : currentX;
          const targetY = command.axis === 'y' ? command.position : currentY;
          await onExecuteMoveTo(targetX, targetY, 10);
        }
      } else if (command.type === 'wait') {
        await new Promise(resolve => setTimeout(resolve, command.delay * 1000));
      } else if (command.type === 'message') {
        await showMessageModal(command.message_text);
      } else if (command.type === 'set_io') {
        // Handle set_io command
        const ioDisplayName = command.io_name;
        await onExecuteSetIO(command.io_name, command.io_state);
      }
      // Note: loop and endloop commands are skipped for single line execution
      
      console.log(`Executed single line ${index + 1}: ${command.type}`);
    } catch (error) {
      console.error(`Error executing line ${index + 1}:`, error);
      alert(`Error executing line ${index + 1}: ${error.message}`);
    } finally {
      setExecuting(false);
      if(selectedLine === program.length - 1) {
        setSelectedLine(null);
      }else{
        setSelectedLine(selectedLine + 1);
      }
    }
  };

  const saveProgram = async () => {
    const programName = prompt('Enter program name:');
    if (!programName || !programName.trim()) return;

    const trimmedName = programName.trim();
    
    try {
      const programData = {
        name: trimmedName,
        program: program,
        description: prompt('Enter program description (optional):') || ''
      };

      const response = await fetch(`${API_BASE_URL}/programs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(programData)
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Program "${trimmedName}" saved successfully!`);
      } else {
        const error = await response.json();
        alert(`Failed to save program: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error saving program:', error);
      alert(`Error saving program: ${error.message}`);
    }
  };

  const openLoadModal = async () => {
    setLoadModal({ show: true, programs: [], selected: null, loading: true, error: null });
    try {
      const response = await fetch(`${API_BASE_URL}/programs`);
      if (!response.ok) throw new Error('Failed to load program list.');
      const data = await response.json();
      if (!data.programs || data.programs.length === 0) {
        setLoadModal({ show: true, programs: [], selected: null, loading: false, error: 'No saved programs found on server.' });
        return;
      }
             setLoadModal({ show: true, programs: data.programs, selected: data.programs[0]?.name || null, loading: false, error: null });
    } catch (error) {
      setLoadModal({ show: true, programs: [], selected: null, loading: false, error: error.message });
    }
  };

  const closeLoadModal = () => setLoadModal({ show: false, programs: [], selected: null, loading: false, error: null });

  const handleLoadProgram = async () => {
    if (!loadModal.selected) return;
    setLoadModal(lm => ({ ...lm, loading: true, error: null }));
    try {
      const loadResponse = await fetch(`${API_BASE_URL}/programs/${encodeURIComponent(loadModal.selected)}`);
      if (loadResponse.ok) {
        const programData = await loadResponse.json();
        setProgram(programData.program || []);
        setProgramStatus('idle');
        setSelectedLine(null);
        closeLoadModal();
      } else {
        const error = await loadResponse.json();
        setLoadModal(lm => ({ ...lm, loading: false, error: error.detail || 'Failed to load program.' }));
      }
    } catch (error) {
      setLoadModal(lm => ({ ...lm, loading: false, error: error.message }));
    }
  };

  const getStatusColor = () => {
    switch (programStatus) {
      case 'running': return '#007bff';
      case 'paused': return '#ffc107';
      case 'completed': return '#28a745';
      case 'error': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const getStatusText = () => {
    switch (programStatus) {
      case 'running': return `Running (${selectedLine !== null ? selectedLine + 1 : '-'}/${program.length})`;
      case 'paused': return `Paused (${selectedLine !== null ? selectedLine + 1 : '-'}/${program.length})`;
      case 'completed': return 'Completed';
      case 'error': return 'Error';
      default: return 'Ready';
    }
  };

  const cancelEditing = () => {
    setSelectedLine(null);
    setNewCommand({
      type: 'move',
      axis: 'x',
      distance: 0,
      speed: 2.0,
      delay: 0,
      position: 0,
      x_position: 0,
      y_position: 0,
      loop_count: 1,
      message_text: '',
      io_name: 'down',
      io_state: false
    });
  };

  return (
    <div className="program-builder">
      
      {/* Program Status */}
      <div className="program-status" style={{ borderColor: getStatusColor() }}>
        <h3>Status: {getStatusText()}</h3>
        {programStatus === 'running' && selectedLine !== null && (
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ 
                width: `${((selectedLine + 1) / program.length) * 100}%`,
                backgroundColor: getStatusColor()
              }}
            />
          </div>
        )}
      </div>
      
      {/* Add Command Form */}
      <div className="add-command-form">
        <h3>{selectedLine !== null ? `Edit Command #${selectedLine + 1}` : 'Add Command'}</h3>
        <div className="form-row">
          <select
            value={newCommand.type}
            onChange={(e) => setNewCommand({...newCommand, type: e.target.value})}
            disabled={estop}
          >
            <option value="move">Relative Move</option>
            <option value="move_to">Absolute Move</option>
            <option value="wait">Wait</option>
            <option value="loop">Loop</option>
            <option value="endloop">End Loop</option>
            <option value="message">Message</option>
            <option value="set_io">Set I/O</option>
          </select>
          
          {newCommand.type === 'move' && (
            <>
              <select
                value={newCommand.axis}
                onChange={(e) => setNewCommand({...newCommand, axis: e.target.value})}
                disabled={estop}
              >
                <option value="x">X Axis</option>
                <option value="y">Y Axis</option>
              </select>
              
              <input
                type="number"
                placeholder="Distance"
                value={newCommand.distance}
                onChange={(e) => setNewCommand({...newCommand, distance: parseFloat(e.target.value) || 0})}
                step="0.001"
                min="-10"
                max="10"
                disabled={estop}
              />
            </>
          )}

          {newCommand.type === 'move_to' && (
            <>
              <select
                value={newCommand.axis}
                onChange={(e) => setNewCommand({...newCommand, axis: e.target.value})}
                disabled={estop}
              >
                <option value="x">X Position</option>
                <option value="y">Y Position</option>
                <option value="xy">XY Movement</option>
              </select>
              
              {(newCommand.axis === 'x' || newCommand.axis === 'y') && (
                <input
                  type="number"
                  placeholder="Position (in)"
                  value={newCommand.position || ''}
                  onChange={(e) => setNewCommand({...newCommand, position: parseFloat(e.target.value) || 0})}
                  step="0.001"
                  min="0"
                  max={newCommand.axis === 'x' ? (tableLimits?.x_axis?.max || 10) : (tableLimits?.y_axis?.max || 10)}
                  disabled={estop}
                />
              )}
              
              {newCommand.axis === 'xy' && (
                <>
                  <input
                    type="number"
                    placeholder="X (in)"
                    value={newCommand.x_position || ''}
                    onChange={(e) => setNewCommand({...newCommand, x_position: parseFloat(e.target.value) || 0})}
                    step="0.001"
                    min="0"
                    max={tableLimits?.x_axis?.max || 10}
                    disabled={estop}
                  />
                  
                  <input
                    type="number"
                    placeholder="Y (in)"
                    value={newCommand.y_position || ''}
                    onChange={(e) => setNewCommand({...newCommand, y_position: parseFloat(e.target.value) || 0})}
                    step="0.001"
                    min="0"
                    max={tableLimits?.y_axis?.max || 10}
                    disabled={estop}
                  />
                </>
              )}
            </>
          )}
          

          
                        {newCommand.type === 'wait' && (
                <input
                  type="number"
                  placeholder="Delay (s)"
                  value={newCommand.delay}
                  onChange={(e) => setNewCommand({...newCommand, delay: parseFloat(e.target.value) || 1})}
                  min="0"
                  step="0.1"
                  disabled={estop}
                />
              )}
              
              {newCommand.type === 'loop' && (
                <input
                  type="number"
                  placeholder="Loop Count"
                  value={newCommand.loop_count || ''}
                  onChange={(e) => setNewCommand({...newCommand, loop_count: parseInt(e.target.value) || 0})}
                  min="1"
                  max="1000"
                  step="1"
                  disabled={estop}
                />
              )}
              
              {newCommand.type === 'message' && (
                <input
                  type="text"
                  placeholder="Message to display"
                  value={newCommand.message_text || ''}
                  onChange={(e) => setNewCommand({...newCommand, message_text: e.target.value})}
                  style={{ minWidth: '200px' }}
                  disabled={estop}
                />
              )}
              
              {newCommand.type === 'set_io' && (
                <>
                  <select
                    value={newCommand.io_name || 'down'}
                    onChange={(e) => setNewCommand({...newCommand, io_name: e.target.value})}
                    disabled={estop}
                  >
                    <option value="down">Down</option>
                    <option value="start">Start</option>
                  </select>
                  
                  <select
                    value={newCommand.io_state ? 'true' : 'false'}
                    onChange={(e) => setNewCommand({...newCommand, io_state: e.target.value === 'true'})}
                    disabled={estop}
                  >
                    <option value="true">ON</option>
                    <option value="false">OFF</option>
                  </select>
                </>
              )}
          
          <button
            onClick={addOrUpdateCommand}
            className={selectedLine !== null ? 'update-btn' : 'add-btn'}
            disabled={!connected || estop}
          >
            {selectedLine !== null ? 'Update Command' : 'Add Command'}
          </button>
          {selectedLine !== null && (
            <button onClick={cancelEditing} className="cancel-btn" disabled={estop}>
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Program List */}
      <div className="program-list">
        <div className="program-header">
          <h3>
            Program ({program.length} commands)
          </h3>
          <div className="program-actions">
            {selectedLine !== null && (
              <div className="line-actions">
                <button
                  onClick={() => moveCommand('up')}
                  disabled={selectedLine === 0 || estop}
                  className="move-btn"
                  title="Move Up"
                >
                  ↑ Move Up
                </button>
                <button
                  onClick={() => moveCommand('down')}
                  disabled={selectedLine === program.length - 1 || estop}
                  className="move-btn"
                  title="Move Down"
                >
                  ↓ Move Down
                </button>
                <button
                  onClick={insertCommand}
                  disabled={selectedLine === null || estop}
                  className="insert-btn"
                  title="Insert Above"
                >
                  Insert
                </button>
                <button
                  onClick={removeCommand}
                  className="remove-btn"
                  title="Remove Command"
                >
                  Remove
                </button>
              </div>
            )}
                        <div className="program-controls">
              {programStatus === 'running' ? (
                <>
                  <button onClick={pauseProgram} className="pause-btn" disabled={estop}>
                    Pause
                  </button>
                  <button onClick={stopProgram} className="stop-btn" disabled={estop}>
                    Stop
                  </button>
                </>
              ) : programStatus === 'paused' ? (
                <>
                  <button onClick={resumeProgram} className="resume-btn" disabled={estop}>
                    ▶ Resume
                  </button>
                  <button onClick={stopProgram} className="stop-btn" disabled={estop}>
                    Stop
                  </button>
                </>
              ) : (
                <>
                  <button 
                    onClick={executeProgram} 
                    disabled={program.length === 0 || !connected || loading || estop} 
                    className="execute-btn"
                    title={selectedLine !== null ? `Execute from line ${selectedLine + 1}` : 'Execute from beginning'}
                  >
                    ▶ Execute Program{selectedLine !== null ? ` (from line ${selectedLine + 1})` : ''}
                  </button>
                  {selectedLine !== null && (
                    <button 
                      onClick={() => executeSingleLine(selectedLine)}
                      disabled={!connected || loading || estop || executing}
                      className="execute-single-btn"
                      title={`Execute line ${selectedLine + 1}`}
                    >
                      ▶ Execute Line {selectedLine + 1}
                    </button>
                  )}
                </>
              )}
              <button onClick={clearProgram} disabled={program.length === 0 || estop} className="clear-btn">
                Clear
              </button>
              <button onClick={saveProgram} disabled={program.length === 0 || estop} className="save-btn">
                Save
              </button>
              <button onClick={openLoadModal} className="load-btn" disabled={estop}>
                Load
              </button>
            </div>
          </div>
        </div>
        
        <div className="command-list">
          {program.length === 0 ? (
            <div className="empty-program">
              No commands in program. Add some commands above.
            </div>
          ) : (
            program.map((command, index) => {
              // Generate single line text for each command
              let commandText = `#${command.step} `;
              
              switch (command.type) {
                case 'move':
                  commandText += `MOVE ${command.axis.toUpperCase()} ${command.distance > 0 ? '+' : ''}${command.distance}in @10in/s`;
                  break;
                case 'move_to':
                  if (command.axis === 'xy') {
                    commandText += `MOVE TO X:${command.x_position}in Y:${command.y_position}in @10in/s`;
                  } else {
                    commandText += `MOVE TO ${command.axis.toUpperCase()}:${command.position}in @10in/s`;
                  }
                  break;
                case 'wait':
                  commandText += `WAIT ${command.delay}s`;
                  break;
                case 'loop':
                  commandText += `LOOP ${command.loop_count} times`;
                  break;
                case 'endloop':
                  commandText += `END LOOP`;
                  break;
                case 'message':
                  commandText += `MESSAGE "${command.message_text}"`;
                  break;
                case 'set_io':
                  const ioDisplayName = command.io_name;
                  commandText += `SET ${ioDisplayName.toUpperCase()} ${command.io_state ? 'ON' : 'OFF'}`;
                  break;
                default:
                  //commandText += command.type.toUpperCase();
              }
              
              return (
                <div 
                  key={command.id} 
                  className={`command-item ${selectedLine === index ? 'selected-line' : ''}`}
                  onClick={() => handleLineSelect(index)}
                  style={{ cursor: (programStatus === 'running' || programStatus === 'paused') ? 'default' : 'pointer' }}
                >
                  <div className="command-text">
                    {commandText}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
      
      {/* Message Modal */}
      {messageModal.show && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Message</h3>
            <p>{messageModal.message}</p>
            <div className="modal-buttons">
              <button onClick={messageModal.onContinue} className="continue-btn">
                Continue
              </button>
              <button onClick={messageModal.onPause} className="pause-btn">
                Pause
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Load Program Modal */}
      {loadModal.show && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Load Program</h3>
            {loadModal.loading ? (
              <p>Loading...</p>
            ) : loadModal.error ? (
              <p style={{ color: '#ff3333' }}>{loadModal.error}</p>
            ) : (
              <>
                <div style={{ marginBottom: 16 }}>
                  <select
                    style={{ width: '100%', padding: 8, fontSize: '1rem' }}
                    value={loadModal.selected || ''}
                    onChange={e => setLoadModal(lm => ({ ...lm, selected: e.target.value }))}
                  >
                    {loadModal.programs.map(program => (
                      <option key={program.name} value={program.name}>{program.name}</option>
                    ))}
                  </select>
                </div>
                <div className="modal-buttons">
                  <button onClick={handleLoadProgram} className="continue-btn" disabled={!loadModal.selected || loadModal.loading}>
                    Open
                  </button>
                  <button onClick={closeLoadModal} className="cancel-btn" disabled={loadModal.loading}>
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProgramBuilder; 
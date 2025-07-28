import React, { useState, useRef, useEffect } from 'react';
import './XYVisualizer.css';

const XYVisualizer = ({ 
  onMoveTo,
  currentPosition = { x: 0, y: 0 }, 
  tableLimits = { x_axis: { min: 0, max: 107.95 }, y_axis: { min: 0, max: 79.375 } },
  connected = false,
  loading = false
}) => {
  const canvasRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [hoverPosition, setHoverPosition] = useState(null);
  const [selectedPosition, setSelectedPosition] = useState(null);
  const speed = 10; // Fixed speed value

  // Calculate canvas dimensions
  const canvasWidth = 400;
  const canvasHeight = 300;
  const margin = 30;

  // Get table dimensions from limits
  const tableDimensions = {
    width: tableLimits.x_axis.max,
    height: tableLimits.y_axis.max
  };

  // Convert table coordinates to canvas coordinates
  const tableToCanvas = (tablePos) => {
    const x = (tablePos.x / tableDimensions.width) * (canvasWidth - 2 * margin) + margin;
    const y = canvasHeight - margin - (tablePos.y / tableDimensions.height) * (canvasHeight - 2 * margin);
    return { x, y };
  };

  // Convert canvas coordinates to table coordinates
  const canvasToTable = (canvasPos) => {
    const x = ((canvasPos.x - margin) / (canvasWidth - 2 * margin)) * tableDimensions.width;
    const y = ((canvasHeight - margin - canvasPos.y) / (canvasHeight - 2 * margin)) * tableDimensions.height;
    return {
      x: Math.max(tableLimits.x_axis.min, Math.min(tableLimits.x_axis.max, x)),
      y: Math.max(tableLimits.y_axis.min, Math.min(tableLimits.y_axis.max, y))
    };
  };

  // Handle mouse events
  const handleMouseDown = (e) => {
    if (!connected || loading) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const tablePos = canvasToTable({ x, y });
    
    setIsDragging(true);
    setSelectedPosition(tablePos);
  };

  const handleMouseMove = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const tablePos = canvasToTable({ x, y });
    
    setHoverPosition(tablePos);
    
    if (isDragging && connected && !loading) {
      setSelectedPosition(tablePos);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
    setHoverPosition(null);
  };

  // Handle position selection and movement
  const handlePositionSelect = (position) => {
    if (!connected || loading) return;
    setSelectedPosition(position);
  };

  const handleMoveToPosition = () => {
    if (!connected || loading || !selectedPosition) return;
    onMoveTo(selectedPosition.x, selectedPosition.y, speed);
  };

  // Draw the visualization
  const drawCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    // Draw background
    ctx.fillStyle = '#1a0000';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Draw grid
    ctx.strokeStyle = '#cc0000';
    ctx.lineWidth = 1;
    
    // Vertical grid lines (every 10mm)
    for (let i = 0; i <= tableDimensions.width; i += 10) {
      const x = (i / tableDimensions.width) * (canvasWidth - 2 * margin) + margin;
      ctx.beginPath();
      ctx.moveTo(x, margin);
      ctx.lineTo(x, canvasHeight - margin);
      ctx.stroke();
    }
    
    // Horizontal grid lines (every 10mm)
    for (let i = 0; i <= tableDimensions.height; i += 10) {
      const y = canvasHeight - margin - (i / tableDimensions.height) * (canvasHeight - 2 * margin);
      ctx.beginPath();
      ctx.moveTo(margin, y);
      ctx.lineTo(canvasWidth - margin, y);
      ctx.stroke();
    }

    // Draw table boundary
    ctx.strokeStyle = '#cc0000';
    ctx.lineWidth = 2;
    ctx.strokeRect(margin, margin, canvasWidth - 2 * margin, canvasHeight - 2 * margin);

    // Draw coordinate labels
    ctx.fillStyle = '#cc0000';
    ctx.font = '10px Arial';
    ctx.textAlign = 'center';
    
    // X-axis labels (every 20mm)
    for (let i = 0; i <= tableDimensions.width; i += 20) {
      const x = (i / tableDimensions.width) * (canvasWidth - 2 * margin) + margin;
      ctx.fillText(`${i}`, x, canvasHeight - 8);
    }
    
    // Y-axis labels (every 20mm)
    for (let i = 0; i <= tableDimensions.height; i += 20) {
      const y = canvasHeight - margin - (i / tableDimensions.height) * (canvasHeight - 2 * margin);
      ctx.fillText(`${i}`, 15, y + 3);
    }

    // Draw current position
    const currentCanvasPos = tableToCanvas(currentPosition);
    ctx.fillStyle = '#cc0000';
    ctx.beginPath();
    ctx.arc(currentCanvasPos.x, currentCanvasPos.y, 6, 0, 2 * Math.PI);
    ctx.fill();
    
    // Draw current position label
    ctx.fillStyle = '#cc0000';
    ctx.font = 'bold 12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(`(${currentPosition.x.toFixed(1)}, ${currentPosition.y.toFixed(1)})`, 
                 currentCanvasPos.x, currentCanvasPos.y - 12);

    // Draw selected position
    if (selectedPosition) {
      const selectedCanvasPos = tableToCanvas(selectedPosition);
      ctx.strokeStyle = '#ff6600';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.arc(selectedCanvasPos.x, selectedCanvasPos.y, 12, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
      
      // Draw selected position label
      ctx.fillStyle = '#ff6600';
      ctx.font = 'bold 12px Arial';
      ctx.fillText(`(${selectedPosition.x.toFixed(1)}, ${selectedPosition.y.toFixed(1)})`, 
                   selectedCanvasPos.x, selectedCanvasPos.y - 25);
    }

    // Draw hover position
    if (hoverPosition && !isDragging && connected) {
      const hoverCanvasPos = tableToCanvas(hoverPosition);
      ctx.strokeStyle = '#00cc00';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.arc(hoverCanvasPos.x, hoverCanvasPos.y, 10, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
      
      // Draw hover position label
      ctx.fillStyle = '#00cc00';
      ctx.font = 'bold 10px Arial';
      ctx.fillText(`(${hoverPosition.x.toFixed(1)}, ${hoverPosition.y.toFixed(1)})`, 
                   hoverCanvasPos.x, hoverCanvasPos.y - 20);
    }

    // Draw axis labels
    ctx.fillStyle = '#cc0000';
    ctx.font = 'bold 12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('X Axis (in.)', canvasWidth / 2, canvasHeight - 10);
    
    ctx.save();
    ctx.translate(12, canvasHeight / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Y Axis (in.)', 0, 0);
    ctx.restore();
  };

  // Redraw canvas when dependencies change
  useEffect(() => {
    drawCanvas();
  }, [currentPosition, hoverPosition, selectedPosition, tableLimits, connected]);

  return (
    <div className="xy-visualizer">
      <h2>X-Y Table Visualizer</h2>
      
      <div className="visualization-container">
        <canvas
          ref={canvasRef}
          width={canvasWidth}
          height={canvasHeight}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseLeave}
          className="coordinate-system"
          style={{ 
            cursor: !connected || loading ? 'not-allowed' : isDragging ? 'grabbing' : 'crosshair',
            opacity: !connected ? 0.6 : 1
          }}
        />
      </div>
      
      {selectedPosition && (
        <div className="position-controls">
          <div className="position-display">
            New Position: X: {selectedPosition.x.toFixed(1)} in, Y: {selectedPosition.y.toFixed(1)} in
          </div>
          <div className="move-controls">
            <button 
              onClick={handleMoveToPosition}
              disabled={!connected || loading}
              className="move-btn"
            >
              {loading ? 'Moving...' : 'Move To Position'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default XYVisualizer; 
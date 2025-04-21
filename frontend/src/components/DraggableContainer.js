import React, { useState, useEffect, useRef, useCallback } from 'react';
import './DraggableContainer.css';

const DraggableContainer = ({ children }) => {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  const handleMouseDown = useCallback((e) => {
    setIsDragging(true);
    setStartPos({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  }, [position]);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    
    const newX = e.clientX - startPos.x;
    const newY = e.clientY - startPos.y;

    // Add boundaries to prevent dragging too far
    const maxX = window.innerWidth * 2;
    const maxY = window.innerHeight * 2;
    
    setPosition({
      x: Math.max(-maxX, Math.min(maxX, newX)),
      y: Math.max(-maxY, Math.min(maxY, newY))
    });
  }, [isDragging, startPos]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleTouchStart = useCallback((e) => {
    if (e.touches.length === 2) {
      setIsDragging(true);
      setStartPos({
        x: e.touches[0].clientX - position.x,
        y: e.touches[0].clientY - position.y
      });
    }
  }, [position]);

  const handleTouchMove = useCallback((e) => {
    if (!isDragging || e.touches.length !== 2) return;
    
    const newX = e.touches[0].clientX - startPos.x;
    const newY = e.touches[0].clientY - startPos.y;

    // Add boundaries to prevent dragging too far
    const maxX = window.innerWidth * 2;
    const maxY = window.innerHeight * 2;
    
    setPosition({
      x: Math.max(-maxX, Math.min(maxX, newX)),
      y: Math.max(-maxY, Math.min(maxY, newY))
    });
  }, [isDragging, startPos]);

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('mousedown', handleMouseDown);
    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseup', handleMouseUp);
    container.addEventListener('mouseleave', handleMouseUp);
    
    container.addEventListener('touchstart', handleTouchStart);
    container.addEventListener('touchmove', handleTouchMove);
    container.addEventListener('touchend', handleTouchEnd);

    return () => {
      container.removeEventListener('mousedown', handleMouseDown);
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseup', handleMouseUp);
      container.removeEventListener('mouseleave', handleMouseUp);
      
      container.removeEventListener('touchstart', handleTouchStart);
      container.removeEventListener('touchmove', handleTouchMove);
      container.removeEventListener('touchend', handleTouchEnd);
    };
  }, [handleMouseDown, handleMouseMove, handleMouseUp, handleTouchStart, handleTouchMove, handleTouchEnd]);

  return (
    <div 
      ref={containerRef}
      className={`draggable-container ${isDragging ? 'dragging' : ''}`}
      style={{
        transform: `translate(${position.x}px, ${position.y}px)`,
        cursor: isDragging ? 'grabbing' : 'grab'
      }}
    >
      {children}
    </div>
  );
};

export default DraggableContainer; 
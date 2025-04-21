import React, { useState, useEffect, useRef } from 'react';
import './MindMap.css';

const MindMap = ({ centralQuestion, concepts }) => {
  const [positions, setPositions] = useState({});
  const [draggedConcept, setDraggedConcept] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [activeNodes, setActiveNodes] = useState(concepts.map(() => true));
  const [expandedNodeIndex, setExpandedNodeIndex] = useState(null);
  const [expandedConcepts, setExpandedConcepts] = useState([]);
  const mapRef = useRef(null);
  const conceptRefs = useRef([]);
  const centralRef = useRef(null);

  // Initialize refs for concept nodes
  useEffect(() => {
    conceptRefs.current = Array(concepts.length).fill().map(() => React.createRef());
  }, [concepts.length]);

  // Initialize positions in a balanced layout
  useEffect(() => {
    if (Object.keys(positions).length === 0) {
      // Positions that match the reference image exactly
      const initialPositions = {
        'concept-0': { x: 0, y: -180 },      // Top
        'concept-1': { x: -280, y: 0 },      // Left
        'concept-2': { x: 280, y: 0 },       // Right
        'concept-3': { x: -180, y: 200 },    // Bottom Left
        'concept-4': { x: 180, y: 200 }      // Bottom Right
      };
      
      setPositions(initialPositions);
    }
  }, [positions]);

  // Expand a node with 5 new child nodes
  const expandNode = (index) => {
    console.log("Expanding node", index);
    setExpandedNodeIndex(index);
    
    // Create 5 new concept nodes with shorter names
    const newConcepts = [
      "Concept A",
      "Concept B", 
      "Concept C",
      "Concept D",
      "Concept E"
    ];
    
    setExpandedConcepts(newConcepts);
    
    // Create positions for the new nodes following the parent's side
    const parentPos = positions[`concept-${index}`];
    const newPositions = { ...positions };
    
    // Determine which side the parent node is on relative to the center
    // This uses the standard layout: top, left, right, bottom-left, bottom-right
    let direction;
    
    if (index === 0) {
      // Top node - place children above it
      direction = 'top';
    } else if (index === 1) {
      // Left node - place children to the left
      direction = 'left';
    } else if (index === 2) {
      // Right node - place children to the right
      direction = 'right';
    } else if (index === 3) {
      // Bottom Left node - place children below and to the left
      direction = 'bottom-left';
    } else if (index === 4) {
      // Bottom Right node - place children below and to the right
      direction = 'bottom-right';
    }
    
    console.log("Direction for expanded nodes:", direction);
    
    // Position nodes based on the parent's position/direction
    switch (direction) {
      case 'top':
        // Arrange horizontally above the parent
        for (let i = 0; i < newConcepts.length; i++) {
          const xOffset = (i - 2) * 120; // -240, -120, 0, 120, 240
          newPositions[`expanded-${index}-${i}`] = {
            x: parentPos.x + xOffset,
            y: parentPos.y - 150
          };
        }
        break;
        
      case 'left':
        // Arrange vertically to the left - increase spacing
        for (let i = 0; i < newConcepts.length; i++) {
          const yOffset = (i - 2) * 100; // -200, -100, 0, 100, 200
          newPositions[`expanded-${index}-${i}`] = {
            x: parentPos.x - 250,
            y: parentPos.y + yOffset
          };
        }
        break;
        
      case 'right':
        // Arrange vertically to the right - increase spacing
        for (let i = 0; i < newConcepts.length; i++) {
          const yOffset = (i - 2) * 100; // -200, -100, 0, 100, 200
          newPositions[`expanded-${index}-${i}`] = {
            x: parentPos.x + 250,
            y: parentPos.y + yOffset
          };
        }
        break;
        
      case 'bottom-left':
        // Arrange horizontally below and to the left
        for (let i = 0; i < newConcepts.length; i++) {
          const xOffset = (i - 2) * 120; // -240, -120, 0, 120, 240
          newPositions[`expanded-${index}-${i}`] = {
            x: parentPos.x - 100 + xOffset,
            y: parentPos.y + 150
          };
        }
        break;
        
      case 'bottom-right':
        // Arrange horizontally below and to the right
        for (let i = 0; i < newConcepts.length; i++) {
          const xOffset = (i - 2) * 120; // -240, -120, 0, 120, 240
          newPositions[`expanded-${index}-${i}`] = {
            x: parentPos.x + 100 + xOffset,
            y: parentPos.y + 150
          };
        }
        break;
    }
    
    setPositions(newPositions);
  };

  // Toggle node active state
  const toggleNodeActive = (index) => {
    // Count how many inactive nodes we currently have
    const inactiveCount = activeNodes.filter(active => !active).length;
    
    // If this node is already inactive, we can always make it active again
    if (!activeNodes[index]) {
      setActiveNodes(prev => {
        const newActive = [...prev];
        newActive[index] = true;
        return newActive;
      });
      // If we're activating a node, clear expansion
      if (expandedNodeIndex !== null) {
        setExpandedNodeIndex(null);
        setExpandedConcepts([]);
      }
      return;
    }
    
    // If this would be the 5th inactive node (all inactive), don't allow it
    if (inactiveCount === 4) {
      // Find the only remaining active node (which must be this one)
      const activeNodeIndices = activeNodes.map((active, i) => active ? i : -1).filter(i => i >= 0);
      if (activeNodeIndices.length === 1 && activeNodeIndices[0] === index) {
        console.log("Can't deactivate the last node");
        return;
      }
    }
    
    // Make this node inactive
    setActiveNodes(prev => {
      const newActive = [...prev];
      newActive[index] = false;
      return newActive;
    });
    
    // Check if we now have 4 inactive nodes (1 active)
    const newInactiveCount = inactiveCount + 1;
    if (newInactiveCount === 4) {
      // Find the one remaining active node
      const remainingActiveIndex = activeNodes.findIndex((active, i) => active && i !== index);
      if (remainingActiveIndex !== -1) {
        // Expand the remaining active node
        expandNode(remainingActiveIndex);
      }
    }
  };
  
  // Handle starting to drag a concept
  const handleMouseDown = (e, conceptId) => {
    e.preventDefault();
    e.stopPropagation();
    
    const rect = e.currentTarget.getBoundingClientRect();
    const mapRect = mapRef.current.getBoundingClientRect();
    
    setDraggedConcept(conceptId);
    setDragOffset({
      x: e.clientX - (rect.left - mapRect.left),
      y: e.clientY - (rect.top - mapRect.top)
    });
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  // Handle dragging a concept
  const handleMouseMove = (e) => {
    if (!draggedConcept) return;
    
    e.preventDefault();
    const mapRect = mapRef.current.getBoundingClientRect();
    const newX = e.clientX - mapRect.left - dragOffset.x;
    const newY = e.clientY - mapRect.top - dragOffset.y;

    setPositions(prev => ({
      ...prev,
      [draggedConcept]: { x: newX, y: newY }
    }));
  };

  // Handle dropping a concept
  const handleMouseUp = () => {
    setDraggedConcept(null);
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };

  // Render connection lines between central node and concepts
  const renderConnections = () => {
    const mapRect = mapRef.current?.getBoundingClientRect();
    const centralRect = centralRef.current?.getBoundingClientRect();
    
    if (!mapRect || !centralRect) return null;
    
    // The exact center of the central question box
    const centerX = mapRect.width / 2;
    const centerY = mapRect.height / 2;
    
    const connections = [];
    
    // Render connections to main concepts
    concepts.forEach((_, index) => {
      const pos = positions[`concept-${index}`];
      if (!pos) return;
      
      // Calculate the exact center position of the concept
      const conceptCenterX = centerX + pos.x;
      const conceptCenterY = centerY + pos.y;
      
      connections.push(
        <line
          key={`line-${index}`}
          x1={centerX}
          y1={centerY}
          x2={conceptCenterX}
          y2={conceptCenterY}
          className={activeNodes[index] ? 'connection' : 'connection inactive'}
        />
      );
      
      // If this is the expanded node, add connections to expanded concepts
      if (index === expandedNodeIndex) {
        expandedConcepts.forEach((_, i) => {
          const expandedPos = positions[`expanded-${index}-${i}`];
          if (!expandedPos) return;
          
          const expandedX = centerX + expandedPos.x;
          const expandedY = centerY + expandedPos.y;
          
          connections.push(
            <line
              key={`expanded-line-${index}-${i}`}
              x1={conceptCenterX}
              y1={conceptCenterY}
              x2={expandedX}
              y2={expandedY}
              className="connection expanded"
            />
          );
        });
      }
    });
    
    return connections;
  };

  // Console log for debugging
  console.log("Active nodes:", activeNodes);
  console.log("Expanded node index:", expandedNodeIndex);
  console.log("Expanded concepts:", expandedConcepts);
  console.log("Positions:", positions);

  return (
    <div className="mind-map-container">
      <div className="mind-map" ref={mapRef}>
        {/* SVG for the connections between nodes */}
        <svg className="connections">
          {mapRef.current && centralRef.current && renderConnections()}
        </svg>
        
        {/* Central Question Node */}
        <div className="central-question" ref={centralRef}>
          {centralQuestion}
        </div>
        
        {/* Concept Nodes */}
        {concepts.map((concept, index) => {
          const pos = positions[`concept-${index}`] || { x: 0, y: 0 };
          const isDragging = draggedConcept === `concept-${index}`;
          
          return (
            <div
              key={index}
              className={`concept ${!activeNodes[index] ? 'inactive' : ''} ${isDragging ? 'dragging' : ''} ${index === expandedNodeIndex ? 'expanded' : ''}`}
              style={{
                top: `calc(50% + ${pos.y}px)`,
                left: `calc(50% + ${pos.x}px)`,
                transform: 'translate(-50%, -50%)',
                cursor: isDragging ? 'grabbing' : 'grab'
              }}
              ref={conceptRefs.current[index]}
              onMouseDown={(e) => handleMouseDown(e, `concept-${index}`)}
              onClick={(e) => {
                e.stopPropagation();
                if (!draggedConcept) {
                  toggleNodeActive(index);
                }
              }}
            >
              {concept}
            </div>
          );
        })}
        
        {/* Expanded Concept Nodes */}
        {expandedNodeIndex !== null && expandedConcepts.map((concept, index) => {
          const pos = positions[`expanded-${expandedNodeIndex}-${index}`];
          if (!pos) return null;
          
          // Add debug border for visibility
          return (
            <div
              key={`expanded-${expandedNodeIndex}-${index}`}
              className="concept expanded-child"
              style={{
                top: `calc(50% + ${pos.y}px)`,
                left: `calc(50% + ${pos.x}px)`,
                transform: 'translate(-50%, -50%)',
                border: '2px solid #000'
              }}
            >
              {concept}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MindMap; 
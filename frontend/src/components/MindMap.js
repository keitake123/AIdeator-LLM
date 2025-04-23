import React, { useState, useEffect, useRef } from 'react';
import './MindMap.css';
import ConceptCard from './ConceptCard';

const MindMap = ({ centralQuestion, concepts }) => {
  const [positions, setPositions] = useState({});
  const [draggedConcept, setDraggedConcept] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [activeNodes, setActiveNodes] = useState(concepts.map(() => true));
  const [expandedNodeIndex, setExpandedNodeIndex] = useState(null);
  const [expandedConcepts, setExpandedConcepts] = useState([]);
  const [nodeSizes, setNodeSizes] = useState({});
  const [cards, setCards] = useState([]);
  const [nextCardId, setNextCardId] = useState(1);
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
    
    // Create 5 new concept nodes with titles and descriptions
    const newConcepts = [
      {
        title: "Fear of letting others down",
        description: "Social and professional pressures can make people fear judgment from peers."
      },
      {
        title: "Concept B",
        description: "A detailed description of concept B and its implications."
      },
      {
        title: "Concept C",
        description: "A detailed description of concept C and its implications."
      },
      {
        title: "Concept D",
        description: "A detailed description of concept D and its implications."
      },
      {
        title: "Concept E",
        description: "A detailed description of concept E and its implications."
      }
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
  
  // Helper function to get precise DOM positions of nodes
  const getNodePosition = (nodeId) => {
    const node = document.querySelector(`[data-node-id="${nodeId}"]`);
    const map = mapRef.current;
    
    if (!node || !map) return null;
    
    const nodeRect = node.getBoundingClientRect();
    const mapRect = map.getBoundingClientRect();
    
    return {
      x: nodeRect.left + nodeRect.width / 2 - mapRect.left,
      y: nodeRect.top + nodeRect.height / 2 - mapRect.top,
      width: nodeRect.width,
      height: nodeRect.height,
    };
  };
  
  // Helper function to calculate intersection points between line and node
  const getIntersection = (target, source, nodeSize) => {
    const dx = source.x - target.x;
    const dy = source.y - target.y;
    
    const w = nodeSize.width / 2;
    const h = nodeSize.height / 2;
    
    if (dx === 0 && dy === 0) return source;
    
    const absDX = Math.abs(dx);
    const absDY = Math.abs(dy);
    const scale = Math.min(w / absDX, h / absDY);
    
    return {
      x: source.x - dx * scale,
      y: source.y - dy * scale
    };
  };
  
  // Render connections between nodes using SVG and DOM positions
  const renderConnections = () => {
    if (!mapRef.current) return null;
    
    return (
      <svg className="connections" style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 1,
        overflow: 'visible'
      }}>
        {/* Main lines - from central node to concept nodes */}
        {concepts.map((_, index) => {
          const centralPos = getNodePosition('central');
          const conceptPos = getNodePosition(`concept-${index}`);
          
          if (!centralPos || !conceptPos) return null;
          
          const centralIntersect = getIntersection(conceptPos, centralPos, centralPos);
          const conceptIntersect = getIntersection(centralPos, conceptPos, conceptPos);
          
          return (
            <line
              key={`line-${index}`}
              x1={centralIntersect.x}
              y1={centralIntersect.y}
              x2={conceptIntersect.x}
              y2={conceptIntersect.y}
              stroke="#888"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray={activeNodes[index] ? "none" : "5,5"}
              opacity={activeNodes[index] ? 1 : 0.7}
            />
          );
        })}
        
        {/* Expanded node connections - from parent node to expanded children */}
        {expandedNodeIndex !== null && expandedConcepts.map((_, i) => {
          const parentPos = getNodePosition(`concept-${expandedNodeIndex}`);
          const childPos = getNodePosition(`expanded-${expandedNodeIndex}-${i}`);
          
          if (!parentPos || !childPos) return null;
          
          const parentIntersect = getIntersection(childPos, parentPos, parentPos);
          const childIntersect = getIntersection(parentPos, childPos, childPos);
          
          return (
            <line
              key={`expanded-line-${expandedNodeIndex}-${i}`}
              x1={parentIntersect.x}
              y1={parentIntersect.y}
              x2={childIntersect.x}
              y2={childIntersect.y}
              stroke="#888"
              strokeWidth="2"
              strokeLinecap="round"
            />
          );
        })}
      </svg>
    );
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

    // Update position in state
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

  // Use useEffect to observe node sizes and trigger redraws
  useEffect(() => {
    const resizeObserver = new ResizeObserver(() => {
      // Force a re-render to update connections by making a shallow
      // copy of the positions state
      setPositions(prev => ({ ...prev }));
    });
    
    const observeNodes = () => {
      // Central Node
      if (centralRef.current) {
        centralRef.current.setAttribute('data-node-id', 'central');
        resizeObserver.observe(centralRef.current);
      }
    
      // Concept Nodes
      conceptRefs.current.forEach((ref, index) => {
        if (ref.current) {
          ref.current.setAttribute('data-node-id', `concept-${index}`);
          resizeObserver.observe(ref.current);
        }
      });
    
      // Expanded Nodes
      document.querySelectorAll('.expanded-child').forEach((node) => {
        const nodeId = node.getAttribute('data-node-id');
        if (nodeId) resizeObserver.observe(node);
      });
    };
    
    // Wait a tick for DOM to update
    setTimeout(observeNodes, 0);
    
    return () => resizeObserver.disconnect();
  }, [positions, expandedConcepts]);

  // Use useEffect to track size changes
  useEffect(() => {
    const resizeObserver = new ResizeObserver(entries => {
      setNodeSizes(prev => {
        const newSizes = { ...prev };
        entries.forEach(entry => {
          const nodeId = entry.target.getAttribute('data-node-id');
          if (nodeId) {
            newSizes[nodeId] = {
              width: entry.contentRect.width,
              height: entry.contentRect.height
            };
          }
        });
        return newSizes;
      });
    });
    
    const observeNodes = () => {
      // Central Node
      if (centralRef.current) {
        centralRef.current.setAttribute('data-node-id', 'central');
        resizeObserver.observe(centralRef.current);
      }
    
      // Concept Nodes
      conceptRefs.current.forEach((ref, index) => {
        if (ref.current) {
          ref.current.setAttribute('data-node-id', `concept-${index}`);
          resizeObserver.observe(ref.current);
        }
      });
    
      // Expanded Nodes
      document.querySelectorAll('.expanded-child').forEach((node) => {
        const nodeId = node.getAttribute('data-node-id');
        if (nodeId) resizeObserver.observe(node);
      });
    };
    
    // Wait for DOM to be ready
    setTimeout(observeNodes, 0);
    
    return () => resizeObserver.disconnect();
  }, [conceptRefs.current.length, expandedNodeIndex, expandedConcepts]);

  // Force connections to update after DOM changes
  useEffect(() => {
    // Force a redraw after the DOM has fully updated
    const timer = setTimeout(() => {
      setPositions(prev => ({ ...prev }));
    }, 50);
    
    return () => clearTimeout(timer);
  }, [nodeSizes]);

  // Handle adding a new card
  const handleAddCard = (sourceNodeId) => {
    const sourcePos = positions[sourceNodeId] || { x: 0, y: 0 };
    
    // Place new card 120px to the right of source card
    const newCard = {
      id: `card-${nextCardId}`,
      title: "New Concept",
      description: "Add a description...",
      x: sourcePos.x + 120,
      y: sourcePos.y,
      type: 'concept'
    };

    setCards(prevCards => [...prevCards, newCard]);
    setNextCardId(prevId => prevId + 1);
    
    setPositions(prev => ({
      ...prev,
      [newCard.id]: { x: newCard.x, y: newCard.y }
    }));
  };

  // Handle expanding a card (generating insights)
  const handleExpandCard = (sourceNodeId) => {
    const sourcePos = positions[sourceNodeId] || { x: 0, y: 0 };
    
    // Place insight card 120px below source card
    const newCard = {
      id: `card-${nextCardId}`,
      title: "Generated Insight",
      description: "This is an AI-generated insight based on the source concept...",
      x: sourcePos.x+120,
      y: sourcePos.y,
      type: 'insight'
    };

    setCards(prevCards => [...prevCards, newCard]);
    setNextCardId(prevId => prevId + 1);
    
    setPositions(prev => ({
      ...prev,
      [newCard.id]: { x: newCard.x, y: newCard.y }
    }));
  };

  // Handle editing a card
  const handleEditCard = (nodeId, newTitle, newDescription) => {
    setCards(prevCards =>
      prevCards.map(card =>
        card.id === nodeId
          ? { ...card, title: newTitle, description: newDescription }
          : card
      )
    );
  };

  // Handle deleting a card
  const handleDeleteCard = (nodeId) => {
    setCards(prevCards => prevCards.filter(card => card.id !== nodeId));
    setPositions(prev => {
      const newPositions = { ...prev };
      delete newPositions[nodeId];
      return newPositions;
    });
  };

  return (
    <div className="mind-map-container">
      <div className="mind-map" ref={mapRef}>
        {/* SVG connections */}
        {renderConnections()}
        
        {/* Central Question Node */}
        <div 
          className="central-question" 
          ref={centralRef}
          data-node-id="central"
          style={{ borderColor: "#888" }}
        >
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
                cursor: isDragging ? 'grabbing' : 'grab',
                borderColor: "#888"
              }}
              ref={conceptRefs.current[index]}
              data-node-id={`concept-${index}`}
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
          
          const nodeId = `expanded-${expandedNodeIndex}-${index}`;
          
          return (
            <ConceptCard
              key={nodeId}
              nodeId={nodeId}
              title={concept.title}
              description={concept.description}
              style={{
                top: `calc(50% + ${pos.y}px)`,
                left: `calc(50% + ${pos.x}px)`,
                border: '2px solid #888'
              }}
              onAdd={handleAddCard}
              onExpand={handleExpandCard}
              onEdit={handleEditCard}
              onDelete={handleDeleteCard}
            />
          );
        })}
        
        {/* Dynamic cards */}
        {cards.map(card => {
          const pos = positions[card.id] || { x: 0, y: 0 };
          const isDragging = draggedConcept === card.id;
          
          return (
            <ConceptCard
              key={card.id}
              nodeId={card.id}
              title={card.title}
              description={card.description}
              style={{
                top: `calc(50% + ${pos.y}px)`,
                left: `calc(50% + ${pos.x}px)`,
                cursor: isDragging ? 'grabbing' : 'grab',
                borderColor: card.type === 'insight' ? "#4CAF50" : "#888"
              }}
              onAdd={handleAddCard}
              onExpand={handleExpandCard}
              onEdit={handleEditCard}
              onDelete={handleDeleteCard}
            />
          );
        })}
      </div>
    </div>
  );
};

export default MindMap; 
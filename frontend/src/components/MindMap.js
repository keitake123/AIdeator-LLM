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
        {/* Main lines - from central node to original concept nodes */}
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
        
        {/* Connections for dynamically added cards - always connect to main concept nodes */}
        {cards.map(card => {
          // Always get the main concept node as the source
          const mainConceptNodeId = card.mainConceptNodeId || 'concept-3'; // Default to concept-3 if not specified
          
          const conceptPos = getNodePosition(mainConceptNodeId);
          const cardPos = getNodePosition(card.id);
          
          if (!conceptPos || !cardPos) return null;
          
          const conceptIntersect = getIntersection(cardPos, conceptPos, conceptPos);
          const cardIntersect = getIntersection(conceptPos, cardPos, cardPos);
          
          return (
            <line
              key={`card-line-${card.id}`}
              x1={conceptIntersect.x}
              y1={conceptIntersect.y}
              x2={cardIntersect.x}
              y2={cardIntersect.y}
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

  // Helper function to check if a position would cause an overlap with existing nodes
  const wouldOverlap = (newPos, nodeWidth = 250, nodeHeight = 120, minDistance = 20) => {
    // Check for overlaps with concept nodes
    for (let i = 0; i < concepts.length; i++) {
      const pos = positions[`concept-${i}`] || { x: 0, y: 0 };
      
      // Calculate distance between centers
      const dx = Math.abs(newPos.x - pos.x);
      const dy = Math.abs(newPos.y - pos.y);
      
      // Check if the nodes would overlap (with minimum spacing between them)
      if (dx < (nodeWidth + minDistance) / 2 && dy < (nodeHeight + minDistance) / 2) {
        return true;
      }
    }
    
    // Check for overlaps with expanded nodes
    if (expandedNodeIndex !== null) {
      for (let i = 0; i < expandedConcepts.length; i++) {
        const pos = positions[`expanded-${expandedNodeIndex}-${i}`];
        if (!pos) continue;
        
        const dx = Math.abs(newPos.x - pos.x);
        const dy = Math.abs(newPos.y - pos.y);
        
        if (dx < (nodeWidth + minDistance) / 2 && dy < (nodeHeight + minDistance) / 2) {
          return true;
        }
      }
    }
    
    // Check for overlaps with existing cards
    for (const card of cards) {
      const pos = positions[card.id];
      if (!pos) continue;
      
      const dx = Math.abs(newPos.x - pos.x);
      const dy = Math.abs(newPos.y - pos.y);
      
      if (dx < (nodeWidth + minDistance) / 2 && dy < (nodeHeight + minDistance) / 2) {
        return true;
      }
    }
    
    // Check for overlap with central node
    const centralNodeSize = { width: 200, height: 120 }; // Approximate central node size
    if (Math.abs(newPos.x) < (centralNodeSize.width + minDistance) / 2 && 
        Math.abs(newPos.y) < (centralNodeSize.height + minDistance) / 2) {
      return true;
    }
    
    return false;
  };

  // Find a non-overlapping position near the given source position
  const findNonOverlappingPosition = (sourcePos, preferredDirection = 'right') => {
    // First try the preferred direction
    let newPos = { 
      x: sourcePos.x + (preferredDirection === 'right' ? 180 : preferredDirection === 'left' ? -180 : 0),
      y: sourcePos.y + (preferredDirection === 'down' ? 150 : preferredDirection === 'up' ? -150 : 0)
    };
    
    // If the preferred direction doesn't overlap, use it
    if (!wouldOverlap(newPos)) {
      return newPos;
    }
    
    // Otherwise, try different directions and distances in a spiral pattern
    const directions = ['right', 'down', 'left', 'up'];
    const distances = [180, 220, 260, 300, 340];
    
    for (const distance of distances) {
      for (const direction of directions) {
        newPos = {
          x: sourcePos.x + (direction === 'right' ? distance : direction === 'left' ? -distance : 0),
          y: sourcePos.y + (direction === 'down' ? distance : direction === 'up' ? -distance : 0)
        };
        
        if (!wouldOverlap(newPos)) {
          return newPos;
        }
        
        // Try diagonal positions too
        if (direction === 'right' || direction === 'left') {
          for (const vertDir of ['up', 'down']) {
            const vertDist = distance * 0.7;
            newPos = {
              x: sourcePos.x + (direction === 'right' ? distance : -distance),
              y: sourcePos.y + (vertDir === 'down' ? vertDist : -vertDist)
            };
            
            if (!wouldOverlap(newPos)) {
              return newPos;
            }
          }
        }
      }
    }
    
    // If we couldn't find a non-overlapping position, return a position far away as last resort
    return {
      x: sourcePos.x + 400,
      y: sourcePos.y + 300
    };
  };

  // Get the bottom-most position of all nodes to place new nodes below
  const getBottomPosition = () => {
    let maxY = -1000; // Start with a low value
    let nodeX = 0; // Default X position

    // Check concept nodes
    for (let i = 0; i < concepts.length; i++) {
      const pos = positions[`concept-${i}`] || { x: 0, y: 0 };
      if (pos.y > maxY) {
        maxY = pos.y;
        nodeX = pos.x; // Remember x position of the lowest node
      }
    }

    // Check expanded nodes
    if (expandedNodeIndex !== null) {
      for (let i = 0; i < expandedConcepts.length; i++) {
        const pos = positions[`expanded-${expandedNodeIndex}-${i}`];
        if (pos && pos.y > maxY) {
          maxY = pos.y;
          nodeX = pos.x;
        }
      }
    }

    // Check cards
    for (const card of cards) {
      const pos = positions[card.id];
      if (pos && pos.y > maxY) {
        maxY = pos.y;
        nodeX = pos.x;
      }
    }

    // If we don't have any nodes yet, place at default position
    if (maxY === -1000) {
      return { x: 0, y: 200 };
    }

    // Return a position below the bottom-most node with a spacing of 180px
    return { 
      x: nodeX,
      y: maxY + 180 
    };
  };

  // Handle adding a new card
  const handleAddCard = (sourceNodeId) => {
    // Always connect to a main concept node, regardless of the source
    // Extract the concept index if source is a main concept, otherwise use Concept 3 as default
    let mainConceptNodeId = 'concept-3'; // Default to Concept 3 if we can't determine
    
    if (sourceNodeId.startsWith('concept-')) {
      // If source is already a main concept node, use it
      mainConceptNodeId = sourceNodeId;
    } else if (sourceNodeId.startsWith('expanded-')) {
      // If source is an expanded node, get its parent concept
      const parts = sourceNodeId.split('-');
      if (parts.length >= 2) {
        mainConceptNodeId = `concept-${parts[1]}`;
      }
    } else if (sourceNodeId.startsWith('card-')) {
      // If source is a card, get its parent concept from the stored data
      const sourceCard = cards.find(card => card.id === sourceNodeId);
      if (sourceCard && sourceCard.mainConceptNodeId) {
        mainConceptNodeId = sourceCard.mainConceptNodeId;
      }
    }
    
    // Get position below all existing nodes
    const newPos = getBottomPosition();
    
    // Create the new card
    const newCard = {
      id: `card-${nextCardId}`,
      title: "New Concept",
      description: "Add a description...",
      x: newPos.x,
      y: newPos.y,
      type: 'concept',
      sourceNodeId: sourceNodeId, // Store immediate parent for positioning
      mainConceptNodeId: mainConceptNodeId // Store main concept for connections
    };

    setCards(prevCards => [...prevCards, newCard]);
    setNextCardId(prevId => prevId + 1);
    
    setPositions(prev => ({
      ...prev,
      [newCard.id]: { x: newPos.x, y: newPos.y }
    }));
  };

  // Handle expanding a card (generating insights)
  const handleExpandCard = (sourceNodeId) => {
    // Always connect to a main concept node, regardless of the source
    // Extract the concept index if source is a main concept, otherwise use Concept 3 as default
    let mainConceptNodeId = 'concept-3'; // Default to Concept 3 if we can't determine
    
    if (sourceNodeId.startsWith('concept-')) {
      // If source is already a main concept node, use it
      mainConceptNodeId = sourceNodeId;
    } else if (sourceNodeId.startsWith('expanded-')) {
      // If source is an expanded node, get its parent concept
      const parts = sourceNodeId.split('-');
      if (parts.length >= 2) {
        mainConceptNodeId = `concept-${parts[1]}`;
      }
    } else if (sourceNodeId.startsWith('card-')) {
      // If source is a card, get its parent concept from the stored data
      const sourceCard = cards.find(card => card.id === sourceNodeId);
      if (sourceCard && sourceCard.mainConceptNodeId) {
        mainConceptNodeId = sourceCard.mainConceptNodeId;
      }
    }
    
    // Get position below all existing nodes
    const newPos = getBottomPosition();
    
    // Adjust the x position a bit to the right to distinguish insight nodes
    newPos.x += 80;
    
    // Create the new card
    const newCard = {
      id: `card-${nextCardId}`,
      title: "Generated Insight",
      description: "This is an AI-generated insight based on the source concept...",
      x: newPos.x,
      y: newPos.y,
      type: 'insight',
      sourceNodeId: sourceNodeId, // Store immediate parent for positioning
      mainConceptNodeId: mainConceptNodeId // Store main concept for connections
    };

    setCards(prevCards => [...prevCards, newCard]);
    setNextCardId(prevId => prevId + 1);
    
    setPositions(prev => ({
      ...prev,
      [newCard.id]: { x: newPos.x, y: newPos.y }
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
              onMouseDown={(e) => handleMouseDown(e, nodeId)}
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
              onMouseDown={(e) => handleMouseDown(e, card.id)}
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
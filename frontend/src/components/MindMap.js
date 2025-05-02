import React, { useState, useEffect, useRef } from 'react';
import './MindMap.css';
import ConceptCard from './ConceptCard';

const MindMap = ({ centralQuestion, concepts }) => {
  const [positions, setPositions] = useState({});
  const [draggedConcept, setDraggedConcept] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [activeNodes, setActiveNodes] = useState(concepts.map(() => true));
  const [expandedNodeIndex, setExpandedNodeIndex] = useState(null);
  const [expandedParentConceptIndex, setExpandedParentConceptIndex] = useState(null);
  const [expandedConcepts, setExpandedConcepts] = useState([]);
  const [nodeSizes, setNodeSizes] = useState({});
  const [cards, setCards] = useState([]);
  const [nextCardId, setNextCardId] = useState(1);
  const mapRef = useRef(null);
  const conceptRefs = useRef([]);
  const centralRef = useRef(null);
  const [mergeMode, setMergeMode] = useState(false);
  const [selectedForMerge, setSelectedForMerge] = useState([]);

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
    setExpandedParentConceptIndex(index);
    
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
        
        {/* Connections for cards (both normal and merged) */}
        {cards.map(card => {
          if (card.mergedFrom && Array.isArray(card.mergedFrom)) {
            // Handle merged cards - connect to each source node
            return card.mergedFrom.map((sourceId, i) => {
              // Skip if the source is a card that was deleted during merge
              if (sourceId.startsWith('card-') && !cards.some(c => c.id === sourceId)) {
                return null;
              }
              
              const sourcePos = getNodePosition(sourceId);
              const targetPos = getNodePosition(card.id);
              
              if (!sourcePos || !targetPos) return null;
              
              const sourceIntersect = getIntersection(targetPos, sourcePos, sourcePos);
              const targetIntersect = getIntersection(sourcePos, targetPos, targetPos);
              
              return (
                <line
                  key={`merged-line-${card.id}-${i}`}
                  x1={sourceIntersect.x}
                  y1={sourceIntersect.y}
                  x2={targetIntersect.x}
                  y2={targetIntersect.y}
                  stroke="#1a73e8"
                  strokeWidth="2"
                  strokeDasharray="5,5"
                  style={{ pointerEvents: 'none' }}
                />
              );
            });
          } else {
            // Regular card - connect to main concept
            const mainConceptNodeId = card.mainConceptNodeId || 'concept-3'; // Default to concept-3 if not specified
            
            // Skip if disconnected
            if (!card.mainConceptNodeId) return null;
            
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
          }
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
  const findNonOverlappingPosition = (sourcePos, nodeWidth = 250, nodeHeight = 120, minDistance = 20) => {
    // Try original position
    if (!wouldOverlap(sourcePos, nodeWidth, nodeHeight, minDistance)) {
      return sourcePos;
    }

    // Try stacking downward in fixed vertical steps, preserving X
    for (let i = 1; i <= 10; i++) {
      const testPos = {
        x: sourcePos.x,
        y: sourcePos.y + i * (nodeHeight + minDistance)
      };
      if (!wouldOverlap(testPos, nodeWidth, nodeHeight, minDistance)) {
        return testPos;
      }
    }

    // If vertical stacking fails, try nudging slightly left/right (but preserve vertical alignment)
    const xOffsets = [-30, 30, -60, 60];
    for (let dx of xOffsets) {
      const testPos = {
        x: sourcePos.x + dx,
        y: sourcePos.y + (nodeHeight + minDistance)
      };
      if (!wouldOverlap(testPos, nodeWidth, nodeHeight, minDistance)) {
        return testPos;
      }
    }

    // Fallback far below
    return {
      x: sourcePos.x,
      y: sourcePos.y + 400
    };
  };

  const getBottomPosition = (sourceNodeId) => {
    let maxY = -1000;
    let xSum = 0;
    let count = 0;

    let relevantKeys = Object.keys(positions);

    // Handle expanded node groups
    if (sourceNodeId && sourceNodeId.startsWith('expanded-')) {
      const prefix = sourceNodeId.split('-').slice(0, 2).join('-'); // e.g. 'expanded-2'
      relevantKeys = relevantKeys.filter(key => key.startsWith(prefix));

      // Calculate average X and max Y for the group
      for (const key of relevantKeys) {
        const pos = positions[key];
        if (pos) {
          maxY = Math.max(maxY, pos.y);
          xSum += pos.x;
          count++;
        }
      }

      const avgX = count > 0 ? xSum / count : 0;

      return {
        x: avgX,
        y: maxY + 150 // Consistent vertical spacing
      };
    }

    // If we have a specific source node, place below it
    if (sourceNodeId && positions[sourceNodeId]) {
      const sourcePos = positions[sourceNodeId];
      return {
        x: sourcePos.x,
        y: sourcePos.y + 150 // Place directly below the source
      };
    }

    // Fallback for non-expanded nodes without a specific source
    for (const key of relevantKeys) {
      const pos = positions[key];
      if (pos && pos.y > maxY) {
        maxY = pos.y;
      }
    }

    return {
      x: 0, // Center position for non-grouped nodes
      y: maxY + 150
    };
  };

  const handleAddCard = (sourceNodeId) => {
    const newCardId = `card-${nextCardId}`;
    
    // Get position based on source node's group
    const newPos = getBottomPosition(sourceNodeId);
    
    // Check for overlaps and adjust if needed
    const finalPos = findNonOverlappingPosition(newPos);
    
    // Determine the main concept to connect to
    const mainConceptNodeId = `concept-${expandedParentConceptIndex ?? 3}`;
    
    setPositions(prev => ({
      ...prev,
      [newCardId]: finalPos
    }));

    setCards(prev => [...prev, {
      id: newCardId,
      title: 'New Concept',
      description: 'Add a description...',
      sourceNodeId, // Store the immediate parent for positioning
      mainConceptNodeId, // Store the main concept for connections
      noIcons: false // Default to noIcons: false
    }]);

    setNextCardId(prev => prev + 1);
  };

  // Special function to position merged nodes far to the left
  const positionMergedNode = (selectedNodeIds) => {
    const nodePositions = selectedNodeIds.map(id => positions[id]).filter(Boolean);

    if (nodePositions.length < 2) {
      return getBottomPosition(selectedNodeIds[0] || 'concept-0');
    }

    // Compute the bounding box of the selected nodes
    const minX = Math.min(...nodePositions.map(p => p.x));
    const maxY = Math.max(...nodePositions.map(p => p.y));
    const minY = Math.min(...nodePositions.map(p => p.y));
    const avgY = (minY + maxY) / 2;

    // Always place merged node to the left, aligned vertically to center
    let target = {
      x: minX - 300,      // Position to the left
      y: avgY             // Vertically centered
    };

    let tries = 0;
    while (wouldOverlap(target) && tries < 5) {
      target.x -= 40;     // Push further left
      tries++;
    }

    return target;
  };

  // Handle expanding a card (generating insights)
  const handleExpandCard = (sourceNodeId) => {
    // Get source node position from positions state
    const sourcePos = positions[sourceNodeId];
    if (!sourcePos) return; // Exit early if the position doesn't exist yet
    
    // Position the new node directly to the left of the source node
    const newPos = {
      x: sourcePos.x - 300,  // Move to the left
      y: sourcePos.y         // Same vertical position
    };
    
    // Create the new card
    const newCardId = `card-${nextCardId}`;
    const newCard = {
      id: newCardId,
      title: "Enter idea title",
      description: "",
      sourceNodeId: sourceNodeId,
      mainConceptNodeId: null,  // No connection
      isExpandable: true,
      noIcons: true              // Disables the hover icon options
    };

    setCards(prevCards => [...prevCards, newCard]);
    setNextCardId(prev => prev + 1);
    
    // Use exact position without overlap adjustments
    setPositions(prev => ({
      ...prev,
      [newCardId]: newPos  // Direct positioning without adjustments
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

  // Add function to check if node is mergeable
  const isMergeable = (nodeId) => {
    // Allow merging only for expanded nodes and additional cards
    return nodeId.startsWith('expanded-') || nodeId.startsWith('card-');
  };

  // Handle toggling merge mode for a node
  const handleToggleMergeMode = (nodeId) => {
    if (!isMergeable(nodeId)) return;

    setSelectedForMerge(prev => {
      // If already selected, remove it
      if (prev.includes(nodeId)) {
        return prev.filter(id => id !== nodeId);
      }
      // If not selected, add it
      return [...prev, nodeId];
    });
  };

  // Handle clicking on a card when in merge mode
  const handleCardClick = (nodeId) => {
    if (mergeMode && isMergeable(nodeId)) {
      handleToggleMergeMode(nodeId);
    }
  };

  // Handle merging selected nodes
  const handleMergeNodes = () => {
    if (selectedForMerge.length < 2) return;

    const nodesToMerge = selectedForMerge.map(nodeId => {
      // First check in cards
      const card = cards.find(c => c.id === nodeId);
      if (card) return { title: card.title, description: card.description };

      // Then check in expanded concepts
      const [_, conceptIndex, childIndex] = nodeId.split('-');
      const concept = expandedConcepts?.[Number(childIndex)];
      if (concept) return { title: concept.title, description: concept.description };

      return { title: "Unknown", description: "" };
    });

    const mergedTitle = "Merged Concept";
    const mergedDescription = nodesToMerge
      .map(node => `${node.title}: ${node.description}`)
      .join('\n\n');

    // Create new merged card
    const newCardId = `card-${nextCardId}`;
    
    // Use specialized function to position merged nodes
    const finalPosition = positionMergedNode(selectedForMerge);

    setCards(prev => [...prev, {
      id: newCardId,
      title: mergedTitle,
      description: mergedDescription,
      isMerged: true,
      mergedFrom: [...selectedForMerge],
      mergedCount: selectedForMerge.length,
      sourceNodes: nodesToMerge.map((node, index) => ({
        title: node.title,
        description: node.description,
        originalId: selectedForMerge[index],
        position: positions[selectedForMerge[index]] // Store original positions for triangle formation
      })),
      mergeDirection: 'left', // Always positioned to the left
      isExpandable: false,
      isMerged: true,
      noIcons: false // Default to noIcons: false
    }]);

    // Set position for new merged card
    setPositions(prev => ({
      ...prev,
      [newCardId]: finalPosition
    }));

    // Only delete dynamic cards, leave expanded concepts untouched
    selectedForMerge.forEach(nodeId => {
      if (nodeId.startsWith('card-')) {
        handleDeleteCard(nodeId);
      }
    });

    // Reset merge state
    setSelectedForMerge([]);
    setMergeMode(false);
    setNextCardId(prev => prev + 1);
  };

  // Add a function to cancel merge mode
  const cancelMergeMode = () => {
    setSelectedForMerge([]);
    setMergeMode(false);
  };

  // Add keyboard handlers for merge operations
  useEffect(() => {
    if (selectedForMerge.length < 2) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleMergeNodes();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        cancelMergeMode();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedForMerge]); // Note: You might need to add other dependencies based on your linter

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
              isSelectedForMerge={selectedForMerge.includes(nodeId)}
              onToggleMergeMode={() => handleToggleMergeMode(nodeId)}
              onClick={() => handleCardClick(nodeId)}
            />
          );
        })}
        
        {/* Dynamic cards */}
        {cards.map(card => {
          const pos = positions[card.id] || { x: 0, y: 0 };
          
          return (
            <ConceptCard
              key={card.id}
              nodeId={card.id}
              title={card.title}
              description={card.description}
              style={{
                top: `calc(50% + ${pos.y}px)`,
                left: `calc(50% + ${pos.x}px)`,
              }}
              onMouseDown={(e) => handleMouseDown(e, card.id)}
              onAdd={handleAddCard}
              onExpand={handleExpandCard}
              onEdit={handleEditCard}
              onDelete={handleDeleteCard}
              isSelectedForMerge={selectedForMerge.includes(card.id)}
              onToggleMergeMode={() => handleToggleMergeMode(card.id)}
              onClick={() => handleCardClick(card.id)}
              isMerged={card.isMerged}
              mergedCount={card.mergedCount}
              sourceNodes={card.sourceNodes}
              isExpandable={card.isExpandable}
              noIcons={card.noIcons}
            />
          );
        })}
      </div>
      
      {/* Updated merge controls with keyboard hints */}
      {selectedForMerge.length >= 2 && (
        <div className="merge-controls">
          <div className="merge-controls-content">
            <button 
              className="merge-button"
              onClick={handleMergeNodes}
            >
              Merge {selectedForMerge.length} nodes
            </button>
            <button 
              className="cancel-button"
              onClick={cancelMergeMode}
            >
              Cancel
            </button>
            <div className="keyboard-hints">
              Press <kbd>Enter</kbd> to merge • <kbd>Esc</kbd> to cancel
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MindMap; 
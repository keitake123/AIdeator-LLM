import React, { useEffect, useRef } from 'react';
import './MindMap.css';

const MindMap = ({ centralQuestion, concepts }) => {
  const mapRef = useRef(null);
  const centralRef = useRef(null);

  useEffect(() => {
    if (!mapRef.current || !centralRef.current) return;

    // Remove old lines
    const oldLines = mapRef.current.getElementsByClassName('concept-line');
    while (oldLines.length > 0) {
      oldLines[0].remove();
    }

    // Add new lines
    const central = centralRef.current.getBoundingClientRect();
    const mapRect = mapRef.current.getBoundingClientRect();

    concepts.forEach((_, index) => {
      const concept = mapRef.current.querySelector(`.concept-${index + 1}`);
      if (!concept) return;

      const conceptRect = concept.getBoundingClientRect();
      const line = document.createElement('div');
      line.className = `concept-line ${index > 2 ? 'inactive' : ''}`;

      // Calculate line position and dimensions
      const startX = central.x + central.width / 2 - mapRect.x;
      const startY = central.y + central.height / 2 - mapRect.y;
      const endX = conceptRect.x + conceptRect.width / 2 - mapRect.x;
      const endY = conceptRect.y + conceptRect.height / 2 - mapRect.y;

      const length = Math.sqrt(Math.pow(endX - startX, 2) + Math.pow(endY - startY, 2));
      const angle = Math.atan2(endY - startY, endX - startX);

      line.style.width = `${length}px`;
      line.style.left = `${startX}px`;
      line.style.top = `${startY}px`;
      line.style.transform = `rotate(${angle}rad)`;

      mapRef.current.appendChild(line);
    });
  }, [concepts, centralQuestion]);

  return (
    <div className="mind-map" ref={mapRef}>
      <div className="central-question" ref={centralRef}>
        {centralQuestion}
      </div>
      <div className="concepts-container">
        {concepts.map((concept, index) => (
          <div 
            key={index} 
            className={`concept concept-${index + 1} ${index > 2 ? 'inactive' : ''}`}
          >
            {concept}
          </div>
        ))}
      </div>
    </div>
  );
};

export default MindMap; 
import React from 'react';
import './MindMap.css';

const MindMap = ({ centralQuestion, concepts }) => {
  return (
    <div className="mind-map">
      <div className="central-question">
        {centralQuestion}
      </div>
      <div className="concepts-container">
        {concepts.map((concept, index) => (
          <div 
            key={index} 
            className={`concept concept-${index + 1}`}
            style={{
              '--angle': `${(360 / concepts.length) * index}deg`,
              '--distance': '150px'
            }}
          >
            {concept}
          </div>
        ))}
      </div>
    </div>
  );
};

export default MindMap; 
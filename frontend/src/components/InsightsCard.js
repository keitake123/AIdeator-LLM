import React, { useState } from 'react';
import './InsightsCard.css';

const InsightsCard = ({
  title,
  description,
  onSearch,
  onExpand,
  onMerge,
  onEdit,
  onDelete,
}) => {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div 
      className="insights-card"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="card-content">
        <h3 className="card-title">{title}</h3>
        <p className="card-description">{description}</p>
      </div>
      
      {isHovered && (
        <div className="card-actions">
          <button className="action-button search" onClick={onSearch} title="Search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5z"/>
            </svg>
          </button>
          <button className="action-button expand" onClick={onExpand} title="Expand">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M5 5l4 4m6 6l4 4M5 19l4-4m6-6l4-4" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
          <button className="action-button merge" onClick={onMerge} title="Merge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M7 4h10v10H7z M4 14h10v6H4z" strokeWidth="2"/>
            </svg>
          </button>
          <button className="action-button edit" onClick={onEdit} title="Edit">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M15 6l3 3L9 18H6v-3L15 6z" strokeWidth="2"/>
            </svg>
          </button>
          <button className="action-button delete" onClick={onDelete} title="Delete">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M6 7h12l-1 13H7L6 7z M4 7h16 M10 4h4" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
      )}
    </div>
  );
};

export default InsightsCard; 
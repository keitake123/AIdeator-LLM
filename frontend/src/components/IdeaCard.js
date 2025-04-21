import React, { useState, useEffect } from 'react';
import './IdeaCard.css';

const IdeaCard = ({
  title,
  description,
  isEditing,
  onAdd,
  onExpand,
  onMerge,
  onEdit,
  onDelete,
  onSave,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [editTitle, setEditTitle] = useState(title);
  const [editDescription, setEditDescription] = useState(description);

  useEffect(() => {
    setEditTitle(title);
    setEditDescription(description);
  }, [title, description]);

  const handleSave = () => {
    onSave(editTitle, editDescription);
  };

  if (isEditing) {
    return (
      <div className="idea-card editing">
        <div className="card-content">
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            placeholder="Enter title"
            className="edit-title"
          />
          <textarea
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            placeholder="Enter description"
            className="edit-description"
          />
          <button className="save-button" onClick={handleSave}>
            Save
          </button>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="idea-card"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="card-content">
        <h3 className="card-title">{title}</h3>
        <p className="card-description">{description}</p>
      </div>
      
      {isHovered && (
        <div className="card-actions">
          <button className="action-button add" onClick={onAdd} title="Add">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M12 5v14M5 12h14" strokeWidth="2" strokeLinecap="round"/>
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

export default IdeaCard;
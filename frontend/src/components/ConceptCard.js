import React, { useState } from 'react';
import './ConceptCard.css';

const ConceptCard = ({
  title,
  description,
  style,
  nodeId,
  onAdd,
  onExpand,
  onEdit,
  onDelete,
  onMouseDown,
  onClick,
  onToggleMergeMode,
  isSelectedForMerge,
  isMerged,
  mergedCount,
  sourceNodes,
  isExpandable,
  noIcons
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(title);
  const [editedDescription, setEditedDescription] = useState(description);

  const handleEdit = (e) => {
    e.stopPropagation(); // Prevent card drag
    if (isEditing) {
      onEdit(nodeId, editedTitle, editedDescription);
      setIsEditing(false);
    } else {
      setIsEditing(true);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleEdit(e);
    }
  };

  const handleAction = (e, action) => {
    e.stopPropagation(); // Prevent card drag
    action();
  };

  const handleSubmit = (e) => {
    e.stopPropagation();
    onEdit(nodeId, editedTitle, editedDescription);
    setIsEditing(false);
  };

  // If it's an expandable node with noIcons, start in editing mode
  React.useEffect(() => {
    if (isExpandable && noIcons) {
      setIsEditing(true);
    }
  }, [isExpandable, noIcons]);

  return (
    <div
      className={`concept expanded-child ${isSelectedForMerge ? 'merge-selected' : ''} ${isMerged ? 'merged' : ''} ${isExpandable ? 'expandable' : ''} ${noIcons ? 'no-icons' : ''}`}
      style={style}
      data-node-id={nodeId}
      onMouseDown={onMouseDown}
      onClick={onClick}
    >
      {isMerged && (
        <div className="concept-merge-label">
          🔗 Merged from {mergedCount} nodes
        </div>
      )}
      {isEditing ? (
        <div className="concept-edit-form" onClick={e => e.stopPropagation()}>
          <input
            type="text"
            value={editedTitle}
            onChange={(e) => setEditedTitle(e.target.value)}
            onKeyPress={handleKeyPress}
            className="concept-edit-title"
            placeholder="Enter title..."
            autoFocus
          />
          <textarea
            value={editedDescription}
            onChange={(e) => setEditedDescription(e.target.value)}
            onKeyPress={handleKeyPress}
            className="concept-edit-description"
            placeholder="Enter description..."
          />
          {noIcons && (
            <button
              className="idea-submit-button"
              onClick={handleSubmit}
            >
              Submit
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="concept-title">{title}</div>
          {isMerged ? (
            <div className="merged-content">
              {description.split('\n\n').map((section, index) => (
                <div key={index} className="merged-section">
                  {section}
                </div>
              ))}
            </div>
          ) : (
            <div className="concept-description">{description}</div>
          )}
        </>
      )}
      {!noIcons && (
      <div className="concept-icon">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">
          <path fill="none" d="M0 0h24v24H0z"/>
          <path d="M9.973 18h4.054c.132-1.202.745-2.194 1.74-3.277.113-.122.832-.867.917-.973a6 6 0 1 0-9.37-.002c.086.107.807.853.918.974.996 1.084 1.609 2.076 1.741 3.278zM14 20h-4v1h4v-1zm-8.246-5a8 8 0 1 1 12.49.002C17.624 15.774 16 17 16 18.5V21a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.5C8 17 6.375 15.774 5.754 15z" fill="rgba(136,136,136,0.6)"/>
        </svg>
      </div>
      )}
      {!noIcons && (
      <div className="card-actions">
        <button 
          className="action-button add" 
          title="Add" 
          onClick={(e) => handleAction(e, () => onAdd(nodeId))}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 5v14M5 12h14" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </button>
        <button 
          className={`action-button merge ${isSelectedForMerge ? 'active' : ''}`}
          title="Merge"
          onClick={(e) => {
            e.stopPropagation();
            onToggleMergeMode();
          }}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M8 2v4m0 12v4M16 2v4m0 12v4M3 12h18M12 3h4c2 0 3 1 3 3v12c0 2-1 3-3 3h-4M12 3H8c-2 0-3 1-3 3v12c0 2 1 3 3 3h4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <button 
          className="action-button expand" 
          title="Create Expandable Node" 
          onClick={(e) => handleAction(e, () => onExpand(nodeId))}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <button 
          className="action-button edit" 
          title="Edit" 
          onClick={handleEdit}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M15 6l3 3L9 18H6v-3L15 6z" strokeWidth="2"/>
          </svg>
        </button>
        <button 
          className="action-button delete" 
          title="Delete" 
          onClick={(e) => handleAction(e, () => onDelete(nodeId))}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" strokeWidth="2"/>
          </svg>
        </button>
      </div>
      )}
    </div>
  );
};

export default ConceptCard; 
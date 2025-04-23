import React, { useState } from 'react';
import IdeaCard from './IdeaCard';
import InsightsCard from './InsightsCard';
import './IdeationBoard.css';

const IdeationBoard = () => {
  const [cards, setCards] = useState([]);
  const [nextId, setNextId] = useState(1);

  // Helper function to generate AI suggestions
  const generateSuggestion = () => {
    // This would typically integrate with an AI service
    // For now, returning placeholder text
    return {
      title: "Generated Idea",
      description: "This is a generated suggestion based on the current context."
    };
  };

  const handleAddCard = (parentId = null) => {
    const newCard = {
      id: nextId,
      type: 'idea',
      title: '',
      description: '',
      parentId,
      isEditing: true
    };
    setCards([...cards, newCard]);
    setNextId(nextId + 1);
  };

  const handleExpandCard = (cardId) => {
    const suggestion = generateSuggestion();
    const newCard = {
      id: nextId,
      type: 'idea',
      title: suggestion.title,
      description: suggestion.description,
      parentId: cardId,
      isEditing: false
    };
    setCards([...cards, newCard]);
    setNextId(nextId + 1);
  };

  const handleMergeCards = (cardId) => {
    const newCard = {
      id: nextId,
      type: 'insights',
      title: 'Merged Insights',
      description: 'Combined insights from merged ideas',
      parentId: cardId,
      isEditing: false
    };
    setCards([...cards, newCard]);
    setNextId(nextId + 1);
  };

  const handleEditCard = (cardId) => {
    setCards(cards.map(card => 
      card.id === cardId ? { ...card, isEditing: true } : card
    ));
  };

  const handleSaveCard = (cardId, newTitle, newDescription) => {
    setCards(cards.map(card => 
      card.id === cardId 
        ? { ...card, title: newTitle, description: newDescription, isEditing: false }
        : card
    ));
  };

  const handleDeleteCard = (cardId) => {
    // Delete the card and all its children
    const deleteRecursive = (id) => {
      const childrenIds = cards
        .filter(card => card.parentId === id)
        .map(card => card.id);
      
      childrenIds.forEach(childId => deleteRecursive(childId));
      setCards(cards.filter(card => card.id !== id));
    };

    deleteRecursive(cardId);
  };

  const handleSearch = (cardId) => {
    // Implement search functionality
    console.log('Searching related to card:', cardId);
  };

  return (
    <div className="ideation-board">
      {cards.map(card => (
        card.type === 'idea' ? (
          <IdeaCard
            key={card.id}
            title={card.title}
            description={card.description}
            isEditing={card.isEditing}
            onAdd={() => handleAddCard(card.id)}
            onExpand={() => handleExpandCard(card.id)}
            onMerge={() => handleMergeCards(card.id)}
            onEdit={() => handleEditCard(card.id)}
            onDelete={() => handleDeleteCard(card.id)}
            onSave={(title, description) => handleSaveCard(card.id, title, description)}
          />
        ) : (
          <InsightsCard
            key={card.id}
            title={card.title}
            description={card.description}
            onSearch={() => handleSearch(card.id)}
            onExpand={() => handleExpandCard(card.id)}
            onMerge={() => handleMergeCards(card.id)}
            onEdit={() => handleEditCard(card.id)}
            onDelete={() => handleDeleteCard(card.id)}
          />
        )
      ))}
      {cards.length === 0 && (
        <button className="add-initial-card" onClick={() => handleAddCard()}>
          Add First Idea
        </button>
      )}
    </div>
  );
};

export default IdeationBoard; 
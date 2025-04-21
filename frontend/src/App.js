import React, { useState } from 'react';
import './App.css';
import IdeationForm from './components/IdeationForm';
import MindMap from './components/MindMap';
import IdeaCard from './components/IdeaCard';
import IdeationBoard from './components/IdeationBoard';

function App() {
  const [mindMapData, setMindMapData] = useState(null);

  const handleGenerate = async ({ targetAudience, problem }) => {
    // TODO: Replace with actual API call
    const question = `How Might We help ${targetAudience} ${problem}?`;
    const sampleConcepts = ['Concept 1', 'Concept 2', 'Concept 3', 'Concept 4', 'Concept 5'];
    setMindMapData({ centralQuestion: question, concepts: sampleConcepts });
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>AIdeator</h1>
      </header>
      <main className="App-main">
        <IdeationForm onGenerate={handleGenerate} />
        {mindMapData && (
          <MindMap 
            centralQuestion={mindMapData.centralQuestion}
            concepts={mindMapData.concepts}
          />
        )}
        <IdeationBoard />
      </main>
    </div>
  );
}

export default App; 
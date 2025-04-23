import React, { useState } from 'react';
import './App.css';
import IdeationForm from './components/IdeationForm';
import MindMap from './components/MindMap';
<<<<<<< HEAD
import IdeaCard from './components/IdeaCard';
import IdeationBoard from './components/IdeationBoard';
=======
import DraggableContainer from './components/DraggableContainer';
>>>>>>> eb8a50f4330814ff535dc149db9c2078291843d1

function App() {
  const [mindMapData, setMindMapData] = useState(null);

  const handleGenerate = async ({ targetAudience, problem }) => {
    // TODO: Replace with actual API call
    const question = `How Might We help ${targetAudience} ${problem}?`;
    const sampleConcepts = ['Concept 1', 'Concept 2', 'Concept 3', 'Concept 4', 'Concept 5'];
    setMindMapData({ centralQuestion: question, concepts: sampleConcepts });
  };

  return (
<<<<<<< HEAD
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
=======
    <DraggableContainer>
      <div className="App">
        <div className="App-content">
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
          </main>
        </div>
      </div>
    </DraggableContainer>
>>>>>>> eb8a50f4330814ff535dc149db9c2078291843d1
  );
}

export default App; 
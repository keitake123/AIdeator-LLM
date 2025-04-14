import React, { useState } from 'react';
import './IdeationForm.css';

const IdeationForm = ({ onGenerate }) => {
  const [targetAudience, setTargetAudience] = useState('');
  const [problem, setProblem] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onGenerate({ targetAudience, problem });
  };

  return (
    <div className="ideation-form">
      <div className="form-group">
        <label>Target Audience</label>
        <input
          type="text"
          value={targetAudience}
          onChange={(e) => setTargetAudience(e.target.value)}
          placeholder="College students"
          className="form-input"
        />
      </div>
      <div className="form-group">
        <label>Problem</label>
        <input
          type="text"
          value={problem}
          onChange={(e) => setProblem(e.target.value)}
          placeholder="Hard to focus"
          className="form-input"
        />
      </div>
      <button onClick={handleSubmit} className="generate-button">
        Generate
      </button>
    </div>
  );
};

export default IdeationForm; 
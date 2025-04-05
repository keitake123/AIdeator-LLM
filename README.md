# LLM Ideation Application

This application uses LangChain and LangGraph to create an interactive ideation experience with ChatGPT.

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

4. Run the application:
```bash
python src/main.py
```

## Project Structure

- `src/`: Main application code
  - `main.py`: Application entry point
  - `chains/`: LangChain components
  - `graphs/`: LangGraph workflow definitions
  - `utils/`: Utility functions
- `requirements.txt`: Project dependencies
- `.env`: Environment variables (not tracked in git)

## Features

- Interactive ideation sessions with ChatGPT
- Structured conversation flows using LangGraph
- State management for multi-turn conversations 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="LLM Ideation App")

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Define the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a creative ideation assistant. Help users generate and refine ideas."),
    ("user", "{input}")
])

# Create the chain
chain = prompt | llm | StrOutputParser()

class IdeationRequest(BaseModel):
    input: str
    context: Optional[List[str]] = None

@app.post("/ideate")
async def ideate(request: IdeationRequest):
    try:
        # Add context to the input if provided
        full_input = request.input
        if request.context:
            full_input = f"Context: {' '.join(request.context)}\n\nUser Input: {request.input}"
        
        # Generate response
        response = chain.invoke({"input": full_input})
        
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
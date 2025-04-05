from typing import TypedDict, Annotated, Sequence, List, Dict
from langgraph.graph import Graph, StateGraph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Define the state with more detailed information
class IdeationState(TypedDict):
    messages: Sequence[HumanMessage | AIMessage | SystemMessage]
    feedback: str
    context: Dict[str, str]
    problem_statement: str
    problem_statement_2: str  # Renamed from refined_problem_statement to problem_statement_2
    final_problem_statement: str  # Track the final selected problem statement
    waiting_for_input: bool
    awaiting_choice: bool  # Track if we're waiting for user to choose between statements
    input_instructions: Dict[str, str]  # Instructions for UI/CLI on what inputs to collect
    regenerate_problem_statement_1: bool  # Flag to indicate regeneration of problem_statement_1
    regenerate_problem_statement_2: bool  # Flag to indicate regeneration of problem_statement_2

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)

# Define the system message template
SYSTEM_TEMPLATE = """Persona: You are an extremely creative entrepreneur with a proven track record of developing innovative, profitable products. As my co-founder and ideation partner, your primary mission is to empower me to generate my own high-quality ideas. Rather than simply listing products or solutions, focus on supporting my brainstorming process by offering strategic questions, frameworks, and prompts that spark unconventional thinking. Challenge my assumptions, introduce fresh perspectives, and guide me to explore new angles—while letting me take the lead in discovering the possibilities.

Goal: In this session, we will co-create a brainstorming mindmap focused on a single problem statement at the center. Together, we'll explore and expand on interconnected concepts, directions, and ideas branching out from that central theme. By combining and refining the various elements in the mindmap, we will ultimately arrive at a set of well-defined product concepts."""

# Define the prompt template for problem statement generation
PROBLEM_STATEMENT_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    ("human", """Generate a single-sentence problem statement for:
Target Audience: {target_audience}
Problem: {problem}

Your response must be:
1. A single sentence starting with "How might we"
2. Include the target audience and problem
3. Include the preferred outcome of the solution in the end
4. End with a question mark
5. No longer than 20 words
6. No additional text or explanations

Example:
Input: Target Audience: college students, Problem: difficulty connecting with industry professionals
Output: "How might we facilitate meaningful connections between college students and industry professionals to enable early exploration of career paths and informed decision-making?"

Now generate a problem statement for:
Target Audience: {target_audience}
Problem: {problem}""")
])

# Define the NEW prompt template for problem statement refinement
PROBLEM_REFINEMENT_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    ("human", """Please follow these steps to generate an alternative problem statement (problem_statement_2) based on this original problem statement:
"{problem_statement}"

1. Identify the Current Problem Statement
   - Write down the original statement.

2. Extract the Preferable Outcome
   - Ask yourself: "After this problem is solved, what do we want to see happening? What's the ideal situation or behavior?"
   - Write this down as your `preferable_outcome`.

3. Brainstorm an Alternate Way to Achieve the Same Outcome
   - Think of another method or approach that would also fulfill the `preferable_outcome`.

4. Create a Second Problem Statement, and form `problem_statement_2`
   - Using the alternate approach, form another "How might we…" statement:
     "How might we + [alternate method] + [preferable_outcome]?"

5. **Output Requirement:**
   - Output only the `problem_statement_2` (the newly formed "How might we…" statement), as a single sentence.
   - Do not include any explanation or additional text.
   - No longer than 20 words.""")
])

# Define the prompt template for confirming the final problem statement
CONFIRM_STATEMENT_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    MessagesPlaceholder(variable_name="messages"),
    ("human", """Great! We'll use the following problem statement for our ideation session:

{final_statement}

Let's start by exploring potential directions and solutions for this problem statement. What key areas should we consider exploring?""")
])

def request_input(state: IdeationState) -> IdeationState:
    """Prepare state for human input by specifying what input is needed."""
    # Set up instructions in the state about what inputs we need to collect
    # This makes the function interface-agnostic - any UI can read these instructions
    state["input_instructions"] = {
        "target_audience": "Target audience:",
        "problem": "Problem:"
    }
    
    state["waiting_for_input"] = True
    state["awaiting_choice"] = False
    state["regenerate_problem_statement_1"] = False
    state["regenerate_problem_statement_2"] = False
    
    return state

def generate_problem_statement(state: IdeationState) -> IdeationState:
    """Generate a problem statement based on target audience and problem."""
    # Validate required inputs
    if not state["context"].get("target_audience") or not state["context"].get("problem"):
        state["problem_statement"] = "Error: Missing required inputs. Please provide both target audience and problem."
        return state

    try:
        # Create the prompt with target audience and problem
        prompt = PROBLEM_STATEMENT_PROMPT.format_messages(
            target_audience=state["context"]["target_audience"],
            problem=state["context"]["problem"]
        )
        
        # Generate response
        response = llm.invoke(prompt)
        formatted_response = response.content.strip()
        
        # Update state with response
        state["problem_statement"] = formatted_response
        
        # If this is the initial generation or a regeneration
        if not any(msg.content.startswith("Statement 1:") for msg in state["messages"] if isinstance(msg, AIMessage)):
            state["messages"].append(AIMessage(content=f"Statement 1: {formatted_response}"))
        else:
            # Replace the existing Statement 1 message
            for i, msg in enumerate(state["messages"]):
                if isinstance(msg, AIMessage) and msg.content.startswith("Statement 1:"):
                    state["messages"][i] = AIMessage(content=f"Statement 1: {formatted_response}")
                    break
        
        state["waiting_for_input"] = False
        state["regenerate_problem_statement_1"] = False
        
        return state

    except Exception as e:
        state["problem_statement"] = f"Error generating problem statement: {str(e)}"
        return state

def generate_problem_statement_2(state: IdeationState) -> IdeationState:
    """Generate an alternative problem statement (problem_statement_2)."""
    if not state.get("problem_statement"):
        state["problem_statement_2"] = "Error: No problem statement to work with."
        return state

    try:
        # Debug - commented out but kept for future use
        # print(f"\nDEBUG - Original problem statement: {state['problem_statement']}")
        
        # Create prompt with the current problem statement
        prompt = PROBLEM_REFINEMENT_PROMPT.format_messages(
            problem_statement=state["problem_statement"]
        )
        
        # Debug: Print the actual content being sent to the LLM - commented out but kept
        # print("\nDEBUG - Prompt being sent to LLM:")
        # for message in prompt:
        #     print(f"Role: {message.type}")
        #     content_preview = message.content[:200] + "..." if len(message.content) > 200 else message.content
        #     print(f"Content preview: {content_preview}\n")
        
        # Generate response
        response = llm.invoke(prompt)
        problem_statement_2 = response.content.strip()
        
        # Post-process to extract just the "How might we" statement if there's extra content
        if len(problem_statement_2.split('\n')) > 1 or len(problem_statement_2.split('.')) > 1:
            import re
            hmw_statements = re.findall(r"How might we[^.?!]*[.?!]", problem_statement_2)
            if hmw_statements:
                problem_statement_2 = hmw_statements[-1].strip()  # Take the last one as it's likely the final statement
        
        # Store the second problem statement
        state["problem_statement_2"] = problem_statement_2
        
        # Only append to messages if it's not a regeneration or if messages doesn't already contain Statement 2
        if not state["regenerate_problem_statement_2"] or not any(msg.content.startswith("Statement 2:") for msg in state["messages"] if isinstance(msg, AIMessage)):
            state["messages"].append(AIMessage(content=f"Statement 2: {problem_statement_2}"))
        else:
            # Replace the existing Statement 2 message
            for i, msg in enumerate(state["messages"]):
                if isinstance(msg, AIMessage) and msg.content.startswith("Statement 2:"):
                    state["messages"][i] = AIMessage(content=f"Statement 2: {problem_statement_2}")
                    break
        
        # Reset regeneration flag
        state["regenerate_problem_statement_2"] = False
        
        # Update instructions for the next user input (choosing between statements with regeneration option)
        state["input_instructions"] = {
            "choice": "Select 'statement 1', 'statement 2', or 'regenerate' to get a new alternative statement"
        }
        state["awaiting_choice"] = True
        
        return state

    except Exception as e:
        state["problem_statement_2"] = f"Error generating problem statement 2: {str(e)}"
        return state

def request_choice(state: IdeationState) -> IdeationState:
    """Request user to choose between the two problem statements or regenerate either statement."""
    # Simply prepare the state for user choice without calling the LLM
    state["awaiting_choice"] = True
    state["input_instructions"] = {
        "choice": "Select between 'statement 1', 'statement 2', 'r1' to regenerate statement 1, or 'r2' to regenerate statement 2",
        "options": {
            "statement 1": state["problem_statement"],
            "statement 2": state["problem_statement_2"],
            "r1": "Regenerate Statement 1",
            "r2": "Regenerate Statement 2"
        }
    }
    
    return state

def process_user_choice(state: IdeationState, choice: str) -> IdeationState:
    """Process user's choice between the two problem statements or request for regeneration."""
    # Normalize choice to handle different input formats
    normalized_choice = choice.lower().strip()
    
    # Check if the user wants to regenerate problem statements
    if "r1" in normalized_choice or "regenerate 1" in normalized_choice or "regenerate statement 1" in normalized_choice:
        state["regenerate_problem_statement_1"] = True
        # Save message about regeneration request
        state["messages"].append(HumanMessage(content="I'd like to regenerate the first problem statement."))
        return state
    
    if "r2" in normalized_choice or "regenerate 2" in normalized_choice or "regenerate statement 2" in normalized_choice:
        state["regenerate_problem_statement_2"] = True
        # Save message about regeneration request
        state["messages"].append(HumanMessage(content="I'd like to regenerate the alternative problem statement."))
        return state
    
    # Set the final problem statement based on user choice
    if "1" in normalized_choice or "statement 1" in normalized_choice:
        state["final_problem_statement"] = state["problem_statement"]
        choice_text = "statement 1"
    elif "2" in normalized_choice or "statement 2" in normalized_choice:
        state["final_problem_statement"] = state["problem_statement_2"]
        choice_text = "statement 2"
    else:
        # Default to statement 1 if choice is unclear
        state["final_problem_statement"] = state["problem_statement"]
        state["feedback"] = "Unclear choice. Defaulting to statement 1."
        choice_text = "statement 1"
    
    # Add user choice to messages
    state["messages"].append(HumanMessage(content=f"I choose {choice_text}."))
    state["awaiting_choice"] = False
    state["regenerate_problem_statement_1"] = False
    state["regenerate_problem_statement_2"] = False
    state["input_instructions"] = {}  # Clear input instructions
    
    return state

def confirm_problem_statement(state: IdeationState) -> IdeationState:
    """Confirm the final problem statement and transition to ideation."""
    try:
        # Create prompt to confirm the final statement
        prompt = CONFIRM_STATEMENT_PROMPT.format_messages(
            messages=state["messages"],
            final_statement=state["final_problem_statement"]
        )
        
        # Generate response
        response = llm.invoke(prompt)
        
        # Update state
        state["messages"].append(response)
        
        return state
        
    except Exception as e:
        state["feedback"] = f"Error confirming problem statement: {str(e)}"
        return state

def run_cli_workflow():
    """Run the ideation workflow as a CLI application."""
    print("\n===== IDEATION WORKFLOW CLI =====\n")
    print("Starting a new ideation session...\n")
    
    # Initialize state
    state = {
        "messages": [SystemMessage(content=SYSTEM_TEMPLATE)],
        "feedback": "",
        "context": {},
        "problem_statement": "",
        "problem_statement_2": "",  # Renamed from refined_problem_statement
        "final_problem_statement": "",
        "waiting_for_input": False,
        "awaiting_choice": False,
        "input_instructions": {},
        "regenerate_problem_statement_1": False,  # New flag for regenerating statement 1
        "regenerate_problem_statement_2": False   # Flag for regenerating statement 2
    }
    
    # Step 1: Request input (get instructions on what to collect)
    state = request_input(state)
    
    # Use the instructions from the state to prompt the user
    for field, prompt in state["input_instructions"].items():
        print(f"{prompt} ")
        user_input = input()
        state["context"][field] = user_input
    
    # Add user inputs to messages
    state["messages"].append(HumanMessage(content=f"Target audience: {state['context']['target_audience']}\nProblem: {state['context']['problem']}"))
    state["waiting_for_input"] = False
    
    # Step 2: Generate problem statement 1
    print("\nGenerating problem statement 1...")
    state = generate_problem_statement(state)
    print(f"Statement 1: {state['problem_statement']}\n")
    
    # Loop until user selects a final problem statement
    final_statement_selected = False
    
    while not final_statement_selected:
        # Check if we need to regenerate statements
        if state["regenerate_problem_statement_1"]:
            print("Regenerating problem statement 1...")
            state = generate_problem_statement(state)
            print(f"Statement 1: {state['problem_statement']}\n")
            state["regenerate_problem_statement_1"] = False
        
        if not state["problem_statement_2"] or state["regenerate_problem_statement_2"]:
            print("Generating problem statement 2...")
            state = generate_problem_statement_2(state)
            print(f"Statement 2: {state['problem_statement_2']}\n")
            state["regenerate_problem_statement_2"] = False
        
        # Display choices to user
        print("Please choose which problem statement to use:")
        print(f"1. Statement 1: {state['problem_statement']}")
        print(f"2. Statement 2: {state['problem_statement_2']}")
        print("r1. Regenerate Statement 1")
        print("r2. Regenerate Statement 2")
        
        choice = input("Enter '1', '2', 'r1', or 'r2': ").lower()
        
        # Process user choice
        state = process_user_choice(state, choice)
        
        # Check if we need to regenerate or proceed
        if state["regenerate_problem_statement_1"] or state["regenerate_problem_statement_2"]:
            continue
        else:
            final_statement_selected = True
    
    print(f"\nYou selected: {choice}")
    print(f"Final problem statement: {state['final_problem_statement']}\n")
    
    # Step 5: Confirm problem statement
    print("Confirming problem statement and starting ideation...")
    state = confirm_problem_statement(state)
    
    # Print the final response
    final_response = state["messages"][-1].content
    print(f"\nAssistant: {final_response}\n")
    
    print("\n===== WORKFLOW COMPLETED =====\n")
    
    return state

# Create the workflow
workflow = StateGraph(IdeationState)

# Add nodes
workflow.add_node("request_input", request_input)
workflow.add_node("generate_problem_statement", generate_problem_statement)
workflow.add_node("generate_problem_statement_2", generate_problem_statement_2)
workflow.add_node("request_choice", request_choice)
workflow.add_node("confirm_problem_statement", confirm_problem_statement)

# Add edges with conditional logic for regeneration
workflow.add_edge("request_input", "generate_problem_statement")
workflow.add_edge("generate_problem_statement", "generate_problem_statement_2")
workflow.add_edge("generate_problem_statement_2", "request_choice")

# Add conditional edges for regeneration
workflow.add_conditional_edges(
    "request_choice",
    lambda state: {
        "generate_problem_statement": state["regenerate_problem_statement_1"],
        "generate_problem_statement_2": state["regenerate_problem_statement_2"],
        "confirm_problem_statement": not (state["regenerate_problem_statement_1"] or state["regenerate_problem_statement_2"])
    }
)

# Set entry point
workflow.set_entry_point("request_input")

# Compile the graph
app = workflow.compile()

# Example usage function
def start_ideation_session() -> IdeationState:
    """Start a new ideation session with a fresh state."""
    initial_state = {
        "messages": [],  # Start with empty message history
        "feedback": "",
        "context": {},
        "problem_statement": "",
        "problem_statement_2": "",  # Renamed from refined_problem_statement
        "final_problem_statement": "",
        "waiting_for_input": False,
        "awaiting_choice": False,
        "input_instructions": {},
        "regenerate_problem_statement_1": False,  # Flag for regenerating statement 1
        "regenerate_problem_statement_2": False   # Flag for regenerating statement 2
    }
    
    # Add the system message to start fresh
    initial_state["messages"].append(SystemMessage(content=SYSTEM_TEMPLATE))
    
    return app.invoke(initial_state)

def process_human_input(state: IdeationState, target_audience: str, problem: str) -> IdeationState:
    """Process human input and generate problem statement."""
    # Update context with human input
    state["context"]["target_audience"] = target_audience
    state["context"]["problem"] = problem
    
    # Add human input to messages
    state["messages"].append(HumanMessage(content=f"Target audience: {target_audience}\nProblem: {problem}"))
    
    # Set waiting for input to false
    state["waiting_for_input"] = False
    
    # Continue with the workflow from the current state
    return app.invoke(state)

def process_choice(state: IdeationState, choice: str) -> IdeationState:
    """Process user's choice and continue the workflow."""
    # Process the choice first
    updated_state = process_user_choice(state, choice)
    
    # Continue with the workflow from the updated state
    return app.invoke(updated_state)

# If this file is run directly, execute the CLI workflow
if __name__ == "__main__":
    run_cli_workflow()
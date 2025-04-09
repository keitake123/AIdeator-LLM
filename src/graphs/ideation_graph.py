from typing import TypedDict, Annotated, Sequence, List, Dict, Optional
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
    
    # New fields for exploration options
    threads: Dict[str, Dict]  # Store the three exploration approaches
    active_thread: Optional[str]  # Track the selected exploration approach
    awaiting_thread_choice: bool  # Track if we're waiting for user to choose an exploration approach
    mindmap: Dict  # For future mindmap structure
    current_step: str  # Track current step in workflow

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

# Template for "Emotional Root Causes" exploration - placeholder for future implementation
EMOTIONAL_ROOT_CAUSES_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    MessagesPlaceholder(variable_name="thread_messages"),
    ("human", """Please follow these steps to explore the emotional root causes behind {problem_statement}. Return only valid JSON in the exact structure specified below. Use concise phrasing (one or two sentences per field). 
a. Emotional Seeds
1. Task: Identify 3 core emotional root causes leading to the problem. What feelings (e.g., anxiety, longing, excitement) do people experience? Why do these emotions arise?
2. Add-on: For each root cause, suggest one product direction that addresses or harnesses the emotion to improve the user experience.
3. Tip: Seek genuinely empathetic insights. Consider social context, personal identity, and psychological triggers. Avoid generic or superficial explanations.

b. Habit & Heuristic Alignment
1. Task: List 2 key human habits or heuristics relevant to the domain (e.g., preference for consistency, aversion to steep learning curves, love for quick feedback).
2. Add-on: Brainstorm 1 direction that cleverly leverages or strengthens these habits.
3. Tip: Think beyond the obvious. Explore how established routines, comfort zones, or mental shortcuts can be nudged in creative ways to improve engagement and satisfaction.

c. Delightful Subversion
1. Task: Identify 2 commonly negative or taboo perceptions/frustrations in this context.
2. Add-on: Suggest how each could be flipped into something playful, intriguing, or surprisingly positive. Keep suggestions concise and open-ended.
3. Tip: Push your creativity here! Consider surprise-and-delight mechanics, or turning negative emotions into rewards that reshape the user’s emotional journey.

Please follow this example of valid output:
{{
  "emotionalSeeds": [
    {{
      "heading": "Fear of letting others down",
      "explanation": "Social and professional pressures can make people fear judgment from peers.",
      "productDirection": "Use progress-sharing with supportive feedback loops instead of performance scores."
    }}
  ],
  "habitHeuristicAlignment": [
    {{
      "heading": "Preference for social proof",
      "explanation": "People tend to feel safer engaging when they see others like them participating.",
      "productDirection": "Showcase student testimonials and photos of real cultural meetups to spark FOMO-driven curiosity."
    }}
  ],
  "delightfulSubversion": [
    {{
      "heading": "Fear of making social mistakes",
      "explanation": "Missteps in unfamiliar social norms can cause embarrassment or withdrawal.",
      "productDirection": "Gamify social learning with humorous 'oops cards' that turn faux pas into laughable, teachable moments."
    }}
  ]
}}""")
])

# Template for "Unconventional Associations" exploration - placeholder for future implementation
UNCONVENTIONAL_ASSOCIATIONS_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    MessagesPlaceholder(variable_name="thread_messages"),
    ("human", """Please follow these steps to explore the unconventional associations behind {problem_statement}. Please return only valid JSON in the exact structure specified below. Use concise phrasing (one or two sentences per field). 

a. Attribute-Based Bridging
Identify Attributes: Choose 3 defining attributes or characteristics of the problem concept (e.g., “it requires active maintenance,” “it thrives on collaboration,” or “it’s quick to appear but slow to sustain”).
Cross-Domain Link: For each attribute, select one concept from a completely different field—technology, biology, art, history, sports, etc.—that also exhibits or relies on this same attribute.
Insight & Product Direction: Explain how the unexpected link can spark new understanding or design ideas for the problem. Propose one product direction based on this analogy.
     
b. Broader Domains
Explore from 2 different perspectives (eg. psychologist, historian, poet, child, philosopher). Feel free to adapt or replace these perspectives to suit the context. Under each perspective, summarize their core concepts as headings, and then describe how each uniquely interprets the problem.
For each perspective, propose one idea or feature that draws inspiration from that viewpoint.
     
c. Metaphorical Links
Present 2 conceptual or symbolic metaphors that could reframe the problem on psychological, spiritual, emotional, or other layers.
Summarize the metaphor and provide one feature or design suggestion that arises from it.
Please follow this example of valid output:
{{
  "attributeBasedBridging": [
    {{
      "heading": "Maintains Momentum (Sailing a Boat)",
      "explanation": "Both focus and sailing require active navigation of changing conditions to stay on course.",
      "productDirection": "Implement a 'drift alert' that nudges users when they stray from tasks, suggesting immediate refocus strategies."
    }}
  ],
  "broaderDomains": [
    {{
      "heading": "Cognitive load affecting concentration",
      "explanation": "Psychologists explore cognitive load and how stress levels affect sustained concentration over time.",
      "productDirection": "Include periodic check-ins for emotional wellbeing, offering calming exercises before focus-intensive tasks."
    }}
  ],
  "metaphoricalLinks": [
    {{
      "heading": "Focus as a Muscle",
      "explanation": "It strengthens with repetition but requires rest and recovery to grow effectively.",
      "productDirection": "Provide a 'cooldown timer' suggesting short breaks after intense work sessions to prevent fatigue."
    }}
  ]
}}""")
])

# Template for "Imaginary Customers' Feedback" exploration - placeholder for future implementation
IMAGINARY_FEEDBACK_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    MessagesPlaceholder(variable_name="thread_messages"),
    ("human", """Please follow these steps to explore the unconventional associations behind {problem_statement}. Please return only valid JSON in the exact structure specified below. Use concise phrasing (one or two sentences per field).
a. Create 4 Imaginary Target Users & Their Feedback
Invent Personas: Come up with 4 distinct user profiles, each having a short description (e.g., name, age, occupation). Making sure they are differentiated enough.
Background: Write one sentence summarizing the persona’s daily life, habits, and tech savviness.
Feedback: List one struggle, pain point, or initial thought the persona might have about the problem as the heading. Ensure each pain point reflects a distinct perspective—mental, physical, emotional, etc.—and is not overlapping. Then, explain this pain point in a single concise sentence.

b. Respond with Potential Product Directions
Link to Feedback: For each feedback item, propose a concise product direction that addresses or alleviates the user’s struggle.
Practical Innovations: Focus on new features, design improvements, or creative innovations that respond to the user’s specific needs or pain points.

Please follow this example of valid output:
[
  {{
    "heading": "Notifications are very distracting.",
    "userProfile": "Emma, 26, Remote Designer. Works from coffee shops, juggling multiple freelance clients and productivity tools.",
    "feedback": [
      {{
        "explanation": "I can get distracted by notifications from different platforms fairly easy",
        "productDirection": "Implement an automatic 'focus mode' that silences unrelated notifications during task time."
      }}
    ]
  }}
 ]""")
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
    state["current_step"] = "initial_input"
    
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
        state["current_step"] = "generate_problem_statement_2"
        
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
        # Create prompt with the current problem statement
        prompt = PROBLEM_REFINEMENT_PROMPT.format_messages(
            problem_statement=state["problem_statement"]
        )
        
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
        state["current_step"] = "request_choice"
        
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
    state["current_step"] = "await_choice"
    
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
        state["current_step"] = "generate_problem_statement"
        return state
    
    if "r2" in normalized_choice or "regenerate 2" in normalized_choice or "regenerate statement 2" in normalized_choice:
        state["regenerate_problem_statement_2"] = True
        # Save message about regeneration request
        state["messages"].append(HumanMessage(content="I'd like to regenerate the alternative problem statement."))
        state["current_step"] = "generate_problem_statement_2"
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
    
    # Move to presenting exploration options instead of confirming
    state["current_step"] = "present_exploration_options"
    
    return state

def present_exploration_options(state: IdeationState) -> IdeationState:
    """Present the three fixed exploration options to the user."""
    # Display confirmation of the selected problem statement
    state["messages"].append(AIMessage(content=f"We'll use the following problem statement for our ideation session: {state['final_problem_statement']}"))
    
    # Initialize the mindmap with the problem statement as the central node
    state["mindmap"] = {
        "id": "root",
        "name": state["final_problem_statement"],
        "children": []
    }
    
    # Define the three fixed exploration options
    threads = [
        ("Emotional Root Causes", "Explore the underlying emotional needs, fears, or motivations"),
        ("Unconventional Associations", "Connect the problem to unexpected domains, metaphors, or analogies"),
        ("Imaginary Customers' Feedback", "Imagine different feedback perspectives on potential solutions")
    ]
    
    # Initialize the threads structure
    state["threads"] = {}
    for i, (name, description) in enumerate(threads, 1):
        thread_id = f"thread_{i}"
        state["threads"][thread_id] = {
            "id": thread_id,
            "name": name,
            "description": description,
            "messages": [SystemMessage(content=SYSTEM_TEMPLATE)]  # Each thread has its own message history
        }
        
        # Add to mindmap
        state["mindmap"]["children"].append({
            "id": thread_id,
            "name": name,
            "description": description,
            "children": []
        })
    
    # Set up for thread choice
    state["awaiting_thread_choice"] = True
    state["input_instructions"] = {
        "thread_choice": "Choose an exploration approach:",
        "options": {
            "1": "Emotional Root Causes",
            "2": "Unconventional Associations", 
            "3": "Imaginary Customers' Feedback"
        }
    }
    state["current_step"] = "await_thread_choice"
    
    return state


def process_thread_choice_multi(state: IdeationState, choice: str) -> IdeationState:
    """Process the user's choice of which exploration approach to use without ending the session."""
    # Reset switching flag
    state["switch_thread"] = False
    
    # Check for "stop" command
    if choice.lower().strip() == "stop":
        state["current_step"] = "end_session"
        state["feedback"] = "Ending the ideation session as requested."
        return state
    
    # Normalize and validate choice
    try:
        thread_num = int(choice.strip())
        if thread_num < 1 or thread_num > 3:
            raise ValueError("Thread choice must be 1, 2, or 3")
    except ValueError:
        # Try to match by name
        thread_map = {
            "emotional": "1",
            "emotional root": "1",
            "emotional root causes": "1",
            "root causes": "1",
            "unconventional": "2",
            "unconventional associations": "2",
            "associations": "2",
            "imaginary": "3",
            "feedback": "3",
            "imaginary customers": "3",
            "customers feedback": "3",
            "imaginary customers' feedback": "3"
        }
        normalized_choice = choice.lower().strip()
        thread_choice = thread_map.get(normalized_choice)
        if thread_choice:
            thread_num = int(thread_choice)
        else:
            state["feedback"] = "Invalid choice. Please select 1 (Emotional Root Causes), 2 (Unconventional Associations), or 3 (Imaginary Customers' Feedback)."
            state["switch_thread"] = True  # Return to thread selection
            return state
    
    # Set the active thread
    thread_id = f"thread_{thread_num}"
    state["active_thread"] = thread_id
    
    # Only add messages if this is the first time selecting this thread
    if len(state["threads"][thread_id]["messages"]) <= 1:  # Only has system message
        # Add user choice to main messages
        state["messages"].append(HumanMessage(content=f"I choose to explore {state['threads'][thread_id]['name']}."))
        
        # Add the choice to thread-specific messages
        thread_message = HumanMessage(content=f"Let's explore the problem statement through the lens of {state['threads'][thread_id]['name']}.")
        state["threads"][thread_id]["messages"].append(thread_message)
        
        # For now, just acknowledge the selection in a simplified workflow
        thread_name = state["threads"][thread_id]["name"]
        state["messages"].append(AIMessage(content=f"Great! We'll explore '{state['final_problem_statement']}' through the {thread_name} approach. This thread now has its own separate conversation history."))
    
    # In the future, this would set up for branch generation
    state["current_step"] = "thread_exploration"  # Mark that we're in thread exploration mode
    
    return state

def thread_exploration(state: IdeationState) -> IdeationState:
    """Handle exploration within a specific thread using the appropriate prompt template."""
    thread_id = state["active_thread"]
    if not thread_id:
        state["feedback"] = "No active thread selected."
        return state
    
    thread_name = state["threads"][thread_id]["name"]
    
    # Select the appropriate prompt template based on the thread
    prompt_template = None
    if thread_id == "thread_1":  # Emotional Root Causes
        prompt_template = EMOTIONAL_ROOT_CAUSES_PROMPT
    elif thread_id == "thread_2":  # Unconventional Associations
        prompt_template = UNCONVENTIONAL_ASSOCIATIONS_PROMPT
    elif thread_id == "thread_3":  # Imaginary Customers' Feedback
        prompt_template = IMAGINARY_FEEDBACK_PROMPT
    else:
        state["feedback"] = f"Unknown thread type: {thread_name}"
        return state
    
    try:
        # Get the messages from the thread
        thread_messages = state["threads"][thread_id]["messages"]
        
        # Format the prompt with the problem statement and thread-specific messages
        prompt = prompt_template.format_messages(
            problem_statement=state["final_problem_statement"],
            thread_messages=thread_messages
        )
        
        # Invoke the LLM
        response = llm.invoke(prompt)
        response_content = response.content.strip()
        
        # DEBUG: Print the raw response for debugging (you can remove this later)
        # print("\n----- RAW LLM RESPONSE -----")
        # print(response_content)
        # print("----------------------------\n")
        
        # Add the LLM response to the thread messages
        state["threads"][thread_id]["messages"].append(AIMessage(content=response_content))
        
        # Add a notification to the main message history
        notification = f"Explored '{state['final_problem_statement']}' through the {thread_name} approach."
        state["messages"].append(AIMessage(content=notification))
        
        # Try to parse JSON from the response
        try:
            import json
            import re
            
            # First try to parse the whole response as JSON
            try:
                json_data = json.loads(response_content)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON using regex
                json_pattern = re.search(r'(\{.*\}|\[.*\])', response_content, re.DOTALL)
                if json_pattern:
                    potential_json = json_pattern.group(0)
                    json_data = json.loads(potential_json)
                else:
                    raise Exception("No valid JSON found in the response")
            
            # Store the parsed JSON in the thread
            state["threads"][thread_id]["exploration_data"] = json_data
            
            # Find the thread node in the mindmap and add the data
            thread_node = next((node for node in state["mindmap"]["children"] if node["id"] == thread_id), None)
            if thread_node:
                thread_node["exploration_data"] = json_data
            
            state["feedback"] = f"Successfully explored the {thread_name} approach and captured structured data."
            
        except Exception as json_error:
            # JSON parsing failed, but the response is still saved
            print(f"Note: Could not parse JSON from response: {str(json_error)}")
            state["feedback"] = f"Explored the {thread_name} approach, but couldn't extract structured data."
        
        return state
        
    except Exception as e:
        # Handle any other errors that might occur
        import traceback
        print(traceback.format_exc())
        state["feedback"] = f"Error during {thread_name} exploration: {str(e)}"
        return state

def end_session(state: IdeationState) -> IdeationState:
    """End the ideation session."""
    # Count explored threads
    explored_threads = []
    for thread_id, thread in state["threads"].items():
        if len(thread["messages"]) > 1:  # More than just the system message
            explored_threads.append(thread["name"])
    
    # Create a summary message
    if explored_threads:
        explored_list = ", ".join(explored_threads)
        summary = f"""
Ideation Session Summary:

Problem Statement: {state['final_problem_statement']}

Explored Approaches: {explored_list}

Each exploration approach has its own separate conversation history for future development.
"""
    else:
        summary = f"""
Ideation Session Summary:

Problem Statement: {state['final_problem_statement']}

No exploration approaches were selected.
"""
    
    # Add summary to messages
    state["messages"].append(AIMessage(content=summary))
    
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
        "regenerate_problem_statement_2": False,  # Flag for regenerating statement 2
        # New fields for exploration options
        "threads": {},
        "active_thread": None,
        "awaiting_thread_choice": False,
        "switch_thread": False,  # Flag for switching between threads
        "mindmap": {},
        "current_step": "initial_input"
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
    
    # Step 3: Present exploration options (instead of confirming problem statement)
    print("Now let's explore this problem from different angles.")
    state = present_exploration_options(state)
    
    # Start multi-thread exploration using state graph workflow
    exploring = True
    
    while exploring:
        # Show the exploration options
        print("\nPlease choose an exploration approach:")
        
        # Show current status of each thread
        for i in range(1, 4):
            thread_id = f"thread_{i}"
            thread = state["threads"][thread_id]
            thread_name = thread["name"]
            status = " (current)" if state["active_thread"] == thread_id else ""
            status += " (explored)" if len(thread["messages"]) > 1 else ""
            print(f"{i}. {thread_name}{status}")
        
        # Get user choice for exploration approach
        exploration_choice = input("\nEnter '1', '2', '3', or 'stop': ").lower()
        
        # Set up context for process_thread_choice_multi
        state["context"]["thread_choice"] = exploration_choice
        
        # Process using state graph workflow
        old_thread = state["active_thread"]
        old_step = state["current_step"]
        
        # Invoke the state graph
        state = process_thread_choice_multi(state, exploration_choice)
        
        # If stopping, break the loop
        if state["current_step"] == "end_session":
            exploring = False
            continue
            
        # If switching threads, continue the loop to show options again
        if state.get("switch_thread", False):
            continue
            
        # If we selected a thread to explore, simulate the thread exploration
        if state["current_step"] == "thread_exploration":
            thread_id = state["active_thread"]
            thread_name = state["threads"][thread_id]["name"]
            
            print(f"\nNow exploring: {thread_name}")
            print(f"This thread has its own separate conversation history.")
            
            # Simulate thread exploration
            state = thread_exploration(state)

            # Display exploration results in a user-friendly way
            thread_id = state["active_thread"]
            thread_data = state["threads"][thread_id].get("exploration_data")

            if thread_data:
                import json
                print("\n===== EXPLORATION RESULTS =====")
                print(json.dumps(thread_data, indent=2))
                print("===============================\n")
            else:
                print("\nExploration complete. Raw response saved to thread history.")
            
            # Display feedback
            if state["feedback"]:
                print(f"\n{state['feedback']}")
                state["feedback"] = ""
    

    # End session and display summary
    state = end_session(state)
    final_message = state["messages"][-1].content
    
    print("\n===== IDEATION SESSION SUMMARY =====\n")
    print(final_message)
    
    # Show thread-specific message counts
    print("\nThread Activity Summary:")
    for thread_id, thread in state["threads"].items():
        # Count only non-system messages
        message_count = sum(1 for msg in thread["messages"] if not isinstance(msg, SystemMessage))
        print(f"- {thread['name']}: {message_count} messages")
    
    print("\n===== WORKFLOW COMPLETED =====\n")
    
    return state

# Create the workflow
workflow = StateGraph(IdeationState)

# Add nodes
workflow.add_node("request_input", request_input)
workflow.add_node("generate_problem_statement", generate_problem_statement)
workflow.add_node("generate_problem_statement_2", generate_problem_statement_2)
workflow.add_node("request_choice", request_choice)
workflow.add_node("present_exploration_options", present_exploration_options)
workflow.add_node("process_thread_choice", lambda state: process_thread_choice_multi(state, state["context"].get("thread_choice", "")))
workflow.add_node("thread_exploration", thread_exploration)
workflow.add_node("end_session", end_session)

# Add edges with conditional logic for regeneration
workflow.add_edge("request_input", "generate_problem_statement")
workflow.add_edge("generate_problem_statement", "generate_problem_statement_2")
workflow.add_edge("generate_problem_statement_2", "request_choice")

# Add conditional edges for problem statement workflow
workflow.add_conditional_edges(
    "request_choice",
    lambda state: {
        "generate_problem_statement": state["regenerate_problem_statement_1"],
        "generate_problem_statement_2": state["regenerate_problem_statement_2"],
        "present_exploration_options": not (state["regenerate_problem_statement_1"] or state["regenerate_problem_statement_2"])
    }
)

# Add conditional edges for exploration options workflow
workflow.add_edge("present_exploration_options", "process_thread_choice")

# Add conditional edges for thread exploration and switching
workflow.add_conditional_edges(
    "process_thread_choice",
    lambda state: {
        "present_exploration_options": state.get("switch_thread", False),  # Switch to another thread
        "thread_exploration": not state.get("switch_thread", False) and state["current_step"] != "end_session",  # Explore the selected thread
        "end_session": state["current_step"] == "end_session"  # End the session
    }
)

# Add edge from thread exploration back to thread selection
workflow.add_edge("thread_exploration", "present_exploration_options")

# Set entry point
workflow.set_entry_point("request_input")

# Compile the graph (only once)
app = workflow.compile()

# Example usage function
def start_ideation_session() -> IdeationState:
    """Start a new ideation session with a fresh state."""
    initial_state = {
        "messages": [],  # Start with empty message history
        "feedback": "",
        "context": {},
        "problem_statement": "",
        "problem_statement_2": "",
        "final_problem_statement": "",
        "waiting_for_input": False,
        "awaiting_choice": False,
        "input_instructions": {},
        "regenerate_problem_statement_1": False,
        "regenerate_problem_statement_2": False,
        # New fields for exploration options
        "threads": {},
        "active_thread": None,
        "awaiting_thread_choice": False, 
        "mindmap": {},
        "current_step": "initial_input"
    }
    
    # Add the system message to start fresh
    initial_state["messages"].append(SystemMessage(content=SYSTEM_TEMPLATE))
    
    return app.invoke(initial_state)

# If this file is run directly, execute the CLI workflow
if __name__ == "__main__":
    run_cli_workflow()
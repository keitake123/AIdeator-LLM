from typing import TypedDict, Annotated, Sequence, List, Dict, Optional
from langgraph.graph import Graph, StateGraph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import os 
from dotenv import load_dotenv
import json
import re

load_dotenv()

# Define the state with more detailed information
class IdeationState(TypedDict):
    messages: Sequence[HumanMessage | AIMessage | SystemMessage]
    feedback: str
    context: Dict[str, str]
    problem_statement: str
    problem_statement_2: str  # Refined_problem_statement
    explanation: str  # Explanation of how the assumption is flipped
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
    
    # New fields for concept expansion
    branches: Dict[str, Dict]  # Store all branches with unique indices
    active_branch: Optional[str]  # Track the currently selected branch
    awaiting_branch_choice: bool  # Track if we're waiting for branch selection
    branch_counter: int  # Global counter for branch indices
    awaiting_concept_input: bool  # Track if we're waiting for user input for concept expansion
    concept_expansion_context: Dict  # Context for concept expansion

    # New fields for user idea input
    awaiting_idea_input: bool  # Track if we're waiting for user idea input
    idea_input_context: Dict  # Context for user idea input

    # New fields for branch deletion
    awaiting_deletion_confirmation: bool  # Track if we're waiting for deletion confirmation
    deletion_context: Dict  # Context for branch deletion

    # New fields for concept combination
    combination_context: Dict  # Stores the branches to be combined
    switch_thread: bool  # Flag for switching between threads

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.8,
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
   - Ask yourself: "After this problem is solved, what do we want to see happening? Why do we need to solve this problem in the first place?"
   - Write this down as your `preferable_outcome`.

3. Extract the core assumption or idea in the original statement
	 - Ask yourself: "What is the indispensible part of this problem statement? What is the most conventional way to solve this problem?"
	 - Write this down as your 'assumption'.

4. Brainstorm an Alternate Way without following the core assumption to Achieve the Same Outcome
   - Disregard the 'assumption', or completely flip it, and think of another perspective that can still achieve the `preferable_outcome`.
   - Think outside the box—be wild and bold.
   - "Gamification" is not the solution to everything. Consider other possibilities first.

5. Create a Second Problem Statement, and form `problem_statement_2`
   - Using the alternate approach, form another "How might we…" statement:
     "How might we + [alternate method] + [preferable_outcome]?"

6. Output Requirement:
   - Output only the `problem_statement_2` (the newly formed "How might we…" statement), and a short explanation of how the assumption is flipped, each as a single sentence.
   - Do not include any explanation or additional text.
   - Each should beo longer than 20 words.
   - Output format:
     "problem_statement_2": "How might we…",
     "explanation": "How the assumption is flipped"
   """)
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
1. Task: List 2 relevant key human habits or heuristics (e.g., preference for consistency) and use it as 'heading'.
2. Add-on: Explain how the habit is tied to the problem and brainstorm 1 direction that cleverly leverages or strengthens these habits.
3. Tip: Think beyond the obvious. Explore how established routines, comfort zones, or mental shortcuts can be nudged in creative ways to improve engagement and satisfaction.

c. Delightful Subversion
1. Task: Describe how 2 commonly negative or taboo perceptions/frustrations can be turned into positive experiences in 'heading' (heading example: Turning distraction into exploration).
2. Add-on: Explain in detail how each could be flipped into something playful, intriguing, or surprisingly positive. Then brainstorm 1 relevant product direction.
3. Tip: Push your creativity here! Consider surprise-and-delight mechanics, or turning negative emotions into rewards that reshape the user's emotional journey.

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
      "heading": "...",
      "explanation": "...",
      "productDirection": "..."
    }}
  ],
  "delightfulSubversion": [
    {{
      "heading": "...",
      "explanation": "...",
      "productDirection": "..."
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
Identify Attributes: Choose 3 defining attributes or characteristics of the problem concept (e.g., "it requires active maintenance," "it thrives on collaboration," or "it's quick to appear but slow to sustain").
Cross-Domain Link: For each attribute, select one concept from a completely different field—technology, biology, art, history, sports, etc.—that also exhibits or relies on this same attribute. Add the domain name in parenthesis in 'heading'. 
Insight & Product Direction: Explain how the unexpected link can spark new understanding or design ideas for the problem. Propose one product direction based on this analogy.
     
b. Broader Domains
Explore the problem from 4 different perspectives from experts in different fields. How is their domain knowledge relevant to this topic? Summarize the connection between the problem statement and the domain as 'heading' (DO NOT include '...'s Perspective' in the heading, be more specific about content), and then describe how each uniquely interprets the problem as 'explanation'.
For each perspective, propose one idea or feature that draws inspiration from that viewpoint as 'productDirection'.

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
  ]
}}""")
])

# Template for "Imaginary Customers' Feedback" exploration - placeholder for future implementation
IMAGINARY_FEEDBACK_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    MessagesPlaceholder(variable_name="thread_messages"),
    ("human", """Please follow these steps to explore imaginary customers' feedback behind {problem_statement}. Please return only valid JSON in the exact structure specified below. Use concise phrasing (one or two sentences per field).
a. Create 5 Imaginary Target Users & Their Feedback
Heading: Use a normative, fact-based heading that states the core pain point directly (e.g., “News is not personalized to my niche market,”). Ensure each pain point reflects a distinct perspective—mental, physical, emotional, etc.—and is not overlapping. Each pain point is directly tied to at least one detail in that user’s profile (e.g., job context, personal routine, or environment). Then, explain this pain point in a single concise sentence.
Invent Personas: Come up with 5 diverse, highly specific user profiles, each having a short description for 'userProfile'. Each persona must differ significantly in either background, industry, occupation, age, or daily habits.
explanation: Explain the pain point in more details.

b. Respond with Potential Product Directions
Link to Feedback: For each feedback item, propose a concise product direction that addresses or alleviates the user's struggle.
Practical Innovations: Focus on new features, design improvements, or creative innovations that respond to the user's specific needs or pain points.

Please follow this example of valid output:
[
  {{
    "heading": "Notifications are very distracting.",
    "userProfile": "Emma, 26, Remote Designers. Works from coffee shops, juggling multiple freelance clients and productivity tools.",
    "explanation": "I can get distracted by notifications from different platforms fairly easy",
    "productDirection": "Implement an automatic 'focus mode' that silences unrelated notifications during task time."
  }}
 ]""")
])

# New template for concept expansion
CONCEPT_EXPANSION_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    ("human", """The problem statement we are trying to solve is: {problem_statement}. {context}, I want to further explore and expand on this concept: {concept_to_expand}

Here's the prompt: {user_guidance} Please provide 3 relevant and creative responses to this prompt. 

Please return only valid JSON without any extra text or explanation. Format your response as JSON with these sections: [
{{
  "heading": "Specific descriptive heading for this direction",
  "explanation": "Deeper analysis of the concept",
  "productDirection": "description of the product concept"
}}
]""")
])

# New function for concept expansion with default guidance
DEFAULT_GUIDANCE_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    ("human", """Please generate the most relevant and simplest one-sentence question to this concept: {concept_to_expand} that would help expand this single concept into more branches. The output should only include the question, no other text or explanation. Do not include "gamification" or anything related in your answer.
Good example: What are some typical forms of Fear of Missing Out (FOMO)?""")
])

USER_IDEA_STRUCTURING_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    ("human", """Please structure this user idea into a JSON format with the following fields:
1. "heading": A concise and faithful description of user input (5-7 words)
2. "explanation": A brief explanation of this concept (1-2 sentences)
3. "productDirection": A practical product direction for solving or leveraging this concept (1-2 sentences)

The user's idea is related to this problem: {problem_statement}
The parent branch is: {parent_heading}: {parent_content}

User idea: {user_idea}

Return ONLY valid JSON without any additional explanation. Example format:
{{
  "heading": "Concise and specific descriptive heading of the concept",
  "explanation": "Brief explanation of what the idea entails.",
  "productDirection": "Practical implementation direction for the product."
}}""")
])

# Define the prompt template for concept combination
CONCEPT_COMBINATION_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_TEMPLATE),
    ("human", """Please combine the distinct concepts below to solve the following problem in an ingenious, surprising, yet still feasible manner: {problem_statement}

Concept 1: {concept1_heading}
{concept1_content}

Concept 2: {concept2_heading}
{concept2_content}

{additional_concepts}

Create 1 innovative product idea that integrate the key elements from all these concepts. The idea should:
1. Methodologies: Choose the approach (or approaches) you find most relevant from the following concise options:
	a. Analogy Swapping: Borrow one concept’s structure or approach and apply it to the other’s domain.
	b. Role Reversal: Flip the assumptions of one concept to serve the opposite goal within the other.
	c. Constraint Merging: Impose the limitations from one concept onto the other to spark fresh solutions.
	d. Hybridization: Blend each concept’s unique strengths to create something more robust.
	e. Layering Concepts: Let one concept be the “engine” while the other shapes the user-facing experience.
2. Incorporate essential elements from all concepts and highlight the “secret sauce” or synergy that emerges from blending these unique elements.
3. Push boundaries with your idea—be unconventional, unexpected, or playful.
4. Maintain a tether to feasibility (e.g., physically possible, practical within a real-world context).
5. You can propose new or expanded features if they strengthen the synergy or help solve the problem more effectively.

Return only valid JSON with these sections for this idea:
{{
    "heading": "Clear and specific product name/concept (7-10 words)",
    "explanation": "Explain how this concept works and what makes it unique (1-2 sentences)",
    "featureLists": ["List of features for the product"],
    "sourceConcepts": ["List of concept headings that contributed to this idea"]
}}
""")
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
    
    # Initialize branch-related fields
    state["branches"] = {}
    state["branch_counter"] = 0
    state["active_branch"] = None
    state["awaiting_branch_choice"] = False
    state["awaiting_concept_input"] = False
    state["concept_expansion_context"] = {}
    
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
    """Generate an alternative problem statement (problem_statement_2) with explanation of how the assumption is flipped."""
    if not state.get("problem_statement"):
        state["problem_statement_2"] = "Error: No problem statement to work with."
        state["explanation"] = ""
        return state

    try:
        # Create prompt with the current problem statement
        prompt = PROBLEM_REFINEMENT_PROMPT.format_messages(
            problem_statement=state["problem_statement"]
        )
        
        # Generate response
        response = llm.invoke(prompt)
        response_content = response.content.strip()
        
        # Extract problem statement and explanation
        problem_statement_2 = ""
        explanation = ""
        
        # Try to parse JSON-like format first
        try:
            import json
            import re
            
            # Check if the response follows the requested format structure
            # Looking for "problem_statement_2": "How might we..." and "explanation": "How the assumption..."
            ps2_match = re.search(r'"problem_statement_2"\s*:\s*"(.*?)"', response_content, re.DOTALL)
            exp_match = re.search(r'"explanation"\s*:\s*"(.*?)"', response_content, re.DOTALL)
            
            if ps2_match and exp_match:
                problem_statement_2 = ps2_match.group(1).strip()
                explanation = exp_match.group(1).strip()
            else:
                # Alternative pattern: look for key-value pairs without strict JSON syntax
                ps2_match = re.search(r'problem_statement_2[:\s]+(.*?)(?:,|\n|$)', response_content, re.DOTALL)
                exp_match = re.search(r'explanation[:\s]+(.*?)(?:,|\n|$)', response_content, re.DOTALL)
                
                if ps2_match:
                    problem_statement_2 = ps2_match.group(1).strip().strip('"\'')
                if exp_match:
                    explanation = exp_match.group(1).strip().strip('"\'')
            
            # If still not found, try to parse as complete JSON object
            if not problem_statement_2 or not explanation:
                # Try to find a JSON object in the response
                json_pattern = re.search(r'({.*})', response_content, re.DOTALL)
                if json_pattern:
                    try:
                        json_str = json_pattern.group(1)
                        # Fix common issues in the JSON string
                        json_str = json_str.replace('problem_statement_2:', '"problem_statement_2":')
                        json_str = json_str.replace('explanation:', '"explanation":')
                        json_str = json_str.replace("'", '"')
                        
                        # Parse the JSON
                        json_data = json.loads(json_str)
                        
                        if "problem_statement_2" in json_data:
                            problem_statement_2 = json_data["problem_statement_2"]
                        if "explanation" in json_data:
                            explanation = json_data["explanation"]
                    except json.JSONDecodeError:
                        pass  # Continue to other methods if JSON parsing fails
            
            # If we still don't have a problem statement, look for "How might we" statements
            if not problem_statement_2:
                hmw_statements = re.findall(r"How might we[^.?!]*[.?!]", response_content)
                if hmw_statements:
                    problem_statement_2 = hmw_statements[-1].strip()
            
            # If we still don't have an explanation, try to find anything after "explanation" keyword
            if not explanation:
                ex_pattern = re.search(r'[Ee]xplanation:?\s+(.*?)(?:\n\n|\Z)', response_content, re.DOTALL)
                if ex_pattern:
                    explanation = ex_pattern.group(1).strip()
        
        except Exception as e:
            print(f"Error parsing response in problem statement 2: {str(e)}")
            # Fallback to simpler approach if parsing fails
            hmw_statements = re.findall(r"How might we[^.?!]*[.?!]", response_content)
            if hmw_statements:
                problem_statement_2 = hmw_statements[-1].strip()
        
        # Store the second problem statement and explanation
        state["problem_statement_2"] = problem_statement_2
        state["explanation"] = explanation
        
        # Only append to messages if it's not a regeneration or if messages doesn't already contain Statement 2
        if not state["regenerate_problem_statement_2"] or not any(msg.content.startswith("Statement 2:") for msg in state["messages"] if isinstance(msg, AIMessage)):
            message_content = f"Statement 2: {problem_statement_2}"
            if explanation:
                message_content += f"\nExplanation: {explanation}"
            state["messages"].append(AIMessage(content=message_content))
        else:
            # Replace the existing Statement 2 message
            message_content = f"Statement 2: {problem_statement_2}"
            if explanation:
                message_content += f"\nExplanation: {explanation}"
            
            for i, msg in enumerate(state["messages"]):
                if isinstance(msg, AIMessage) and msg.content.startswith("Statement 2:"):
                    state["messages"][i] = AIMessage(content=message_content)
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
        import traceback
        print(f"Error in generate_problem_statement_2: {str(e)}")
        print(traceback.format_exc())
        state["problem_statement_2"] = f"Error generating problem statement 2: {str(e)}"
        state["explanation"] = ""
        return state

def request_choice(state: IdeationState) -> IdeationState:
    """Request user to choose between the two problem statements or regenerate either statement."""
    # Simply prepare the state for user choice without calling the LLM
    state["awaiting_choice"] = True
    # Include the explanation in the display if available
    statement_2_display = state["problem_statement_2"]
    if state.get("explanation"):
        statement_2_display += f"\nExplanation: {state['explanation']}"

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

def display_problem_statement_choices(state):
    """Helper function to display problem statement choices with explanations."""
    print("Please choose which problem statement to use:")
    print(f"1. Statement 1: {state['problem_statement']}")
    
    # Display statement 2 with explanation if available
    statement_2_text = f"2. Statement 2: {state['problem_statement_2']}"
    if state.get("explanation"):
        statement_2_text += f"\n   Explanation: {state['explanation']}"
    print(statement_2_text)
    
    print("r1. Regenerate Statement 1")
    print("r2. Regenerate Statement 2")
    

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
    """Present the exploration options to the user, including all combined concepts threads."""
    # If this is the first time, set up the threads and mindmap
    if not state["threads"]:
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
                "messages": [SystemMessage(content=SYSTEM_TEMPLATE)],  # Each thread has its own message history
                "branches": {}  # Initialize branches for this thread
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
    
    # Get all thread options including combined concepts
    thread_options = get_thread_options_display(state)
    
    # Transform into dictionary for input_instructions
    options_dict = {}
    for option in thread_options:
        options_dict[str(option["index"])] = f"{option['name']}: {option['description']}"
    
    state["input_instructions"] = {
        "thread_choice": "Choose an exploration approach:",
        "options": options_dict
    }
    state["current_step"] = "await_thread_choice"
    
    return state

def get_thread_options_display(state: IdeationState) -> list:
    """Get a formatted list of thread options for display.
    This can be used by any interface (CLI, web, etc.)."""
    options = []
    
    # Use the existing threads state
    for i in range(1, 4):  # We have 3 fixed threads
        thread_id = f"thread_{i}"
        if thread_id in state["threads"]:
            thread = state["threads"][thread_id]
            name = thread["name"]
            desc = thread["description"]
            status = ""
            
            # Add status indicators if a thread is active or has been explored
            if state["active_thread"] == thread_id:
                status += " (current)"
            
            if len(thread["messages"]) > 1:
                status += " (explored)"
                
            options.append({
                "index": i,
                "id": thread_id,
                "name": name,
                "description": desc,
                "status": status,
                "display": f"{i}. {name}: {desc}{status}"
            })
    
    # Add combined concept threads
    counter = len(options) + 1
    for thread_id, thread in state["threads"].items():
        if thread_id.startswith("thread_combined_"):
            name = thread["name"]
            desc = thread["description"]
            status = ""
            
            if state["active_thread"] == thread_id:
                status += " (current)"
                
            options.append({
                "index": counter,
                "id": thread_id,
                "name": name,
                "description": desc,
                "status": status,
                "display": f"{counter}. {name}: {desc}{status}"
            })
            counter += 1
    
    return options

def process_thread_choice_multi(state: IdeationState, choice: str) -> IdeationState:
    """Process the user's choice of which exploration approach to use."""
    # Reset switching flag
    state["switch_thread"] = False
    
    # Check for "stop" command
    if choice.lower().strip() == "stop":
        state["current_step"] = "end_session"
        state["feedback"] = "Ending the ideation session as requested."
        return state
    
    # Check for special commands
    if "combine" in choice.lower():
        return process_combine_request(state, choice)
    
    if choice.lower().strip().startswith('b'):
        return process_branch_selection(state, choice)
    
    if "delete" in choice.lower():
        return process_delete_request(state, choice)
    
    if "add idea" in choice.lower():
        return process_add_idea_request(state, choice)
    
    # Get all thread options for display/selection
    thread_options = get_thread_options_display(state)
    
    # Try to match by index number
    try:
        selected_index = int(choice.strip())
        selected_option = next((opt for opt in thread_options if opt["index"] == selected_index), None)
        
        if selected_option:
            thread_id = selected_option["id"]
        else:
            state["feedback"] = f"Invalid thread number: {selected_index}. Please select a valid option."
            state["switch_thread"] = True
            return state
            
    except ValueError:
        # Try to match by name
        normalized_choice = choice.lower().strip()
        
        # First check standard methodology threads
        thread_map = {
            "emotional": "thread_1",
            "emotional root": "thread_1",
            "emotional root causes": "thread_1",
            "root causes": "thread_1",
            "unconventional": "thread_2",
            "unconventional associations": "thread_2",
            "associations": "thread_2",
            "imaginary": "thread_3",
            "feedback": "thread_3",
            "imaginary customers": "thread_3",
            "customers feedback": "thread_3",
            "imaginary customers' feedback": "thread_3"
        }
        
        thread_id = thread_map.get(normalized_choice)
        
        # If not found in standard map, try to match combined concept threads by name
        if not thread_id:
            for opt in thread_options:
                if opt["name"].lower() in normalized_choice or normalized_choice in opt["name"].lower():
                    thread_id = opt["id"]
                    break
        
        if not thread_id:
            state["feedback"] = "Invalid choice. Please select a valid option."
            state["switch_thread"] = True
            return state
    
    # Set the active thread
    is_reselection = (thread_id == state["active_thread"] and 
                       len(state["threads"][thread_id]["messages"]) > 1)
    
    # If re-selecting, reset the thread's branches and clear exploration data
    if is_reselection and not thread_id.startswith("thread_combined_"):
        # For methodology threads, allow regeneration
        # Keep track of branches to remove from global registry
        branches_to_remove = []
        for branch_id, branch in state["branches"].items():
            if branch["thread_id"] == thread_id:
                branches_to_remove.append(branch_id)
        
        # Remove branches from global registry
        for branch_id in branches_to_remove:
            del state["branches"][branch_id]
        
        # Reset thread's branches and exploration data
        state["threads"][thread_id]["branches"] = {}
        if "exploration_data" in state["threads"][thread_id]:
            del state["threads"][thread_id]["exploration_data"]
        
        # Reset mindmap children for this thread
        thread_node = next((node for node in state["mindmap"]["children"] if node["id"] == thread_id), None)
        if thread_node:
            thread_node["children"] = []
            if "exploration_data" in thread_node:
                del thread_node["exploration_data"]
        
        # Add a message indicating regeneration
        state["messages"].append(HumanMessage(
            content=f"I'd like to regenerate ideas for the {state['threads'][thread_id]['name']} approach."
        ))
        
        # Add a new message to start the exploration from scratch
        thread_message = HumanMessage(
            content=f"Let's explore the problem statement through the lens of {state['threads'][thread_id]['name']} again."
        )
        state["threads"][thread_id]["messages"].append(thread_message)
    
    state["active_thread"] = thread_id
    state["active_branch"] = None  # Reset active branch when switching threads
    
    # Only add messages if this is the first time selecting this thread
    # (for methodology threads)
    if not thread_id.startswith("thread_combined_") and len(state["threads"][thread_id]["messages"]) <= 1:
        # Add user choice to main messages
        state["messages"].append(HumanMessage(content=f"I choose to explore {state['threads'][thread_id]['name']}."))
        
        # Add the choice to thread-specific messages
        thread_message = HumanMessage(content=f"Let's explore the problem statement through the lens of {state['threads'][thread_id]['name']}.")
        state["threads"][thread_id]["messages"].append(thread_message)
        
        # Acknowledge the selection
        thread_name = state["threads"][thread_id]["name"]
        state["messages"].append(AIMessage(content=f"Great! We'll explore '{state['final_problem_statement']}' through the {thread_name} approach. This thread now has its own separate conversation history."))
    
    # For combined concept threads or methodology threads, set appropriate next step
    if thread_id.startswith("thread_combined_"):
        # For combined concept threads, just acknowledge selection
        thread_name = state["threads"][thread_id]["name"]
        state["messages"].append(HumanMessage(content=f"I want to work with the combined concept: {thread_name}"))
        state["messages"].append(AIMessage(content=f"Switched to the combined concept: {thread_name}. You can expand on this concept or add your own ideas to it."))
        state["current_step"] = "present_exploration_options"
    else:
        # For methodology threads, set up for thread exploration
        state["current_step"] = "thread_exploration"
    
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

        # DEBUG: Print the raw LLM response
        print("\n===== DEBUG: RAW LLM RESPONSE =====")
        print(response_content)
        print("===== END RAW RESPONSE =====\n")
        
        # Add the LLM response to the thread messages
        state["threads"][thread_id]["messages"].append(AIMessage(content=response_content))
        
        # Add a notification to the main message history
        notification = f"Explored '{state['final_problem_statement']}' through the {thread_name} approach."
        state["messages"].append(AIMessage(content=notification))
        
        # Try to parse JSON from the response
        try:
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
            
            # Create branches for this thread based on the exploration data
            create_branches_from_exploration(state, thread_id, json_data)
            
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

def create_branches_from_exploration(state: IdeationState, thread_id: str, json_data: dict) -> None:
    """Create branches from the exploration data."""
    # Get access to the thread and its branches
    thread = state["threads"][thread_id]
    thread_name = thread["name"]
    
    # Process based on thread type
    branches = []
    
    if thread_id == "thread_1":  # Emotional Root Causes
        # Extract emotional seeds
        if "emotionalSeeds" in json_data:
            for idx, item in enumerate(json_data["emotionalSeeds"]):
                branches.append({
                    "heading": item["heading"],
                    "explanation": item["explanation"],
                    "productDirection": item["productDirection"],
                    "source": "emotionalSeeds",
                    "source_idx": idx
                })
                
        # Extract habit & heuristic alignment
        if "habitHeuristicAlignment" in json_data:
            for idx, item in enumerate(json_data["habitHeuristicAlignment"]):
                branches.append({
                    "heading": item["heading"],
                    "explanation": item["explanation"],
                    "productDirection": item["productDirection"],
                    "source": "habitHeuristicAlignment",
                    "source_idx": idx
                })
                
        # Extract delightful subversion
        if "delightfulSubversion" in json_data:
            for idx, item in enumerate(json_data["delightfulSubversion"]):
                branches.append({
                    "heading": item["heading"],
                    "explanation": item["explanation"],
                    "productDirection": item["productDirection"],
                    "source": "delightfulSubversion",
                    "source_idx": idx
                })
    
    elif thread_id == "thread_2":  # Unconventional Associations
        # Extract attribute-based bridging
        if "attributeBasedBridging" in json_data:
            for idx, item in enumerate(json_data["attributeBasedBridging"]):
                branches.append({
                    "heading": item["heading"],
                    "explanation": item["explanation"],
                    "productDirection": item["productDirection"],
                    "source": "attributeBasedBridging",
                    "source_idx": idx
                })
                
        # Extract broader domains
        if "broaderDomains" in json_data:
            for idx, item in enumerate(json_data["broaderDomains"]):
                branches.append({
                    "heading": item["heading"],
                    "explanation": item["explanation"],
                    "productDirection": item["productDirection"],
                    "source": "broaderDomains",
                    "source_idx": idx
                })
    
    elif thread_id == "thread_3":  # Imaginary Customers' Feedback
        # Handle the array format for this thread
        if isinstance(json_data, list):
            for user_idx, user_item in enumerate(json_data):
                branches.append({
                    "heading": user_item.get("heading", f"User {user_idx+1}"),
                    "explanation": user_item.get("explanation", ""),
                    "productDirection": user_item.get("productDirection", ""),
                    "userProfile": user_item.get("userProfile", ""),
                    "source": "imaginaryFeedback",
                    "source_idx": user_idx
                })
    
    # Add branches to the state with unique IDs
    for branch_data in branches:
        branch_id = f"b{state['branch_counter'] + 1}"
        state['branch_counter'] += 1
        
        # Ensure branch data is standardized for concept category
        branch_data = standardize_concept_branch_data(branch_data)
        
        # Generate content field for display purposes
        content = f"{branch_data['explanation']}"
        if branch_data.get('productDirection'):
            content += f" Product direction: {branch_data['productDirection']}"
        if thread_id == "thread_3" and branch_data.get('userProfile'):
            content = f"User: {branch_data['userProfile']}\nFeedback: {content}"
        
        # Create the branch
        new_branch = {
            "id": branch_id,
            "thread_id": thread_id,
            "heading": branch_data["heading"],
            "content": content,  # Keep content for backwards compatibility
            "explanation": branch_data["explanation"],
            "productDirection": branch_data["productDirection"],
            "source": branch_data.get("source", ""),
            "parent_branch": None,  # Top-level branches have no parent
            "children": [],  # Initialize empty children list
            "expanded": False,  # Track if this branch has been expanded
            "expansion_data": None,  # Will store expansion data when expanded
            "category": "concept"  # Explicitly mark as concept category
        }
        
        # Add userProfile for imaginary feedback branches
        if thread_id == "thread_3" and "userProfile" in branch_data:
            new_branch["userProfile"] = branch_data["userProfile"]
        
        # Add to global branches registry and thread-specific branches
        state["branches"][branch_id] = new_branch
        thread["branches"][branch_id] = new_branch
        
        # Add to mindmap
        thread_node = next((node for node in state["mindmap"]["children"] if node["id"] == thread_id), None)
        if thread_node:
            # Add branch to thread node's children
            branch_node = {
                "id": branch_id,
                "name": branch_data["heading"],
                "content": content,
                "explanation": branch_data["explanation"],
                "productDirection": branch_data["productDirection"],
                "children": []  # Initialize empty children for future expansions
            }
            # Add userProfile for imaginary feedback branches
            if thread_id == "thread_3" and "userProfile" in branch_data:
                branch_node["userProfile"] = branch_data["userProfile"]
            
            thread_node["children"].append(branch_node)


def generate_default_guidance(state: IdeationState, branch_id: str) -> str:
    """Generate contextually relevant default guidance for concept expansion."""
    branch = state["branches"][branch_id]
    
    try:
        # Create prompt for generating default guidance
        prompt = DEFAULT_GUIDANCE_PROMPT.format_messages(
            problem_statement=state["final_problem_statement"],
            concept_to_expand=f"{branch['heading']}: {branch['content']}",
            context=f"From {state['threads'][branch['thread_id']]['name']} exploration."
        )
        
        # Invoke the LLM
        response = llm.invoke(prompt)
        default_guidance = response.content.strip()
        
        # Clean up the response if needed (remove quotes, etc.)
        if default_guidance.startswith('"') and default_guidance.endswith('"'):
            default_guidance = default_guidance[1:-1]
        
        return default_guidance
        
    except Exception as e:
        # Fallback to static default if generation fails
        print(f"Error generating default guidance: {str(e)}")
        return DEFAULT_GUIDANCE_PROMPT


def display_available_branches(state: IdeationState) -> None:
    """Format and display available branches for selection with hierarchy."""
    # Check if there are any branches
    if not state["branches"]:
        print("No branches available yet. Please explore a thread first.")
        return
    
    print("\n===== AVAILABLE BRANCHES =====")

    # Create a set to track branches that have been displayed
    displayed_branches = set()

    # Group branches by thread
    for thread_id, thread in state["threads"].items():
        thread_name = thread["name"]
        
        # Find top-level branches for this thread (those with no parent)
        top_level_branches = [b for b_id, b in state["branches"].items() 
                             if b["thread_id"] == thread_id and b["parent_branch"] is None]
        
        if top_level_branches:
            # For combined concept threads, display their branch ID in the thread header
            thread_branch_id = ""
            if thread_id.startswith("thread_combined_"):
                # Get the first branch in this thread (the combined concept itself)
                if top_level_branches:
                    thread_branch_id = f" [{top_level_branches[0]['id']}]"
            
            print(f"\n{thread_name}{thread_branch_id}:")
            
            # Display each top-level branch and its children
            for branch in top_level_branches:
                branch_id = branch["id"]
                expanded_marker = " [expanded]" if branch["expanded"] else ""
                current_marker = " *" if state["active_branch"] == branch_id else ""
                
                # Add source concepts indicator for combined concepts
                source_concepts = ""
                if "source_concepts" in branch:
                    source_concepts = f" (from {', '.join(branch['source_concepts'])})"
                
                # Add category indicator for clarity
                category_marker = f" [{branch.get('category', 'concept')}]"
                
                print(f"  {branch_id}{current_marker}: {branch['heading']}{expanded_marker}{source_concepts}{category_marker}")
                
                # Display content based on branch category
                if branch.get("category") == "product":
                    # Product category display format
                    print(f"      Description: {branch.get('description', '')}")
                    
                    # Display features list
                    features = branch.get("features", [])
                    if features:
                        print("      Features:")
                        for feature in features:
                            print(f"      - {feature}")
                else:
                    # Concept category display format
                    if "explanation" in branch:
                        print(f"      Explanation: {branch['explanation']}")
                    if "productDirection" in branch:
                        print(f"      Product Direction: {branch['productDirection']}")
                    if "userProfile" in branch:
                        print(f"      User Profile: {branch['userProfile']}")
                
                print()  # Empty line for better readability
                
                # Track this branch as displayed
                displayed_branches.add(branch_id)
                
                # Display children branches if any
                if branch["children"]:
                    display_child_branches(state, branch, displayed_branches, indent=4)
    
    print("\n=============================")

def display_child_branches(state: IdeationState, parent_branch: dict, displayed_branches: set, indent: int = 4):
    """Helper function to display child branches recursively."""
    for child_id in parent_branch["children"]:
        # Skip if already displayed
        if child_id in displayed_branches:
            continue
            
        child = state["branches"].get(child_id)
        if child:
            expanded_marker = " [expanded]" if child["expanded"] else ""
            current_marker = " *" if state["active_branch"] == child_id else ""
            
            # Add category indicator for clarity
            category_marker = f" [{child.get('category', 'concept')}]"
            
            # Display the child branch with proper indentation
            indent_spaces = " " * indent
            print(f"{indent_spaces}{child_id}{current_marker}: {child['heading']}{expanded_marker}{category_marker}")
            
            # Display content based on branch category
            if child.get("category") == "product":
                # Product category display format
                print(f"{indent_spaces}    Description: {child.get('description', '')}")
                
                # Display features list
                features = child.get("features", [])
                if features:
                    print(f"{indent_spaces}    Features:")
                    for feature in features:
                        print(f"{indent_spaces}    - {feature}")
            else:
                # Concept category display format
                if "explanation" in child:
                    print(f"{indent_spaces}    Explanation: {child['explanation']}")
                if "productDirection" in child:
                    print(f"{indent_spaces}    Product Direction: {child['productDirection']}")
                if "userProfile" in child:
                    print(f"{indent_spaces}    User Profile: {child['userProfile']}")
            
            print()  # Empty line for better readability
            
            # Track this branch as displayed
            displayed_branches.add(child_id)
            
            # Recursively display this branch's children
            if child["children"]:
                display_child_branches(state, child, displayed_branches, indent + 4)

def process_branch_selection(state: IdeationState, choice: str) -> IdeationState:
    """Process user's selection of a branch."""
    # Extract branch ID from choice (e.g., "b1", "b23")
    branch_match = re.match(r'b(\d+)', choice.lower().strip())
    if not branch_match:
        state["feedback"] = "Invalid branch selection format. Use 'b' followed by the branch number (e.g., b1, b2)."
        return state
    
    branch_num = branch_match.group(1)
    branch_id = f"b{branch_num}"
    
    # Check if branch exists
    if branch_id not in state["branches"]:
        state["feedback"] = f"Branch {branch_id} does not exist."
        return state
    
    # Set the active branch
    state["active_branch"] = branch_id
    branch = state["branches"][branch_id]
    
    # Set the active thread to the branch's thread
    state["active_thread"] = branch["thread_id"]
    
    # Add message about branch selection
    state["messages"].append(HumanMessage(content=f"I want to explore branch {branch_id}: {branch['heading']}"))
    
    # If the branch has already been expanded, show the expansion
    if branch["expanded"] and branch["expansion_data"]:
        # Create a response from the existing expansion data
        expansion_data = branch["expansion_data"]
        
        # Format a response showing the expansion
        response = f"Here's the existing expansion for {branch_id}: {branch['heading']}\n\n"
        response += f"Analysis: {expansion_data.get('analysis', '')}\n\n"
        
        # Add applications
        response += "Applications:\n"
        for app in expansion_data.get("applications", []):
            response += f"- {app.get('heading', '')}: {app.get('explanation', '')}\n"
        
        response += "\nWould you like to expand on a specific aspect or create a new expansion?"
        
        state["messages"].append(AIMessage(content=response))
        state["current_step"] = "branch_expansion_options"
    else:
        # Set up for concept expansion input
        state["awaiting_concept_input"] = True
        state["concept_expansion_context"] = {
            "branch_id": branch_id,
            "heading": branch["heading"],
            "content": branch["content"]
        }

        # Generate suggested guidance
        suggested_guidance = generate_default_guidance(state, branch_id)
        state["concept_expansion_context"]["suggested_guidance"] = suggested_guidance
        
        # Update input instructions
        state["input_instructions"] = {
            "concept_guidance": f"How would you like to expand branch {branch_id}: {branch['heading']}?\n(Enter your guidance or press Enter to use the suggestion below)\n\nSuggested guidance: {suggested_guidance}"
        }
        
        state["current_step"] = "await_concept_input"
        state["messages"].append(AIMessage(content=f"Selected branch {branch_id}: {branch['heading']}. Please provide any specific guidance for expanding this concept, or press Enter to use default guidance."))
    
    return state

def process_concept_input(state: IdeationState, user_input: str) -> IdeationState:
    """Process user input for concept expansion."""
    # Get branch information
    branch_id = state["concept_expansion_context"]["branch_id"]
    branch = state["branches"][branch_id]
    
    # Use the suggested guidance if no input provided
    if not user_input.strip():
        concept_guidance = state["concept_expansion_context"]["suggested_guidance"]
        print(f"Using suggested guidance: {concept_guidance}")
        user_message = f"I'll use the suggested guidance: {concept_guidance}"
    else:
        concept_guidance = user_input.strip()
        user_message = concept_guidance
    
    # Update the context with the guidance
    state["concept_expansion_context"]["guidance"] = concept_guidance
    state["messages"].append(HumanMessage(content=concept_guidance if user_input.strip() else "Please proceed with default guidance."))
    
    # Reset awaiting flag
    state["awaiting_concept_input"] = False
    
    # Move to concept expansion
    state["current_step"] = "expand_concept"
    
    return state

def expand_concept(state: IdeationState) -> IdeationState:
    """Expand a concept based on user guidance."""
    # Get concept information from context
    context = state["concept_expansion_context"]
    branch_id = context["branch_id"]
    branch = state["branches"][branch_id]
    
    try:
        # Create prompt for concept expansion
        prompt = CONCEPT_EXPANSION_PROMPT.format_messages(
            concept_to_expand=f"{branch['heading']}: {branch['content']}",
            context=f"From {state['threads'][branch['thread_id']]['name']} perspective",
            problem_statement=state["final_problem_statement"],
            user_guidance=context["guidance"]
        )
        
        # Invoke the LLM
        response = llm.invoke(prompt)
        response_content = response.content.strip()
        
        # Strip markdown code block formatting if present
        response_content = strip_markdown_code_blocks(response_content)

        # Try to parse JSON from the response
        try:
            # Parse the JSON
            json_data = json.loads(response_content)
            
            # Normalize the JSON structure
            expanded_concepts = []
            
            # If JSON is an array, use it directly as expanded concepts
            if isinstance(json_data, list):
                expanded_concepts = json_data
                # Also store in a structured format for consistency
                json_data = {"expandedConcepts": expanded_concepts}
                print("Converted JSON array to object with expandedConcepts field")
            # If JSON is a dictionary, look for expandedConcepts field
            elif isinstance(json_data, dict):
                expanded_concepts = json_data.get("expandedConcepts", [])
            
            # Mark the branch as expanded and store expansion data
            branch["expanded"] = True
            branch["expansion_data"] = json_data
            
            # Create sub-branches from the expanded concepts
            for idx, concept in enumerate(expanded_concepts):
                # Standardize the concept data
                concept = standardize_concept_branch_data(concept)
                
                # Create a new branch for each expanded concept
                sub_branch_id = f"b{state['branch_counter'] + 1}"
                state['branch_counter'] += 1
                
                # Generate content field for display purposes
                content = f"{concept['explanation']}"
                if concept.get('productDirection'):
                    content += f" Product Direction: {concept['productDirection']}"
                
                # Create the sub-branch with standardized fields
                sub_branch = {
                    "id": sub_branch_id,
                    "thread_id": branch["thread_id"],
                    "heading": concept["heading"],
                    "content": content,  # Keep content for backwards compatibility
                    "explanation": concept["explanation"],
                    "productDirection": concept["productDirection"],
                    "source": "concept_expansion",
                    "parent_branch": branch_id,
                    "children": [],
                    "expanded": False,
                    "expansion_data": None,
                    "category": "concept"  # Explicitly mark as concept category
                }
                
                # Add to global branches registry
                state["branches"][sub_branch_id] = sub_branch
                
                # Add to parent branch's children list
                branch["children"].append(sub_branch_id)
                
                # Add to mindmap
                thread_node = next((node for node in state["mindmap"]["children"] if node["id"] == branch["thread_id"]), None)
                if thread_node:
                    branch_node = next((node for node in thread_node["children"] if node["id"] == branch_id), None)
                    if branch_node:
                        # Add sub-branch to branch node's children
                        sub_branch_node = {
                            "id": sub_branch_id,
                            "name": concept["heading"],
                            "content": content,
                            "explanation": concept["explanation"],
                            "productDirection": concept["productDirection"],
                            "children": []
                        }
                        branch_node["children"].append(sub_branch_node)
            
            # Format a user-friendly response showing expansion results
            result_message = format_expansion_results(json_data, branch_id, branch["heading"], expanded_concepts)
            state["messages"].append(AIMessage(content=result_message))
            
            state["feedback"] = f"Successfully expanded concept '{branch['heading']}' and created {len(expanded_concepts)} sub-branches."
            
        except Exception as json_error:
            # JSON parsing failed
            print(f"Note: Could not parse JSON from expansion response: {str(json_error)}")
            
            # Store the raw response as expansion data
            branch["expanded"] = True
            branch["expansion_data"] = {"raw_response": response_content}
            
            # Add raw response to messages
            state["messages"].append(AIMessage(content=f"Expanded concept '{branch['heading']}':\n\n{response_content}"))
            
            state["feedback"] = f"Expanded concept '{branch['heading']}', but couldn't extract structured data."
            
        # Return to thread/branch selection
        state["current_step"] = "present_exploration_options"
        state["concept_expansion_context"] = {}  # Clear context
        
        return state
        
    except Exception as e:
        # Handle any other errors
        import traceback
        print(traceback.format_exc())
        state["feedback"] = f"Error during concept expansion: {str(e)}"
        state["current_step"] = "present_exploration_options"
        return state
        
def strip_markdown_code_blocks(content: str) -> str:
    """Strip markdown code block formatting from the content."""
    # Remove ```json and ``` markers
    if content.startswith("```") and content.endswith("```"):
        # Find the first newline to skip the language identifier line
        first_newline = content.find('\n')
        if first_newline != -1:
            # Extract content between first newline and last ```
            content = content[first_newline:].strip()
            # Remove the trailing ```
            if content.endswith("```"):
                content = content[:-3].strip()
    
    # If it starts with ```json but doesn't properly end with ```, just remove the start
    elif content.startswith("```json") or content.startswith("```"):
        # Find the first newline to skip the language identifier line
        first_newline = content.find('\n')
        if first_newline != -1:
            content = content[first_newline:].strip()
    
    return content

def format_expansion_results(json_data: dict, branch_id: str, branch_heading: str, expanded_concepts=None) -> str:
    """Format expansion results in a user-friendly way."""
    result = f"## Expanded Concept: {branch_heading} ({branch_id})\n\n"
    
    # Add expanded concepts
    expanded_concepts = json_data.get("expandedConcepts", [])
    if expanded_concepts:
        result += "### Expanded Concepts\n"
        for idx, concept in enumerate(expanded_concepts, 1):
            result += f"{idx}. **{concept.get('heading', '')}**\n"
            result += f"   Explanation: {concept.get('explanation', '')}\n"
            result += f"   Product Direction: {concept.get('productDirection', '')}\n\n"
    
    # Add note about sub-branches
    result += f"\nSub-branches have been created for each expanded concept. You can select them using their branch IDs."
    
    return result

# New function to handle user idea input request
def process_add_idea_request(state: IdeationState, input_text: str) -> IdeationState:
    """Process user's request to add an idea to a specific branch."""
    # Extract branch ID from input (format: "add idea bX" where X is the branch number)
    branch_match = re.search(r'add idea\s+b(\d+)', input_text.lower())
    if not branch_match:
        state["feedback"] = "Invalid format. Please use 'add idea bX' where X is the branch number."
        return state
    
    branch_num = branch_match.group(1)
    branch_id = f"b{branch_num}"
    
    # Check if branch exists
    if branch_id not in state["branches"]:
        state["feedback"] = f"Branch {branch_id} does not exist."
        return state
    
    # Set up for idea input
    state["awaiting_idea_input"] = True
    state["idea_input_context"] = {
        "branch_id": branch_id,
        "parent_branch": state["branches"][branch_id]
    }
    
    # Update input instructions
    state["input_instructions"] = {
        "idea_input": f"What idea would you like to add to branch {branch_id}: {state['branches'][branch_id]['heading']}?"
    }
    
    state["current_step"] = "await_idea_input"
    state["messages"].append(HumanMessage(content=f"I want to add my own idea to branch {branch_id}."))
    
    return state

# New function to process the user's idea content
def process_user_idea(state: IdeationState, user_idea: str) -> IdeationState:
    """Process the user's idea and convert it to the structured format."""
    # Get the context for the idea
    context = state["idea_input_context"]
    branch_id = context["branch_id"]
    parent_branch = context["parent_branch"]
    
    # Add the user idea to messages
    state["messages"].append(HumanMessage(content=f"My idea for {branch_id}: {user_idea}"))
    
    # Process the idea using the LLM to structure it
    try:
        # Prepare the prompt with the user's idea and context
        prompt = USER_IDEA_STRUCTURING_PROMPT.format_messages(
            user_idea=user_idea,
            problem_statement=state["final_problem_statement"],
            parent_heading=parent_branch["heading"],
            parent_content=parent_branch["content"]
        )
        
        # Invoke the LLM
        response = llm.invoke(prompt)
        response_content = response.content.strip()
        
        # Strip markdown code block formatting if present
        response_content = strip_markdown_code_blocks(response_content)
        
        # Parse the JSON
        try:
            json_data = json.loads(response_content)
            
            # Standardize the concept data
            json_data = standardize_concept_branch_data(json_data)
            
            # Create a new branch for the user's idea
            sub_branch_id = f"b{state['branch_counter'] + 1}"
            state['branch_counter'] += 1
            
            # Generate content field for display purposes
            content = f"{json_data['explanation']}"
            if json_data.get('productDirection'):
                content += f" Product Direction: {json_data['productDirection']}"
            
            # Create the sub-branch with standardized fields
            sub_branch = {
                "id": sub_branch_id,
                "thread_id": parent_branch["thread_id"],
                "heading": json_data["heading"],
                "content": content,  # Keep content for backwards compatibility
                "explanation": json_data["explanation"],
                "productDirection": json_data["productDirection"],
                "source": "user_input",
                "parent_branch": branch_id,
                "children": [],
                "expanded": False,
                "expansion_data": None,
                "user_created": True,  # Mark as user-created for reference
                "raw_idea": user_idea,  # Store the original user input
                "category": "concept"  # Explicitly mark as concept category
            }
            
            # Add to global branches registry
            state["branches"][sub_branch_id] = sub_branch
            
            # Add to parent branch's children list
            parent_branch["children"].append(sub_branch_id)
            
            # Add to mindmap
            thread_node = next((node for node in state["mindmap"]["children"] if node["id"] == parent_branch["thread_id"]), None)
            if thread_node:
                branch_node = next((node for node in thread_node["children"] if node["id"] == branch_id), None)
                if branch_node:
                    # Add sub-branch to branch node's children
                    sub_branch_node = {
                        "id": sub_branch_id,
                        "name": json_data["heading"],
                        "content": content,
                        "explanation": json_data["explanation"],
                        "productDirection": json_data["productDirection"],
                        "user_created": True,
                        "children": []
                    }
                    branch_node["children"].append(sub_branch_node)
            
            # Format a success message
            success_message = f"Added your idea as branch {sub_branch_id}: {sub_branch['heading']}\n"
            success_message += f"Explanation: {json_data['explanation']}\n"
            success_message += f"Product Direction: {json_data['productDirection']}"
            
            state["messages"].append(AIMessage(content=success_message))
            state["feedback"] = f"Successfully added your idea as branch {sub_branch_id}."
            
        except Exception as json_error:
            # JSON parsing failed, use a simpler approach
            print(f"Error parsing JSON: {str(json_error)}")
            
            # Create a standardized concept with minimal structure
            concept_data = {
                "heading": "User Idea",
                "explanation": user_idea,
                "productDirection": ""
            }
            
            # Create a new branch with standardized data
            sub_branch_id = f"b{state['branch_counter'] + 1}"
            state['branch_counter'] += 1
            
            # Create the sub-branch with standardized fields
            sub_branch = {
                "id": sub_branch_id,
                "thread_id": parent_branch["thread_id"],
                "heading": concept_data["heading"],
                "content": concept_data["explanation"],  # Keep content for backwards compatibility
                "explanation": concept_data["explanation"],
                "productDirection": concept_data["productDirection"],
                "source": "user_input",
                "parent_branch": branch_id,
                "children": [],
                "expanded": False,
                "expansion_data": None,
                "user_created": True,
                "raw_idea": user_idea,  # Store the original input for reference
                "category": "concept"  # Explicitly mark as concept category
            }
            
            # Add to global branches registry
            state["branches"][sub_branch_id] = sub_branch
            
            # Add to parent branch's children list
            parent_branch["children"].append(sub_branch_id)
            
            # Add to mindmap
            thread_node = next((node for node in state["mindmap"]["children"] if node["id"] == parent_branch["thread_id"]), None)
            if thread_node:
                branch_node = next((node for node in thread_node["children"] if node["id"] == branch_id), None)
                if branch_node:
                    sub_branch_node = {
                        "id": sub_branch_id,
                        "name": concept_data["heading"],
                        "content": concept_data["explanation"],
                        "explanation": concept_data["explanation"],
                        "productDirection": concept_data["productDirection"],
                        "user_created": True,
                        "children": []
                    }
                    branch_node["children"].append(sub_branch_node)
            
            state["messages"].append(AIMessage(content=f"Added your idea as branch {sub_branch_id}."))
            state["feedback"] = f"Added your idea as branch {sub_branch_id}, but couldn't structure it in the standard format."
        
        # Reset the awaiting flag and context
        state["awaiting_idea_input"] = False
        state["idea_input_context"] = {}
        
        # Return to main options
        state["current_step"] = "present_exploration_options"
        
        return state
        
    except Exception as e:
        # Handle any errors
        import traceback
        print(traceback.format_exc())
        state["feedback"] = f"Error processing your idea: {str(e)}"
        state["awaiting_idea_input"] = False
        state["idea_input_context"] = {}
        state["current_step"] = "present_exploration_options"
        return state

def process_delete_request(state: IdeationState, input_text: str) -> IdeationState:
    """Process user's request to delete a branch."""
    # Extract branch ID from input (format: "delete bX" where X is the branch number)
    branch_match = re.search(r'delete\s+b(\d+)', input_text.lower())
    if not branch_match:
        state["feedback"] = "Invalid format. Please use 'delete bX' where X is the branch number."
        return state
    
    branch_num = branch_match.group(1)
    branch_id = f"b{branch_num}"
    
    # Check if branch exists
    if branch_id not in state["branches"]:
        state["feedback"] = f"Branch {branch_id} does not exist."
        return state
    
    # Get branch info for confirmation
    branch = state["branches"][branch_id]
    
    # Count how many children will also be deleted
    children_count = count_branch_children(state, branch_id)
    
    # Set up for confirmation
    state["awaiting_deletion_confirmation"] = True
    state["deletion_context"] = {
        "branch_id": branch_id,
        "branch_heading": branch["heading"],
        "children_count": children_count
    }
    
    # Update input instructions
    confirmation_message = f"Are you sure you want to delete branch {branch_id}: \"{branch['heading']}\"?"
    if children_count > 0:
        confirmation_message += f" This will also delete {children_count} sub-branch{'es' if children_count != 1 else ''}."
    
    state["input_instructions"] = {
        "deletion_confirmation": confirmation_message,
        "options": {
            "yes": "Yes, delete this branch",
            "no": "No, keep this branch"
        }
    }
    
    state["current_step"] = "await_deletion_confirmation"
    state["messages"].append(HumanMessage(content=f"I want to delete branch {branch_id}."))
    
    return state

def count_branch_children(state: IdeationState, branch_id: str) -> int:
    """Recursively count all children of a branch."""
    branch = state["branches"].get(branch_id)
    if not branch:
        return 0
        
    total_children = len(branch["children"])
    
    # Count children of children recursively
    for child_id in branch["children"]:
        total_children += count_branch_children(state, child_id)
    
    return total_children

def process_deletion_confirmation(state: IdeationState, confirmation: str) -> IdeationState:
    """Process user's confirmation for branch deletion."""
    if not state.get("awaiting_deletion_confirmation", False):
        state["feedback"] = "No deletion in progress."
        return state
    
    # Reset awaiting flag
    state["awaiting_deletion_confirmation"] = False
    
    # Normalize confirmation input
    confirmation = confirmation.lower().strip()
    
    if confirmation in ["yes", "y", "confirm", "delete"]:
        # User confirmed deletion
        branch_id = state["deletion_context"]["branch_id"]
        branch_heading = state["deletion_context"]["branch_heading"]
        
        # Perform the deletion
        delete_branch(state, branch_id)
        
        # Add message about deletion
        state["messages"].append(AIMessage(content=f"Deleted branch {branch_id}: \"{branch_heading}\" and all its sub-branches."))
        
        state["feedback"] = f"Successfully deleted branch {branch_id} and all its sub-branches."
    else:
        # User cancelled deletion
        branch_id = state["deletion_context"]["branch_id"]
        state["messages"].append(AIMessage(content=f"Branch deletion cancelled. Branch {branch_id} was kept."))
        
        state["feedback"] = "Branch deletion cancelled."
    
    # Clear deletion context
    state["deletion_context"] = {}
    
    # Return to main options
    state["current_step"] = "present_exploration_options"
    
    return state

def delete_branch(state: IdeationState, branch_id: str) -> None:
    """Delete a branch and all its children recursively."""
    # Get the branch
    branch = state["branches"].get(branch_id)
    if not branch:
        return
    
    # Get the thread_id and parent_branch (if any)
    thread_id = branch.get("thread_id")
    parent_branch_id = branch.get("parent_branch")
    
    # First recursively delete all children
    children_to_delete = branch["children"].copy()  # Make a copy to avoid modifying while iterating
    for child_id in children_to_delete:
        delete_branch(state, child_id)
    
    # Remove from parent's children list if it has a parent
    if parent_branch_id and parent_branch_id in state["branches"]:
        parent_branch = state["branches"][parent_branch_id]
        if branch_id in parent_branch["children"]:
            parent_branch["children"].remove(branch_id)
    
    # Remove from thread's branches
    if thread_id and thread_id in state["threads"]:
        thread = state["threads"][thread_id]
        if branch_id in thread.get("branches", {}):
            del thread["branches"][branch_id]
    
    # Remove from mindmap
    remove_branch_from_mindmap(state, branch_id)
    
    # Remove from global branches registry
    if branch_id in state["branches"]:
        del state["branches"][branch_id]
    
    # If this was the active branch, reset it
    if state["active_branch"] == branch_id:
        state["active_branch"] = None

def remove_branch_from_mindmap(state: IdeationState, branch_id: str) -> None:
    """Remove a branch from the mindmap recursively."""
    # Get the branch
    branch = state["branches"].get(branch_id)
    if not branch:
        return
    
    # Get the thread_id and parent_branch (if any)
    thread_id = branch.get("thread_id")
    parent_branch_id = branch.get("parent_branch")
    
    if thread_id:
        # Find the thread node in the mindmap
        thread_node = next((node for node in state["mindmap"]["children"] if node["id"] == thread_id), None)
        if thread_node:
            if parent_branch_id:
                # This is a sub-branch, find its parent in the mindmap
                parent_node = find_branch_node_in_mindmap(thread_node, parent_branch_id)
                if parent_node and "children" in parent_node:
                    # Remove the branch from its parent's children
                    parent_node["children"] = [child for child in parent_node["children"] if child["id"] != branch_id]
            else:
                # This is a top-level branch directly under the thread
                thread_node["children"] = [child for child in thread_node["children"] if child["id"] != branch_id]

def find_branch_node_in_mindmap(parent_node: dict, branch_id: str) -> dict:
    """Find a branch node in the mindmap by its ID."""
    # Check if this is the node we're looking for
    if parent_node.get("id") == branch_id:
        return parent_node
    
    # Check children recursively
    for child in parent_node.get("children", []):
        result = find_branch_node_in_mindmap(child, branch_id)
        if result:
            return result
    
    return None

def process_combine_request(state: IdeationState, input_text: str) -> IdeationState:
    """Process user's request to combine multiple branches/concepts."""
    # Extract branch IDs from input (format: "combine b1 b2 b3...")
    branch_match = re.search(r'combine\s+((?:b\d+\s*)+)', input_text.lower())
    if not branch_match:
        state["feedback"] = "Invalid format. Please use 'combine' followed by branch IDs (e.g., combine b1 b2 b3)."
        return state
    
    branch_ids_str = branch_match.group(1).strip()
    branch_ids = re.findall(r'b\d+', branch_ids_str)
    
    # Need at least 2 branches to combine
    if len(branch_ids) < 2:
        state["feedback"] = "Please select at least 2 branches to combine."
        return state
    
    # Validate that all branches exist
    invalid_branches = [bid for bid in branch_ids if bid not in state["branches"]]
    if invalid_branches:
        state["feedback"] = f"Branch(es) {', '.join(invalid_branches)} do not exist."
        return state
    
    # Add combine request to messages
    state["messages"].append(HumanMessage(content=f"I want to combine branches {', '.join(branch_ids)}."))
    
    # Set up context for combination and proceed directly
    state["combination_context"] = {
        "branch_ids": branch_ids,
        "branches": {bid: state["branches"][bid] for bid in branch_ids}
    }
    
    state = combine_concepts(state)
    
    return state

def combine_concepts(state: IdeationState) -> IdeationState:
    """Combine selected concepts to generate new product ideas where each idea gets its own thread."""
    # Get the branches to combine
    branch_ids = state["combination_context"]["branch_ids"]
    branches = {bid: state["branches"][bid] for bid in branch_ids}
    
    # Format the branches for the prompt
    concept1 = branches[branch_ids[0]]
    concept2 = branches[branch_ids[1]]
    
    # Format any additional concepts beyond the first two
    additional_concepts = ""
    for i, bid in enumerate(branch_ids[2:], 3):
        branch = branches[bid]
        additional_concepts += f"\nConcept {i}: {branch['heading']}\n{branch['content']}\n"
    
    try:
        # Create a temporary message about the combination request for the main message thread
        combination_message = f"Combining concepts: {', '.join([b['heading'] for b in branches.values()])}"
        state["messages"].append(HumanMessage(content=combination_message))
        
        # Format the prompt with the concepts to combine using the template
        prompt = CONCEPT_COMBINATION_PROMPT.format_messages(
            problem_statement=state["final_problem_statement"],
            concept1_heading=concept1["heading"],
            concept1_content=concept1["content"],
            concept2_heading=concept2["heading"],
            concept2_content=concept2["content"],
            additional_concepts=additional_concepts
        )
        
        # Invoke the LLM
        response = llm.invoke(prompt)
        response_content = response.content.strip()
        
        # Add notification to main message history
        notification = f"Created new ideas by combining concepts: {', '.join([b['heading'] for b in branches.values()])}"
        state["messages"].append(AIMessage(content=notification))
        
        # Try to parse JSON from the response
        try:
            # Strip markdown code block formatting if present
            response_content = strip_markdown_code_blocks(response_content)
            
            # Debug log
            print("Attempting to parse JSON response:")
            print(response_content[:200] + "..." if len(response_content) > 200 else response_content)
            
            # Wrap in extra error handling to provide better feedback
            try:
                # Parse JSON
                json_data = json.loads(response_content)
                
                # Validate the structure is what we expect
                if not isinstance(json_data, list):
                    print(f"Warning: Expected a list but got {type(json_data)}, converting")
                    if isinstance(json_data, dict):
                        json_data = [json_data]  # Convert single dict to list
                    else:
                        json_data = [{"heading": "Combined Concept", 
                                     "explanation": str(json_data),
                                     "featureLists": []}]
                
                # Create thread and branch for EACH combined concept
                combined_thread_ids = create_individual_combined_threads(state, json_data, branch_ids)
                
                num_ideas = len(json_data) if isinstance(json_data, list) else 1
                state["feedback"] = f"Successfully combined concepts and created {num_ideas} new product idea(s), each with its own thread."
                
                # Set the first combined thread as active if any were created
                if combined_thread_ids:
                    state["active_thread"] = combined_thread_ids[0]
                    state["active_branch"] = None  # Reset active branch
                
            except Exception as inner_error:
                print(f"Inner JSON parsing error: {str(inner_error)}")
                raise  # Re-raise to be caught by outer handler
            
        except Exception as json_error:
            # JSON parsing failed - create a single combined concept with the raw text
            print(f"Error parsing JSON in combination response: {str(json_error)}")
            
            # Create a simple structured product from the text response
            fallback_concept = [{
                "heading": "Combined Product Idea",
                "description": "This combines elements from the selected concepts.",
                "features": ["Generated product idea based on combined concepts"],
                "sourceConcepts": branch_ids
            }]
            
            # Create a thread for this concept anyway
            combined_thread_ids = create_individual_combined_threads(state, fallback_concept, branch_ids)
            
            if combined_thread_ids:
                state["active_thread"] = combined_thread_ids[0]
                state["active_branch"] = None
                
            state["feedback"] = "Created a combined concept with the generated content."
        
        return state
        
    except Exception as e:
        # Handle any other errors
        import traceback
        print(traceback.format_exc())
        state["feedback"] = f"Error during concept combination: {str(e)}"
        state["combination_context"] = {}
        return state

def create_individual_combined_threads(state: IdeationState, json_data: list, source_branch_ids: list) -> list:
    """Create individual threads and branches for each combined concept."""
    thread_ids = []
    
    # Get the source branches
    source_branches = {bid: state["branches"][bid] for bid in source_branch_ids if bid in state["branches"]}
    
    # Process each combined concept and create a separate thread for each
    for idx, concept in enumerate(json_data):
        # Make sure concept is a dictionary
        if isinstance(concept, str):
            # If concept is a string, create a basic product concept dictionary
            concept = {
                "heading": f"Combined Concept {idx+1}",
                "description": concept,
                "features": ["No specific features provided"],
                "category": "product"
            }
        
        # Ensure concept is properly standardized as product category
        concept = standardize_product_branch_data(concept)
            
        # Generate a unique branch ID first for this combined concept
        branch_id = f"b{state['branch_counter'] + 1}"
        state['branch_counter'] += 1
        
        # Generate a unique thread ID for this combined concept
        thread_id = f"thread_combined_{state['branch_counter']}"
        thread_ids.append(thread_id)
        
        # Safely get sourceConcepts if it exists, otherwise use source_branch_ids
        source_concepts = source_branch_ids
        if "sourceConcepts" in concept:
            source_concepts = concept["sourceConcepts"]
        
        # Get branch headings for display, with fallbacks for non-existent branches
        source_names = []
        for sc in source_concepts:
            if sc in state["branches"]:
                source_names.append(state["branches"][sc]["heading"])
            else:
                source_names.append(sc)
        
        # Get concept heading with fallback
        concept_heading = concept.get("heading", f"Combined Concept {idx+1}")
        
        # Get description and features from standardized product format
        description = concept.get("description", "")
        features = concept.get("features", [])
        
        # Remove any tags that might have been generated
        description = re.sub(r'<[^>]*>', '', description)
        
        # Create formatted content for display
        features_text = ""
        if features:
            features_text = "\n\nFeatures:\n" + "\n".join([f"- {feature}" for feature in features])
        
        content = description + features_text
        
        # Create the branch for this combined concept with explicit product category
        new_branch = {
            "id": branch_id,
            "thread_id": thread_id,
            "heading": concept_heading,
            "content": content,  # Keep for display purposes
            "description": description,
            "features": features,
            "source": "concept_combination",
            "parent_branch": None,  # Top-level combined concepts have no parent
            "children": [],  # Initialize empty children list
            "expanded": False,  # Track if this branch has been expanded
            "expansion_data": None,  # Will store expansion data when expanded
            "source_concepts": source_concepts,  # Track which concepts were combined
            "category": "product"  # Explicitly mark as product category
        }
        
        # Add to global branches registry
        state["branches"][branch_id] = new_branch
        
        # Format the message content without any tags
        features_msg = ""
        if features:
            features_msg = "\n\nFeatures:\n" + "\n".join([f"- {feature}" for feature in features])
            
        message_content = f"This product idea ({branch_id}) combines elements from multiple concepts:\n\n{description}{features_msg}"
            
        # Create a new thread for this specific combined concept
        state["threads"][thread_id] = {
            "id": thread_id,
            "name": concept_heading,
            "description": f"Product idea combining concepts: {', '.join(source_names)}",
            "messages": [
                SystemMessage(content=SYSTEM_TEMPLATE),
                HumanMessage(content=f"Let's explore this combined product idea: {concept_heading}"),
                AIMessage(content=message_content)
            ],
            "branches": {
                branch_id: new_branch  # Initialize with the main branch for this combined concept
            },
            "source_concepts": source_concepts,
            "combined_concept": True  # Flag to identify combined concept threads
        }
        
        # Add to mindmap as a top-level node (at the same level as the methodology threads)
        state["mindmap"]["children"].append({
            "id": thread_id,
            "name": concept_heading,
            "description": f"Combined from: {', '.join(source_names)}",
            "combined": True,  # Flag to identify combined concept nodes
            "children": [
                {
                    "id": branch_id,
                    "name": concept_heading,
                    "content": content,
                    "description": description,
                    "features": features,
                    "children": [],
                    "source_concepts": source_concepts,
                    "category": "product"  # Explicitly mark as product category
                }
            ]
        })
    
    return thread_ids

def ensure_categories_in_branches(state: IdeationState) -> IdeationState:
    """Ensure all branches in the state have a category field and correct format."""
    # Update all branches to have a proper category and format
    for branch_id, branch in state["branches"].items():
        # Determine the proper category for this branch
        proper_category = determine_branch_category(branch, state)
        
        # Set or update the category
        branch["category"] = proper_category
        
        # Apply the appropriate standardization based on category
        if proper_category == "product":
            # Standardize product branch
            standardized = standardize_product_branch_data(branch)
            # Update the branch with standardized values
            for key, value in standardized.items():
                branch[key] = value
        else:
            # Standardize concept branch
            standardized = standardize_concept_branch_data(branch)
            # Update the branch with standardized values
            for key, value in standardized.items():
                branch[key] = value
    
    # Update all mindmap nodes to have proper category
    update_mindmap_categories(state["mindmap"], state["branches"])
    
    return state

def determine_branch_category(branch: dict, state: IdeationState) -> str:
    """Determine the proper category for a branch."""
    # Check if the branch is in a combined thread
    if branch.get("thread_id", "").startswith("thread_combined_"):
        return "product"
    
    # Check if the branch was explicitly created as a product
    if branch.get("source") == "concept_combination":
        return "product"
    
    # Check if this branch has source_concepts (indicating it was created by combining)
    if "source_concepts" in branch and len(branch.get("source_concepts", [])) > 1:
        return "product"
    
    # Check if the branch already has a valid category set
    if branch.get("category") in ["concept", "product"]:
        # If it's already categorized as product, keep it that way
        # (don't downgrade products to concepts)
        return branch["category"]
    
    # Default to concept category for all other branches
    return "concept"

def update_mindmap_categories(mindmap_node: dict, branches: dict):
    """Recursively update all nodes in the mindmap to have proper category field."""
    # Skip non-dict nodes
    if not isinstance(mindmap_node, dict):
        return
        
    # Skip nodes without children
    if "children" not in mindmap_node:
        return
        
    # Update each child
    for child in mindmap_node.get("children", []):
        # If child has an ID that matches a branch, copy category and format
        if "id" in child and child["id"] in branches:
            branch = branches[child["id"]]
            
            # Get category from branch
            category = branch.get("category", "concept")  # Default to concept
            child["category"] = category
            
            # Ensure appropriate fields exist based on category
            if category == "product":
                # Copy or set required product fields
                child["description"] = branch.get("description", "")
                child["features"] = branch.get("features", [])
                
                # Remove concept-specific fields if they exist
                if "explanation" in child:
                    del child["explanation"]
                if "productDirection" in child:
                    del child["productDirection"]
                
                # Generate content field for display
                features_text = ""
                if child["features"]:
                    features_text = "\n\nFeatures:\n" + "\n".join([f"- {feature}" for feature in child["features"]])
                
                child["content"] = child["description"] + features_text
            else:
                # Copy or set required concept fields
                child["explanation"] = branch.get("explanation", "")
                child["productDirection"] = branch.get("productDirection", "")
                
                # Remove product-specific fields if they exist
                if "description" in child:
                    del child["description"]
                if "features" in child:
                    del child["features"]
                
                # Copy userProfile if it exists
                if "userProfile" in branch:
                    child["userProfile"] = branch["userProfile"]
                
                # Generate content field for display
                content = child["explanation"]
                if child["productDirection"]:
                    content += f" Product Direction: {child['productDirection']}"
                if "userProfile" in child and child["userProfile"]:
                    content = f"User: {child['userProfile']}\nFeedback: {content}"
                
                child["content"] = content
        
        # Recursively update this child's children
        update_mindmap_categories(child, branches)

def standardize_concept_branch_data(branch_data: dict) -> dict:
    """Standardize concept branch data to ensure consistent format."""
    # Create a new dictionary to avoid modifying the original input
    standardized = {}
    
    # Ensure required fields exist
    standardized["heading"] = branch_data.get("heading", "Untitled Concept")
    
    # Extract explanation from content or existing explanation field
    if "explanation" in branch_data:
        standardized["explanation"] = branch_data["explanation"]
    elif "content" in branch_data and isinstance(branch_data["content"], str):
        content = branch_data["content"]
        
        # Try to extract explanation and productDirection if they're combined in content
        product_dir_patterns = ["Product direction:", "Product Direction:", "Product direction", "Product Direction"]
        
        for pattern in product_dir_patterns:
            if pattern in content:
                parts = content.split(pattern, 1)
                standardized["explanation"] = parts[0].strip()
                standardized["productDirection"] = parts[1].strip()
                break
        else:
            # If no pattern found, use entire content as explanation
            standardized["explanation"] = content
            standardized["productDirection"] = ""
    else:
        # Fallback to empty explanation
        standardized["explanation"] = ""
    
    # Ensure productDirection exists
    if "productDirection" in branch_data:
        standardized["productDirection"] = branch_data["productDirection"]
    elif "productDirection" not in standardized:
        standardized["productDirection"] = ""
    
    # For imaginary customer feedback, ensure userProfile exists if needed
    if branch_data.get("source") == "imaginaryFeedback" or "userProfile" in branch_data:
        if "userProfile" in branch_data:
            standardized["userProfile"] = branch_data["userProfile"]
        elif "content" in branch_data and "User:" in branch_data["content"]:
            # Extract userProfile from content if it contains "User:" pattern
            user_part = branch_data["content"].split("User:", 1)[1].split("\n", 1)[0].strip()
            standardized["userProfile"] = user_part
        else:
            standardized["userProfile"] = ""
    
    # Copy any source information
    if "source" in branch_data:
        standardized["source"] = branch_data["source"]
    
    if "source_idx" in branch_data:
        standardized["source_idx"] = branch_data["source_idx"]
        
    # Preserve any other special fields that might be needed
    for field in ["id", "thread_id", "parent_branch", "children", "expanded", "expansion_data"]:
        if field in branch_data:
            standardized[field] = branch_data[field]
    
    # Always explicitly set category as concept
    standardized["category"] = "concept"
    
    # For backwards compatibility - create content field that combines explanation and productDirection
    content = standardized["explanation"]
    if standardized["productDirection"]:
        content += f" Product Direction: {standardized['productDirection']}"
    if "userProfile" in standardized and standardized["userProfile"]:
        content = f"User: {standardized['userProfile']}\nFeedback: {content}"
    
    standardized["content"] = content
    
    return standardized

def standardize_product_branch_data(branch_data: dict) -> dict:
    """Standardize product branch data to ensure consistent format."""
    # Create a new dictionary to avoid modifying the original
    standardized = {}
    
    # Ensure required fields exist
    standardized["heading"] = branch_data.get("heading", "Untitled Product")
    
    # Process description field
    if "description" in branch_data:
        standardized["description"] = branch_data["description"]
    elif "explanation" in branch_data:
        standardized["description"] = branch_data["explanation"]
    else:
        standardized["description"] = branch_data.get("content", "No description available.")
    
    # Process features list
    features = []
    # Try to extract from featureLists if it exists
    if "featureLists" in branch_data and isinstance(branch_data["featureLists"], list):
        features = branch_data["featureLists"]
    elif "features" in branch_data and isinstance(branch_data["features"], list):
        features = branch_data["features"]
    
    # If no features found, create a default placeholder
    if not features:
        features = ["No specific features provided"]
    
    standardized["features"] = features
    
    # Ensure sourceConcepts exists if applicable
    if "sourceConcepts" in branch_data:
        standardized["sourceConcepts"] = branch_data["sourceConcepts"]
    elif "source_concepts" in branch_data:
        standardized["sourceConcepts"] = branch_data["source_concepts"]
    else:
        standardized["sourceConcepts"] = []
    
    # Set product category
    standardized["category"] = "product"
    
    return standardized



def end_session(state: IdeationState) -> IdeationState:
    """End the ideation session."""
    # Simply set the current step to indicate the session has ended
    state["current_step"] = "session_ended"
    state["feedback"] = "Ideation session ended."
    
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
        "regenerate_problem_statement_1": False,
        "regenerate_problem_statement_2": False,
        # New fields for exploration options
        "threads": {},
        "active_thread": None,
        "awaiting_thread_choice": False,
        "switch_thread": False,  # Flag for switching between threads
        "mindmap": {},
        "current_step": "initial_input",
        # New fields for branch management
        "branches": {},
        "branch_counter": 0,
        "active_branch": None,
        "awaiting_branch_choice": False,
        "awaiting_concept_input": False,
        "concept_expansion_context": {},
        # User idea fields
        "awaiting_idea_input": False,
        "idea_input_context": {},
        # New fields for branch deletion
        "awaiting_deletion_confirmation": False,
        "deletion_context": {},
        # Fields for concept combination
        "combination_context": {}
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
        display_problem_statement_choices(state)
        
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

    # Display the thread options using the helper function
    print("\nExploration approaches:")
    thread_options = get_thread_options_display(state)
    for option in thread_options:
        print(option["display"])
    
    # Start multi-thread exploration using state graph workflow
    exploring = True
    
    while exploring:
        # Display available branches
        display_available_branches(state)
        
        # Show the exploration options
        print("\nChoose next action:")
        print("1-3: Select a thread (exploration approach)")
        print("b#: Select a branch (e.g., b1, b2, b3)")
        print("add idea b#: Add your own idea to a branch (e.g., add idea b1)")
        print("delete b#: Delete a branch and all its sub-branches (e.g., delete b1)")
        print("combine b# b# [b#...]: Combine multiple concepts (e.g., combine b1 b2)")
        print("stop: End the ideation session")
        
        # Get user choice
        user_choice = input("\nEnter your choice: ").lower()
        
        # Check for stop command
        if user_choice.strip() == "stop":
            exploring = False
            state = end_session(state)
            continue
        
        # Set up context for processing
        state["context"]["thread_choice"] = user_choice

        # Process combine request
        if "combine" in user_choice.lower():
            # Process combine request directly (no confirmation step)
            state = process_combine_request(state, user_choice)
            
            # Display feedback
            if state["feedback"]:
                print(f"\n{state['feedback']}")
                state["feedback"] = ""
                
            continue
            
        # Process deletion request
        if "delete" in user_choice.lower():
            # Process deletion request
            state = process_delete_request(state, user_choice)
            
            # If awaiting confirmation
            if state.get("awaiting_deletion_confirmation", False):
                # Show confirmation prompt using input instructions
                confirmation_message = state["input_instructions"]["deletion_confirmation"]
                options = state["input_instructions"]["options"]
                
                print(f"\n{confirmation_message}")
                for key, value in options.items():
                    print(f"{key}: {value}")
                    
                confirmation = input("\nConfirm (yes/no): ")
                
                # Process confirmation
                state = process_deletion_confirmation(state, confirmation)
                
                # Display feedback
                if state["feedback"]:
                    print(f"\n{state['feedback']}")
                    state["feedback"] = ""
                    
            continue
        
        # Process add idea request
        if "add idea" in user_choice.lower():
            # Process add idea request
            state = process_add_idea_request(state, user_choice)
            
            # If awaiting idea input
            if state.get("awaiting_idea_input", False):
                # Get user's idea
                print(f"\n{state['input_instructions']['idea_input']}")
                idea_input = input("\nYour idea: ")
                
                # Process user's idea
                state = process_user_idea(state, idea_input)
                
                # Display feedback
                if state["feedback"]:
                    print(f"\n{state['feedback']}")
                    state["feedback"] = ""
                    
            continue
            
        # Process branch selection
        elif user_choice.startswith('b'):
            # Branch selection
            state = process_branch_selection(state, user_choice)
            
            # If awaiting concept input
            if state["awaiting_concept_input"]:
                # Get the suggested guidance from the context
                suggested_guidance = state["concept_expansion_context"]["suggested_guidance"]
                
                # Display the prompt with suggested guidance
                print(f"\nPlease provide guidance for expanding branch {state['concept_expansion_context']['branch_id']}: {state['concept_expansion_context']['heading']}")
                print(f"(Enter your guidance or press Enter to use this suggestion)")
                print(f"\nSuggested guidance: {suggested_guidance}")
                
                concept_input = input("\nYour guidance: ")
                
                # Process concept input
                state = process_concept_input(state, concept_input)
                
                # Expand the concept
                print(f"\nExpanding concept {state['concept_expansion_context']['branch_id']}...")
                state = expand_concept(state)
                
                # Display feedback
                if state["feedback"]:
                    print(f"\n{state['feedback']}")
                    state["feedback"] = ""
        else:
            # Thread selection or other action
            old_thread = state["active_thread"]
            old_step = state["current_step"]
            
            # Process thread choice
            state = process_thread_choice_multi(state, user_choice)
            
            # If stopping, break the loop
            if state["current_step"] == "end_session":
                exploring = False
                continue
                
            # If switching threads, continue the loop to show options again
            if state.get("switch_thread", False):
                if state["feedback"]:
                    print(f"\n{state['feedback']}")
                    state["feedback"] = ""
                continue
                
            # If we selected a thread to explore, simulate the thread exploration
            if state["current_step"] == "thread_exploration":
                thread_id = state["active_thread"]
                thread_name = state["threads"][thread_id]["name"]
                
                print(f"\nNow exploring: {thread_name}")
                print(f"This thread has its own separate conversation history.")
                
                # Simulate thread exploration
                state = thread_exploration(state)
                
                # Display feedback
                if state["feedback"]:
                    print(f"\n{state['feedback']}")
                    state["feedback"] = ""
    
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
workflow.add_node("process_branch_selection", lambda state: process_branch_selection(state, state["context"].get("branch_choice", "")))
workflow.add_node("process_concept_input", lambda state: process_concept_input(state, state["context"].get("concept_input", "")))
workflow.add_node("expand_concept", expand_concept)
workflow.add_node("end_session", end_session)
workflow.add_node("process_add_idea_request", lambda state: process_add_idea_request(state, state["context"].get("thread_choice", "")))
workflow.add_node("process_user_idea", lambda state: process_user_idea(state, state["context"].get("idea_input", "")))
workflow.add_node("process_delete_request", lambda state: process_delete_request(state, state["context"].get("thread_choice", "")))
workflow.add_node("process_deletion_confirmation", lambda state: process_deletion_confirmation(state, state["context"].get("deletion_confirmation", "")))
workflow.add_node("process_combine_request", lambda state: process_combine_request(state, state["context"].get("thread_choice", "")))

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
        "thread_exploration": not state.get("switch_thread", False) and state["current_step"] == "thread_exploration",  # Explore the selected thread
        "process_branch_selection": not state.get("switch_thread", False) and state["current_step"] == "process_branch_selection",  # Process branch selection
        "process_combine_request": not state.get("switch_thread", False) and "combine" in state["context"].get("thread_choice", "").lower(),  # Process combine request
        "end_session": state["current_step"] == "end_session"  # End the session
    }
)

# Add edge from thread exploration back to thread selection
workflow.add_edge("thread_exploration", "present_exploration_options")

# Add conditional edges for branch selection and concept expansion
workflow.add_conditional_edges(
    "process_branch_selection",
    lambda state: {
        "process_concept_input": state["awaiting_concept_input"],
        "present_exploration_options": not state["awaiting_concept_input"]
    }
)

# Add conditional edges for add idea request
workflow.add_conditional_edges(
    "process_add_idea_request",
    lambda state: {
        "process_user_idea": state.get("awaiting_idea_input", False),
        "present_exploration_options": not state.get("awaiting_idea_input", False)
    }
)

# Add edges for concept expansion
workflow.add_edge("process_concept_input", "expand_concept")
workflow.add_edge("expand_concept", "present_exploration_options")

# Add edge from process_user_idea back to present_exploration_options
workflow.add_edge("process_user_idea", "present_exploration_options")

# Add conditional edges for delete request
workflow.add_conditional_edges(
    "process_delete_request",
    lambda state: {
        "process_deletion_confirmation": state.get("awaiting_deletion_confirmation", False),
        "present_exploration_options": not state.get("awaiting_deletion_confirmation", False)
    }
)

# Add edge for deletion confirmation
workflow.add_edge("process_deletion_confirmation", "present_exploration_options")

# Add direct edge for combine request (no confirmation step)
workflow.add_edge("process_combine_request", "present_exploration_options")

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
        "explanation": "",  # Initialize the new field
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
        "current_step": "initial_input",
        # New fields for branch management
        "branches": {},
        "branch_counter": 0,
        "active_branch": None,
        "awaiting_branch_choice": False,
        "awaiting_concept_input": False,
        "concept_expansion_context": {},
        "switch_thread": False,  # Flag for switching between threads
        # New fields for user idea input
        "awaiting_idea_input": False,
        "idea_input_context": {},
        # New fields for branch deletion
        "awaiting_deletion_confirmation": False,
        "deletion_context": {},
        # Fields for concept combination
        "combination_context": {}
    }
    
    # Add the system message to start fresh
    initial_state["messages"].append(SystemMessage(content=SYSTEM_TEMPLATE))
    
    return app.invoke(initial_state)

# If this file is run directly, execute the CLI workflow
if __name__ == "__main__":
    run_cli_workflow()


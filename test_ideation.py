from src.graphs.ideation_graph import start_ideation_session, process_human_input

def test_problem_statement():
    # Start a new ideation session
    state = start_ideation_session()
    
    # New example input
    target_audience = "elderly people"
    problem = "couldn't find a way to get groceries delivered to their home"
    print(f"\nInput values:")
    print(f"Target audience: {target_audience}")
    print(f"Problem: {problem}")
    
    # Process the input and generate problem statement
    state = process_human_input(state, target_audience, problem)
    print("\nOriginal problem statement:")
    print(f"{state.get('original_problem_statement', 'No problem statement generated')}")
    print("\nRefined problem statement:")
    print(f"{state.get('refined_problem_statement', 'No refined problem statement generated')}")

if __name__ == "__main__":
    test_problem_statement() 
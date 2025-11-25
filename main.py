from kb_parser import load_kb, parse_literal
from inference_engine import ask

# Function that receives text entered by the user (eg "NeedsCooling(X)?")
# and converts it into a structure that the logic engine can process.
def make_query_from_str(qs: str):
    """Convert user input into a literal (predicate with arguments)."""
    s = qs.strip().rstrip('?').strip()    # clean the '?' sign and unnecessary spaces
    if not s:
        return None
    try:
        return parse_literal(s)           # try to interpret the text as a FOL literal
    except Exception as e:
        print(f"Error parsing query: {e}")  # if an error occurs, display it
        return None


# Function for pretty-printing the results returned by the logic engine.
def display_solutions(literal, sols):
    """Pretty-print query results for the user."""
    if not sols:
        print("  No solutions.")   # case where there is no answer
        return

    # Variables in the query (e.g., X, Room, etc.)
    vars_in_query = [
        a for a in literal["args"]
        if isinstance(a, str) and a and a[0].isupper()
    ]

    print(f"  Solutions found: {len(sols)}")

    # Iterate through each found solution
    for s in sols:
        if vars_in_query:
            # For each variable, display the value it was instantiated with
            pairs = [f"{v} = {s.get(v, v)}" for v in vars_in_query]
            print("   - " + ", ".join(pairs))
        else:
            # If there are no variables, the answer is simply "Yes"
            print("   - Yes.")


# Entry point of the program
if __name__ == "__main__":

    print("=== SmartHome FOL Reasoner ===")
    print("Loading knowledge base...")

    # Load the knowledge base from the kb.fol file
    facts, rules = load_kb("kb.fol")
    print(f"KB loaded: {len(facts)} facts, {len(rules)} rules.\n")

    # Run a few example queries automatically, as a demo
    print("Running demo queries...")
    demo_queries = [
        "NeedsCooling(X)?",
        "TurnOnAC(X)?",
        "ShouldTurnOffLight(X)?",
        "NeedsHeating(X)?",
        "GreaterThan(29, 25)?"
    ]

    # Process each query from the demo list
    for q in demo_queries:
        print(f"\nQuery: {q}")
        lit = make_query_from_str(q)
        if lit:
            sols = ask(lit, facts, rules)   # call the logic engine
            display_solutions(lit, sols)    # show results

    # Activate interactive mode for the user
    print("\n=== Interactive Mode ===")
    print("Type a query like:   NeedsCooling(X)?")
    print("Commands: 'exit', 'quit', 'help'\n")

    while True:
        qs = input("Query > ").strip()   # read user input
        # Special commands
        if qs.lower() in ["exit", "quit"]:
            print("Exiting SmartHome Reasoner. Goodbye!")
            break

        if qs.lower() == "help":
            print("""
Enter queries in FOL form, for example:
   NeedsCooling(X)?
   TurnOnAC(Room)?
   Occupied(living_room)?
   GreaterThan(Temperature, 25)?

Commands:
   exit  - leave the program
   help  - show this help message
""")
            continue

        # Convert the text into a FOL query
        lit = make_query_from_str(qs)
        if lit is None:
            continue

        # Ask the logic engine to find solutions
        sols = ask(lit, facts, rules)

        # Display what the engine found
        display_solutions(lit, sols)

from kb_parser import load_kb, parse_literal
from inference_engine import ask

def make_query_from_str(qs: str):
    s = qs.strip().rstrip('?').strip()
    lit = parse_literal(s)
    return lit

if __name__ == "__main__":
    facts, rules = load_kb("kb.fol")
    print("KB loaded.")
    examples = [
        "NeedsCooling(X)?",
        "TurnOnAC(X)?",
        "ShouldTurnOffLight(X)?",
        "NeedsHeating(X)?",
        "GreaterThan(29, 25)?"
    ]
    for q in examples:
        lit = make_query_from_str(q)
        sols = ask(lit, facts, rules)
        print(f"\nQuery: {q}")
        if not sols:
            print("  No.")
        else:
            for s in sols:
                qs_vars = [a for a in lit["args"] if isinstance(a, str) and a and a[0].isupper()]
                if qs_vars:
                    display = ', '.join([f"{v} = {s.get(v, v)}" for v in qs_vars])
                else:
                    display = "Yes."
                print(f"  {display}")

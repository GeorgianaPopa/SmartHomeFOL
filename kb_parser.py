import re
from typing import List, Tuple, Dict, Any

# An "Predicate" is represented as: ("PredicateName", [list_of_arguments])
Predicate = Tuple[str, List[Any]]
Fact = Predicate   # a fact is just a simple predicate
Rule = Dict[str, Any]  # a rule contains a head and a body

# Regular expression to recognize something like: Predicate(arg1, arg2)
LIT_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$')

# Regular expression for negated literals like: not(Predicate(...))
NOT_WRAP_RE = re.compile(r'^\s*not\s*\(\s*(.+)\s*\)\s*$', re.IGNORECASE)

def split_top_level(s: str, sep: str = ',') -> List[str]:
    """Split a string by a separator, but only where we are not inside parentheses.
       This correctly separates arguments even if they have complex forms.
    """
    parts: List[str] = []
    buf = []
    depth = 0
    for ch in s:
        if ch == '(':
            depth += 1
            buf.append(ch)
        elif ch == ')':
            depth -= 1
            buf.append(ch)
        elif ch == sep and depth == 0:
            # if the separator appears at level 0 (we are not inside parentheses), split the argument
            part = ''.join(buf).strip()
            if part != '':
                parts.append(part)
            buf = []
        else:
            buf.append(ch)
    last = ''.join(buf).strip()
    if last != '':
        parts.append(last)
    return parts


def tokenize_args(argstr: str) -> List[str]:
    """Receives the content inside parentheses and splits it into individual arguments."""
    if argstr.strip() == '':
        return []
    return [a.strip() for a in split_top_level(argstr, sep=',') if a.strip() != '']


def parse_atom(atom_str: str) -> Tuple[str, List[Any]]:
    """
    Parses something like Predicate(a, X, 27)
    Returns: (predicate_name, list_of_arguments)
    Numbers are automatically converted to int.
    """
    m = LIT_RE.match(atom_str.strip())
    if not m:
        raise ValueError(f"Invalid atom syntax: '{atom_str}'")

    pred = m.group(1)
    argstr = m.group(2).strip()

    args = []
    if argstr != '':
        for tok in tokenize_args(argstr):
            # transformăm automat numerele în int
            if re.fullmatch(r'-?\d+', tok):
                args.append(int(tok))
            else:
                args.append(tok)
    return pred, args


def parse_literal(lit_str: str) -> Dict[str, Any]:
    """
    Parses a literal which can be negated or positive.
    Examples accepted:
       Predicate(a, b)
       not(Predicate(a, b))
       not Predicate(a, b)

    Returns a dictionary:
       { "pred": name, "args": [...], "negated": True/False }
    """
    s = lit_str.strip()

    neg = False
    inner = s

    # Detect the "not ..." form
    if s.lower().startswith('not'):
        rest = s[3:].strip()
        if rest.startswith('(') and rest.endswith(')'):
            inner = rest[1:-1].strip()
        else:
            inner = rest
        neg = True

    pred, args = parse_atom(inner)
    return {"pred": pred, "args": args, "negated": neg}


def parse_fact(line: str) -> Fact:
    """Parses a fact, which is a predicate ending with a period."""
    line = line.strip().rstrip('.').strip()
    pred, args = parse_atom(line)
    return (pred, args)


def parse_rule(line: str) -> Rule:
    """
    Parses a rule of the form:
        Head(X) :- Body1(X), Body2(X).
    Returns a dictionary with:
        {
            "head": (predicate, [args]),
            "body": [ list_of_literals ]
        }
    """
    line = line.strip().rstrip('.').strip()

    if ':-' not in line:
        raise ValueError(f"Invalid rule (missing ':-'): {line}")

    head_str, body_str = line.split(':-', 1)
    head_pred, head_args = parse_atom(head_str.strip())

    # correctly split all conditions in the body
    body_parts = [p.strip() for p in split_top_level(body_str) if p.strip() != '']
    body = [parse_literal(part) for part in body_parts]

    return {"head": (head_pred, head_args), "body": body}

def load_kb(path: str) -> Tuple[List[Fact], List[Rule]]:
    """
    Loads the kb.fol file and returns lists of:
        - facts
        - rules

    What it does:
        ✓ removes comments (everything after '%')
        ✓ removes empty lines
        ✓ reconstructs statements that span multiple lines
    """
    facts: List[Fact] = []
    rules: List[Rule] = []

    # Read the entire file
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned = []
    for raw in lines:
        # remove comments and empty lines
        line = raw.split('%', 1)[0].strip()
        if line == '':
            continue
        cleaned.append(line)

    statements = []
    buffer = ""

    # Build complete statements (only end with ".")
    for line in cleaned:
        buffer += " " + line
        if line.endswith('.'):
            statements.append(buffer.strip())
            buffer = ""

    # if something remains unclosed, we have a syntax error in the file
    if buffer.strip() != "":
        raise ValueError(f"Unterminated statement in KB: '{buffer.strip()}'")

    # Identify whether each statement is a fact or a rule
    for stmt in statements:
        if ':-' in stmt:
            try:
                rule = parse_rule(stmt)
                rules.append(rule)
            except Exception as e:
                raise ValueError(f"Error parsing rule '{stmt}': {e}")
        else:
            try:
                fact = parse_fact(stmt)
                facts.append(fact)
            except Exception as e:
                raise ValueError(f"Error parsing fact '{stmt}': {e}")

    return facts, rules

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Simple FOL KB parser (SmartHome project)")
    parser.add_argument("--kb", type=str, default="kb.fol", help="Path to kb.fol")
    args = parser.parse_args()

    facts, rules = load_kb(args.kb)

    print("==== Facts ====")
    for p, a in facts:
        print(f"- {p}({', '.join(map(str, a))})")

    print("\n==== Rules ====")
    for r in rules:
        head_pred, head_args = r["head"]
        head_str = f"{head_pred}({', '.join(map(str, head_args))})"

        body_parts = []
        for lit in r["body"]:
            body_str = f"{lit['pred']}({', '.join(map(str, lit['args']))})"
            if lit["negated"]:
                body_str = "not " + body_str
            body_parts.append(body_str)

        print(f"- {head_str} :- {', '.join(body_parts)}")

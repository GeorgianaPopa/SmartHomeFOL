import re
from typing import List, Tuple, Dict, Any

Predicate = Tuple[str, List[Any]]
Fact = Predicate
Rule = Dict[str, Any]

LIT_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)\s*$')

NOT_WRAP_RE = re.compile(r'^\s*not\s*\(\s*(.+)\s*\)\s*$', re.IGNORECASE)


def split_top_level(s: str, sep: str = ',') -> List[str]:
    """Split string by sep but only at top-level (paren depth == 0)."""
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
    """Split argument list by commas at top level (handles nested parentheses)."""
    if argstr.strip() == '':
        return []
    return [a.strip() for a in split_top_level(argstr, sep=',') if a.strip() != '']


def parse_atom(atom_str: str) -> Tuple[str, List[Any]]:
    """
    Parse an atom like: Predicate(a, X, 27)
    Returns (predicate_name, [args]).
    Numeric arguments automatically converted to int.
    """
    m = LIT_RE.match(atom_str.strip())
    if not m:
        raise ValueError(f"Invalid atom syntax: '{atom_str}'")

    pred = m.group(1)
    argstr = m.group(2).strip()

    args = []
    if argstr != '':
        for tok in tokenize_args(argstr):
            if re.fullmatch(r'-?\d+', tok):
                args.append(int(tok))
            else:
                args.append(tok)
    return pred, args


def parse_literal(lit_str: str) -> Dict[str, Any]:
    """
    Parse a literal that may be negated.
    Accepts:
        - Predicate(a, b)
        - not(Predicate(a, b))
        - not Predicate(a, b)
    Returns dict: { "pred": name, "args": [...], "negated": bool }
    """
    s = lit_str.strip()

    neg = False
    inner = s

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
    """Parse a fact: a predicate ending with a period."""
    line = line.strip().rstrip('.').strip()
    pred, args = parse_atom(line)
    return (pred, args)


def parse_rule(line: str) -> Rule:
    """
    Parse a rule of the form:
        Head(X) :- Body1(X), Body2(X).
    Returns:
        {
            "head": (pred, args),
            "body": [ literal_dict, literal_dict, ... ]
        }
    """
    line = line.strip().rstrip('.').strip()

    if ':-' not in line:
        raise ValueError(f"Invalid rule (missing ':-'): {line}")

    head_str, body_str = line.split(':-', 1)
    head_pred, head_args = parse_atom(head_str.strip())

    body_parts = [p.strip() for p in split_top_level(body_str) if p.strip() != '']
    body = [parse_literal(part) for part in body_parts]

    return {"head": (head_pred, head_args), "body": body}


def load_kb(path: str) -> Tuple[List[Fact], List[Rule]]:
    """
    Load kb.fol and return (facts, rules).
    Performs:
        - comment removal
        - blank line removal
        - correct statement reconstruction (line-by-line)
    """
    facts: List[Fact] = []
    rules: List[Rule] = []

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned = []
    for raw in lines:
        line = raw.split('%', 1)[0].strip()
        if line == '':
            continue
        cleaned.append(line)

    statements = []
    buffer = ""

    for line in cleaned:
        buffer += " " + line
        if line.endswith('.'):
            statements.append(buffer.strip())
            buffer = ""

    if buffer.strip() != "":
        raise ValueError(f"Unterminated statement in KB: '{buffer.strip()}'")

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
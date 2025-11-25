from typing import Dict, List, Tuple, Any, Generator, Optional
import itertools
import copy
import re

# A "substition" associates variables with concrete values
Subst = Dict[str, Any]

# Facts are tuples: ("Predicate", [arg1, arg2])
Predicate = Tuple[str, List[Any]]

# Literal: {"pred": ..., "args": [...], "negated": True/False}
LiteralDict = Dict[str, Any]

# Rule: {"head":(...), "body":[...]}
RuleDict = Dict[str, Any]

# Variables start with a capital letter: X, Y, Temp etc.
VAR_RE = re.compile(r'^[A-Z_][A-Za-z0-9_]*$')

def is_variable(x: Any) -> bool:
    """Checks if a term is a variable (e.g. X, Y)."""
    return isinstance(x, str) and VAR_RE.match(x) is not None


def occurs_check(var: str, x: Any, theta: Subst) -> bool:
    """
    Avoids cycles like X = f(X).
    True if the variable appears in the term x.
    """
    if var == x:
        return True
    if is_variable(x) and x in theta:
        return occurs_check(var, theta[x], theta)
    if isinstance(x, list):
        return any(occurs_check(var, xi, theta) for xi in x)
    return False


def apply_subst_to_term(term: Any, theta: Subst) -> Any:
    """Apply substitution to a simple term."""
    if is_variable(term):
        # Replace the chain until we reach the final value
        while term in theta:
            term = theta[term]
        return term
    return term


def apply_subst_to_args(args: List[Any], theta: Subst) -> List[Any]:
    """Apply substitution to a list of arguments."""
    return [apply_subst_to_term(a, theta) for a in args]


def compose(theta1: Subst, theta2: Subst) -> Subst:
    """Combine two substitutions into one."""
    res = {}
    # Apply theta2 over theta1 where needed
    for v, val in theta1.items():
        if is_variable(val) and val in theta2:
            res[v] = theta2[val]
        else:
            res[v] = val
    # Add the rest from theta2
    for v, val in theta2.items():
        if v not in res:
            res[v] = val
    return res

def unify(x: Any, y: Any, theta: Subst) -> Optional[Subst]:
    """
    Tries to unify two terms.
    If successful -> returns a new substitution.
    If not -> returns None.
    """
    if theta is None:
        return None
    if x == y:
        return theta

    if is_variable(x):
        return unify_var(x, y, theta)
    if is_variable(y):
        return unify_var(y, x, theta)

    # Unify list-to-list (arguments)
    if isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        new_theta = theta.copy()
        for xi, yi in zip(x, y):
            new_theta = unify(xi, yi, new_theta)
            if new_theta is None:
                return None
        return new_theta

    return None


def unify_var(var: str, x: Any, theta: Subst) -> Optional[Subst]:
    """Special unification for variables."""
    if var in theta:
        return unify(theta[var], x, theta)
    if is_variable(x) and x in theta:
        return unify(var, theta[x], theta)
    if occurs_check(var, x, theta):
        return None
    new_theta = theta.copy()
    new_theta[var] = x
    return new_theta

def facts_for_pred(facts: List[Predicate], pred_name: str) -> List[Predicate]:
    """Returns all facts with the requested predicate name."""
    return [f for f in facts if f[0] == pred_name]


def rules_for_head(rules: List[RuleDict], pred_name: str) -> List[RuleDict]:
    """Returns rules whose head has the same predicate."""
    return [r for r in rules if r["head"][0] == pred_name]

_unique_var_counter = itertools.count()

def rename_rule(rule: RuleDict) -> RuleDict:
    """
    Creates a copy of the rule where all variables are renamed
    with a unique suffix (e.g. X__5). This avoids collisions.
    """
    mapping = {}
    uid = next(_unique_var_counter)

    def rename_term(t):
        if is_variable(t):
            if t not in mapping:
                mapping[t] = f"{t}__{uid}"
            return mapping[t]
        return t

    # rename the head
    new_head_pred = rule["head"][0]
    new_head_args = [rename_term(a) for a in rule["head"][1]]

    # rename the body
    new_body = []
    for lit in rule["body"]:
        new_args = [rename_term(a) for a in lit["args"]]
        new_body.append({
            "pred": lit["pred"],
            "args": new_args,
            "negated": lit.get("negated", False)
        })

    return {"head": (new_head_pred, new_head_args), "body": new_body}

def eval_builtin(pred: str, args: List[Any], theta: Subst) -> bool:
    """Evaluates simple numeric comparisons."""
    resolved = apply_subst_to_args(args, theta)

    try:
        a, b = resolved[0], resolved[1]

        # Uninstantiated variables cannot be compared
        if is_variable(a) or is_variable(b):
            return False

        # Convert numeric strings to int
        if isinstance(a, str) and re.fullmatch(r'-?\d+', a):
            a = int(a)
        if isinstance(b, str) and re.fullmatch(r'-?\d+', b):
            b = int(b)

    except Exception:
        return False

    if pred == "GreaterThan":
        return a > b
    if pred == "LessThan":
        return a < b

    return False

def prove_literal(literal: LiteralDict, facts: List[Predicate], rules: List[RuleDict], theta: Subst) -> Generator[Subst, None, None]:
    """
    Tries to prove a literal.
    If successful, returns compatible substitutions.
    Full implementation of backward chaining.
    """
    pred = literal["pred"]
    args = literal["args"]
    neg = literal.get("negated", False)

    #1. Negation-as-failure
    if neg:
        positive = {"pred": pred, "args": args, "negated": False}
        has_proof = False
        # if the positive literal cannot be proven -> the negation is true
        for _ in prove_literal(positive, facts, rules, theta.copy()):
            has_proof = True
            break
        if not has_proof:
            yield theta
        return

    #2. Built-in predicate
    if pred in ("GreaterThan", "LessThan"):
        if eval_builtin(pred, args, theta):
            yield theta
        return

    #3. Try to prove using facts
    for fact in facts_for_pred(facts, pred):
        fact_args = fact[1]
        new_theta = unify(args, fact_args, theta.copy())
        if new_theta is not None:
            yield new_theta

    #4. Try to prove using rules
    for rule in rules_for_head(rules, pred):
        r = rename_rule(rule)   # avoid variable collisions
        head_pred, head_args = r["head"]

        new_theta = unify(args, head_args, theta.copy())
        if new_theta is None:
            continue

        # prove all literals in the body
        for theta2 in prove_all(r["body"], facts, rules, new_theta):
            yield theta2


def prove_all(literals: List[LiteralDict], facts: List[Predicate], rules: List[RuleDict], theta: Subst) -> Generator[Subst, None, None]:
    """
    Proves a list of conditions (conjunction).
    All must be true.
    """
    if not literals:
        yield theta
        return

    first, *rest = literals

    # prove the current literal
    for theta1 in prove_literal(first, facts, rules, theta):
        # and continue with the rest
        for theta2 in prove_all(rest, facts, rules, theta1):
            yield theta2

def ask(query: LiteralDict, facts: List[Predicate], rules: List[RuleDict]) -> List[Subst]:
    """
    Processes a query and returns a list of solutions (substitutions).
    Example query:
        {"pred": "TurnOnAC", "args": ["X"], "negated": False}
    """
    solutions = []

    # start with an empty substitution
    for theta in prove_literal(query, facts, rules, {}):
        # normalize the result (resolve chains like X=Y, Y=a etc.)
        normalized = {}
        for var, val in theta.items():
            normalized[var] = apply_subst_to_term(val, theta)
        solutions.append(normalized)

    return solutions

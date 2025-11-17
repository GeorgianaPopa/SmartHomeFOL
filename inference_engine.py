from typing import Dict, List, Tuple, Any, Generator, Optional
import itertools
import copy
import re

Subst = Dict[str, Any]            
Predicate = Tuple[str, List[Any]]  
LiteralDict = Dict[str, Any]       
RuleDict = Dict[str, Any]          

VAR_RE = re.compile(r'^[A-Z_][A-Za-z0-9_]*$')

def is_variable(x: Any) -> bool:
    return isinstance(x, str) and VAR_RE.match(x) is not None

def occurs_check(var: str, x: Any, theta: Subst) -> bool:
    """Simple occurs check to avoid X = f(X) cycles — returns True if var occurs in x."""
    if var == x:
        return True
    if is_variable(x) and x in theta:
        return occurs_check(var, theta[x], theta)
    if isinstance(x, list):
        return any(occurs_check(var, xi, theta) for xi in x)
    return False

def apply_subst_to_term(term: Any, theta: Subst) -> Any:
    """Apply substitution to a single term (variable/const/int)."""
    if is_variable(term):
        while term in theta:
            term = theta[term]
        return term
    return term

def apply_subst_to_args(args: List[Any], theta: Subst) -> List[Any]:
    return [apply_subst_to_term(a, theta) for a in args]

def compose(theta1: Subst, theta2: Subst) -> Subst:
    """Return composition theta12 = theta2 o theta1 (apply theta1 then theta2)."""
    res = {}
    for v, val in theta1.items():
        if is_variable(val) and val in theta2:
            res[v] = theta2[val]
        else:
            res[v] = val
    for v, val in theta2.items():
        if v not in res:
            res[v] = val
    return res

def unify(x: Any, y: Any, theta: Subst) -> Optional[Subst]:
    """
    Unify term x and y under substitution theta.
    Terms can be: variable (string starting with uppercase),
                    constant (string lowercase or int),
                    or list of terms (for argument lists, though we unify elementwise).
    Returns new substitution or None if fail.
    """
    if theta is None:
        return None
    if x == y:
        return theta

    if is_variable(x):
        return unify_var(x, y, theta)
    if is_variable(y):
        return unify_var(y, x, theta)

    if isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        new_theta = theta.copy()
        for xi, yi in zip(x, y):
            new_theta = unify(xi, yi, new_theta)
            if new_theta is None:
                return None
        return new_theta

    if x == y:
        return theta
    return None

def unify_var(var: str, x: Any, theta: Subst) -> Optional[Subst]:
    if var in theta:
        return unify(theta[var], x, theta)
    if is_variable(x) and x in theta:
        return unify(var, theta[x], theta)
    # occurs check
    if occurs_check(var, x, theta):
        return None
    new_theta = theta.copy()
    new_theta[var] = x
    return new_theta

def facts_for_pred(facts: List[Predicate], pred_name: str) -> List[Predicate]:
    return [f for f in facts if f[0] == pred_name]

def rules_for_head(rules: List[RuleDict], pred_name: str) -> List[RuleDict]:
    return [r for r in rules if r["head"][0] == pred_name]

_unique_var_counter = itertools.count()

def rename_rule(rule: RuleDict) -> RuleDict:
    """
    Return a renamed copy of rule where each variable is suffixed with a unique id.
    Ensures variables in different rule applications don't clash.
    """
    mapping = {}
    uid = next(_unique_var_counter)
    def rename_term(t):
        if is_variable(t):
            if t not in mapping:
                mapping[t] = f"{t}__{uid}"
            return mapping[t]
        return t

    new_head_pred, new_head_args = rule["head"][0], [rename_term(a) for a in rule["head"][1]]
    new_body = []
    for lit in rule["body"]:
        new_args = [rename_term(a) for a in lit["args"]]
        new_body.append({"pred": lit["pred"], "args": new_args, "negated": lit.get("negated", False)})
    return {"head": (new_head_pred, new_head_args), "body": new_body}

def eval_builtin(pred: str, args: List[Any], theta: Subst) -> bool:
    """
    Evaluate built-in numeric comparisons:
      - GreaterThan(a, b)
      - LessThan(a, b)
    Arguments may be ints, or variables substituted via theta.
    """
    resolved = apply_subst_to_args(args, theta)
    try:
        a = resolved[0]
        b = resolved[1]
        if is_variable(a) or is_variable(b):
            return False
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
    Try to prove a single literal under current substitution theta.
    Yields possible extended substitutions.
    Handles negation-as-failure for literal["negated"] == True.
    """
    pred = literal["pred"]
    args = literal["args"]
    neg = literal.get("negated", False)

    if neg:
        positive = {"pred": pred, "args": args, "negated": False}
        has_proof = False
        for _ in prove_literal(positive, facts, rules, theta.copy()):
            has_proof = True
            break
        if not has_proof:
            yield theta
        return

    if pred in ("GreaterThan", "LessThan"):
        ok = eval_builtin(pred, args, theta)
        if ok:
            yield theta
        return

    for fact in facts_for_pred(facts, pred):
        fact_args = fact[1]
        new_theta = unify(args, fact_args, theta.copy())
        if new_theta is not None:
            yield new_theta

    for rule in rules_for_head(rules, pred):
        r = rename_rule(rule)
        head_pred, head_args = r["head"]
        new_theta = unify(args, head_args, theta.copy())
        if new_theta is None:
            continue
        for theta2 in prove_all(r["body"], facts, rules, new_theta):
            yield theta2

def prove_all(literals: List[LiteralDict], facts: List[Predicate], rules: List[RuleDict], theta: Subst) -> Generator[Subst, None, None]:
    """
    Prove a list (conjunction) of literals. Yields substitutions.
    """
    if not literals:
        yield theta
        return
    first, *rest = literals
    for theta1 in prove_literal(first, facts, rules, theta):
        for theta2 in prove_all(rest, facts, rules, theta1):
            yield theta2

def ask(query: LiteralDict, facts: List[Predicate], rules: List[RuleDict]) -> List[Subst]:
    """
    Ask a single query literal; return list of substitutions (solutions).
    Example query: {"pred":"TurnOnAC", "args":["X"], "negated":False}
    """
    solutions = []
    # initial empty substitution
    for theta in prove_literal(query, facts, rules, {}):
        # normalize substitution values (resolve chains)
        normalized = {}
        for var, val in theta.items():
            normalized[var] = apply_subst_to_term(val, theta)
        solutions.append(normalized)
    return solutions

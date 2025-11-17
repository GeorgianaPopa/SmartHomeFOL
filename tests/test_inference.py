import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kb_parser import load_kb, parse_literal
from inference_engine import unify, ask

def test_unify_simple():
    theta = {}
    assert unify("a", "a", theta) == {}

    theta = {}
    res = unify("X", "a", theta)
    assert res is not None and res.get("X") == "a"

    theta = {}
    res = unify(["X", "b"], ["a", "b"], theta)
    assert res is not None and res.get("X") == "a"

def test_ask_needs_cooling():
    kb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb.fol")
    facts, rules = load_kb(kb_path)
    q = parse_literal("NeedsCooling(X)")
    sols = ask(q, facts, rules)
    found = {sol.get("X") for sol in sols}
    assert "living_room" in found
    assert "kitchen" in found

def test_ask_turn_on_ac():
    kb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb.fol")
    facts, rules = load_kb(kb_path)
    q = parse_literal("TurnOnAC(X)")
    sols = ask(q, facts, rules)
    found = {sol.get("X") for sol in sols}
    assert "living_room" in found
    assert "kitchen" in found

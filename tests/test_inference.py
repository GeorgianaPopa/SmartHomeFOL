import sys
import os

# Ensure the parent project directory is added to Python's module search path.
# This allows importing kb_parser and inference_engine correctly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kb_parser import load_kb, parse_literal
from inference_engine import unify, ask


def test_unify_simple():
    """Basic tests for the unify() function."""
    
    # Case 1: identical constants unify trivially
    theta = {}
    assert unify("a", "a", theta) == {}

    # Case 2: variable X unified with constant 'a'
    theta = {}
    res = unify("X", "a", theta)
    assert res is not None and res.get("X") == "a"

    # Case 3: list unification: [X, b] with [a, b]
    theta = {}
    res = unify(["X", "b"], ["a", "b"], theta)
    assert res is not None and res.get("X") == "a"


def test_ask_needs_cooling():
    """Test inference: which rooms need cooling?"""
    
    # Load KB relative to project root
    kb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb.fol")
    facts, rules = load_kb(kb_path)

    # Query: NeedsCooling(X)
    q = parse_literal("NeedsCooling(X)")
    sols = ask(q, facts, rules)

    # Collect all X solutions returned by inference
    found = {sol.get("X") for sol in sols}

    # Check that expected rooms appear in solutions
    assert "living_room" in found
    assert "kitchen" in found


def test_ask_turn_on_ac():
    """Test inference for TurnOnAC rule."""
    
    kb_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb.fol")
    facts, rules = load_kb(kb_path)

    # Query: TurnOnAC(X)
    q = parse_literal("TurnOnAC(X)")
    sols = ask(q, facts, rules)

    found = {sol.get("X") for sol in sols}

    assert "living_room" in found
    assert "kitchen" in found

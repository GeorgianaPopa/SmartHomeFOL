# Knowledge Base for Smart Homes (FOL)

 ## Overview
 This project uses **First-Order Logic (FOL)** to model a smart home environment.
 It identifies rooms, sensors, and logical rules that deduce new information, like: 
 - Which rooms require heating or cooling; 
 - When lights should be switched off;
 - When to switch on the air conditioner or heater.

 ## Files 
 - `kb.fol`: Knowledge base (rules and facts);
 -`kb_parser.py`.: The FOL knowledge base is loaded and parsed;
 - `inference_engine.py`: Unification and backward chaining;
 - `main.py`: Demo and query interface.

 ## Sample Inquiries
- TurnOnAC(X)?
- NeedsCooling(X)?
- ShouldTurnOffLight(X)?
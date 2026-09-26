import os
import sys

# Ensure models are loaded
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import classifier
from knowledge_base import rag
from dialogue_manager import start_or_continue
import db

def run_tests():
    print("Loading models...")
    classifier.load_models()
    rag.build_index()
    print("Models loaded. Starting test...")
    
    session_id = "test-session-" + os.urandom(4).hex()
    
    print("\n--- Test 1: Greeting ---")
    res = start_or_continue(session_id, "bonjour")
    print(res)
    
    print("\n--- Test 2: FAQ Question ---")
    res = start_or_continue(session_id, "kifech nkhaless el fetoura?")
    print(res)
    
    print("\n--- Test 3: Complaint ---")
    res = start_or_continue(session_id, "mochkla fil me, m9assous 3ala dar")
    print(res)

    print("\n--- Test 4: Tracking ---")
    res = start_or_continue(session_id, "PL-12345678")
    print(res)
    
    print("\n--- Test 5: Off topic ---")
    res = start_or_continue(session_id, "donne moi une recette de pizza")
    print(res)

if __name__ == "__main__":
    run_tests()

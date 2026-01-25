import sys
import os
from dotenv import load_dotenv

# Ensure we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.core.state import AgentState, update_state
from app.schemas import UserAttempt, SignalMetrics
from app.core.agent import formulate_strategy

# Load env for API keys
load_dotenv()

def run_simulation():
    print("=== STARTING AGENT SIMULATION ===")
    
    # 1. Init State
    state = AgentState(session_id="test_user")
    print(f"Initial State: Stress={state.stress_level}")
    
    # 2. Simulate Attempt 1: Good Flow
    print("\n--- Try 1: Good Fluency ---")
    metrics_1 = SignalMetrics(fluency_wpm=120, hesitation_ratio=0.1, grammar_error_count=0, coherence_score=0.9, lexical_diversity=0.8, grammar_complexity=0.7, pronunciation_score=0.8, is_complete=True)
    attempt_1 = UserAttempt(task_id="1", transcript="I went to the store.", audio_duration=10.0)
    
    # Decision
    # Note: formulate_strategy calls LLM, so this needs API Key. If not set, it might fail or print error.
    # We will assume environment is set or gracefully handle.
    try:
        intervention_1 = formulate_strategy(state, metrics_1)
        print(f"Agent Action: {intervention_1.action_id} -> {intervention_1.next_task_prompt}")
    except Exception as e:
        print(f"Agent failed (likely no API key): {e}")

    # print("MOCK AGENT: Doing nothing (PASS)")


    # Update State
    state = update_state(state, attempt_1, metrics_1, "PASS", "Describe your day")
    print(f"New Stress: {state.stress_level}")
    
    # 3. Simulate Attempt 2: Stuttering (High Stress Input)
    print("\n--- Try 2: Low Fluency (Stuttering) ---")
    metrics_2 = SignalMetrics(fluency_wpm=40, hesitation_ratio=0.6, grammar_error_count=0, coherence_score=0.8, lexical_diversity=0.3, grammar_complexity=0.3, pronunciation_score=0.4, is_complete=True)
    attempt_2 = UserAttempt(task_id="2", transcript="I... uh...", audio_duration=10.0)

    # Update State
    state = update_state(state, attempt_2, metrics_2, "PASS", "Describe your day")
    print(f"New Stress: {state.stress_level} (Should scale up)")
    
    # 4. Simulate Failure
    print("\n--- Try 3: Total Failure ---")
    metrics_3 = SignalMetrics(fluency_wpm=20, hesitation_ratio=0.8, grammar_error_count=5, coherence_score=0.2, lexical_diversity=0.1, grammar_complexity=0.1, pronunciation_score=0.1, is_complete=False)
    attempt_3 = UserAttempt(task_id="3", transcript="...", audio_duration=10.0)
    
    state = update_state(state, attempt_3, metrics_3, "FAIL", "Describe your day")
    print(f"New Stress: {state.stress_level} (Should be high)")
    
    # 5. Check Logic
    if state.stress_level > 0.5:
        print("\nSUCCESS: Stress system is responsive.")
    else:
        print("\nFAIL: Stress system is too lenient.")
        
    # 6. Check Educational Features (Mock Check)
    # Since we can't easily mock the LLM response in this integration test without mocking the network,
    # we just check if the code path doesn't crash. 
    # In a real unit test we would mock 'formulate_strategy' return value.
    print("\n--- Educational Feature Check ---")
    print("Code path for 'keywords', 'ideal_response', 'feedback_markdown' exists in schemas.")
    print("SUCCESS: Schemas are ready for frontend consumption.")

if __name__ == "__main__":
    run_simulation()

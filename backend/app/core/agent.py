import os
import json
import re
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from app.core.state import AgentState
from app.schemas import SignalMetrics, Intervention

# Configure DeepInfra
llm = ChatOpenAI(
    base_url="https://api.deepinfra.com/v1/openai",
    api_key=os.getenv("DEEPINFRA_API_KEY"),
    model="meta-llama/Llama-3.2-3B-Instruct",
    temperature=0.1, # Keep it strict
)

def clean_json_string(s: str) -> str:
    """
    Robustly extracts JSON from a string, handling Markdown code blocks 
    and extra conversational text.
    """
    # 1. Try to find content inside ```json ... ``` blocks first (Common in Llama)
    json_block = re.search(r"```json\s*(\{.*?\})\s*```", s, re.DOTALL)
    if json_block:
        return json_block.group(1)

    # 2. If no code blocks, look for the first outer { and last }
    json_match = re.search(r"(\{.*\})", s, re.DOTALL)
    if json_match:
        return json_match.group(1)
        
    # 3. If nothing is found, return empty
    return ""

def formulate_strategy(state: AgentState, current_metrics: SignalMetrics) -> Intervention:
    """
    Decides the next intervention based on the full User Session State.
    """
    
    # 1. Construct History Context (Compact format)
    history_str = "\n".join([
        f"- Attempt {h.attempt_id}: {h.outcome} (WPM: {h.metrics.fluency_wpm}, Coherence: {h.metrics.coherence_score})" 
        for h in state.history[-3:] # Last 3 only
    ])
    
    prompt = f"""
    You are the "Intervention Policy Engine" for an IELTS training app. 
    Your goal is to manage the user's cognitive load to maximize learning pressure without causing panic.

    USER STATE:
    - Stress Level: {state.stress_level:.2f} (0.0=Sleepy, 1.0=Panic)
    - Fluency Trend: {state.fluency_trend}
    - Consecutive Failures: {state.consecutive_failures}
    
    CURRENT ATTEMPT METRICS:
    - WPM: {current_metrics.fluency_wpm} (Target: >100)
    - Hesitation: {current_metrics.hesitation_ratio} (Target: <0.2)
    - Coherence: {current_metrics.coherence_score} (Target: >0.5)
    
    RECENT HISTORY:
    {history_str}

    LOGIC MATRIX:
    
    1. IF Coherence < 0.5:
       ACTION: "FAIL"
       Constraint: "Explain clearly."
       
    2. IF Stress > 0.8:
       ACTION: "DEESCALATE_PRESSURE"
       Constraint: +20% Time.
       
    3. IF WPM < 90 AND Stress < 0.5:
       ACTION: "ESCALATE_PRESSURE"
       Constraint: -10% Time.
       
    4. IF Filler Words > 3:
       ACTION: "MAINTAIN"
       Constraint: "Avoid using 'um' or 'uh'."
       
    5. OTHERWISE:
       ACTION: "MAINTAIN" 
       
    TEACHING MODE (REQUIRED):
    - `ideal_response`: Rewrite the user's attempt as a Band 7.0 Native Speaker response (1-2 sentences).
    - `feedback_markdown`: Bullet point list of specific grammar or vocabulary improvements.
    - `keywords`: List of 5 sophisticated words relevant to the NEXT topic.
      * CRITICAL: If User WPM < 60 (Low Fluency), provide SIMPLE but useful connectors (e.g., "However", "Therefore", "In my opinion").
      * If User Fluency is High, provide SOPHISTICATED idioms.
    
    RESPONSE FORMAT:
    {{
      "action_id": "MAINTAIN" | "ESCALATE_PRESSURE" | "DEESCALATE_PRESSURE" | "FORCE_RETRY" | "DRILL_SPECIFIC" | "FAIL",
      "next_task_prompt": "string",
      "topic_core": "string",
      "constraints": {{ "timer": int, "strictness": "low"|"high" }},
      "ideal_response": "string",
      "feedback_markdown": "string",
      "keywords": ["string", "string", "string", "string", "string"]
    }}
    """
    
    print(f"--- AGENT: Analyzing State (Stress: {state.stress_level}) ---")
    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        raw_content = response.content
        
        json_str = clean_json_string(raw_content)
        if not json_str:
            raise ValueError("No JSON found")
            
        data = json.loads(json_str)
        return Intervention(**data)
        
    except Exception as e:
        print(f"AGENT ERROR: {e}")
        return Intervention(
            action_id="MAINTAIN",
            next_task_prompt="Continue. Describe your favorite meal.",
            topic_core="Food", 
            constraints={"timer": 45}
        )
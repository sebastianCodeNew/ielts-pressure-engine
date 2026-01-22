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

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

# Configure Output Parser
parser = PydanticOutputParser(pydantic_object=Intervention)

def formulate_strategy(state: AgentState, current_metrics: SignalMetrics, current_part: str = "PART_1") -> Intervention:
    """
    Decides the next intervention based on the full User Session State.
    """
    
    # 1. Construct History Context (Compact format)
    history_str = "\n".join([
        f"- Attempt {h.attempt_id}: {h.outcome} (WPM: {h.metrics.fluency_wpm}, Coherence: {h.metrics.coherence_score})" 
        for h in state.history[-3:] # Last 3 only
    ])
    
    # 2. Define Prompt with Format Instructions
    prompt_template = PromptTemplate(
        template="""
        You are an expert IELTS Speaking Examiner. 
        CURRENT PART: {current_part}

        GOAL: Assess the user's performance and provide detailed educational feedback.

        USER STATE:
        - Stress Level: {stress_level:.2f}
        - Fluency Trend: {fluency_trend}
        
        CURRENT ATTEMPT METRICS:
        - WPM: {wpm}
        - Coherence: {coherence}
        
        LOGIC MATRIX:
        - If in PART 1: Ask personal, simple questions.
        - If in PART 2: Provide a complex topic for a 2-minute "Cue Card" speech.
        - If in PART 3: Ask abstract, analytical questions based on the Part 2 topic.

        SCORING (0-9):
        - `detailed_scores`: Provide scores for Fluency, Coherence, Lexical Resource, Grammar, and Pronunciation.
        
        TEACHING FEEDBACK:
        - `grammar_advice`: One specific correction.
        - `vocabulary_advice`: One better word.
        - `pronunciation_advice`: One word to practice pronouncing.
        
        {format_instructions}
        """,
        input_variables=["stress_level", "fluency_trend", "consecutive_failures", "wpm", "hesitation", "coherence", "history", "current_part"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    print(f"--- AGENT: Analyzing State (Part: {current_part}) ---")
    
    try:
        # 3. Invoke Chain
        formatted_prompt = prompt_template.format(
            stress_level=state.stress_level,
            fluency_trend=state.fluency_trend,
            consecutive_failures=state.consecutive_failures,
            wpm=current_metrics.fluency_wpm,
            hesitation=current_metrics.hesitation_ratio,
            coherence=current_metrics.coherence_score,
            history=history_str,
            current_part=current_part
        )
        
        response = llm.invoke([SystemMessage(content=formatted_prompt)])
        
        # 4. Parse Output
        intervention = parser.parse(response.content)
        return intervention
        
    except Exception as e:
        print(f"AGENT ERROR: {e}")
        # Fallback
        return Intervention(
            action_id="MAINTAIN",
            next_task_prompt="Continue. Describe your favorite meal.",
            topic_core="Food", 
            constraints={"timer": 45},
            ideal_response="I enjoy eating pasta because it is versatile and delicious.",
            feedback_markdown="- Speak more confidently.\n- Avoid pauses.",
            keywords=["Delicious", "Versatile", "Cuisine", "Texture", "Flavor"]
        )
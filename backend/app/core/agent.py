import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from app.core.state import AgentState
from app.schemas import SignalMetrics, Intervention

# Configure DeepInfra
llm = ChatOpenAI(
    base_url="https://api.deepinfra.com/v1/openai",
    api_key=os.getenv("DEEPINFRA_API_KEY"),
    model="meta-llama/Llama-3.3-70B-Instruct",
    temperature=0.1, 
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
        for h in state.history[-3:]
    ])
    
    # 2. Define Prompt with Format Instructions
    prompt_template = PromptTemplate(
        template="""
        You are an expert IELTS Speaking Examiner. 
        CURRENT PART: {current_part}

        GOAL: Assess the user's performance and provide detailed educational feedback.
        
        USER PROFILE:
        - Target Band: {target_band}
        - Key Weakness: {weakness}

        USER STATE:
        - Stress Level: {stress_level:.2f}
        - Fluency Trend: {fluency_trend}
        
        CURRENT ATTEMPT METRICS:
        - WPM: {wpm}
        - Coherence: {coherence}
        - Lexical Diversity (TTR): {lexical_diversity}
        - Grammar Complexity: {grammar_complexity}
        
        ADAPTIVE LOGIC:
        - Compare metrics against Target Band {target_band}.
        - If USER WEAKNESS is "{weakness}", focus feedback specifically on that area.
        - If user is performing BELOW target, simplify questions and be encouraging.
        - If user is performing AT/ABOVE target, challenge them with abstract/complex follow-ups.

        SCORING (0-9):
        - Provide scores for Fluency, Coherence, Lexical Resource, Grammar, and Pronunciation based on IELTS band descriptors.
        
        FEEDBACK:
        - Be constructive and specific.
        
        SEMANTIC GAP ANALYSIS:
        - Contrast the user's response with what a Band 9 "Ideal Response" would cover.
        - Identify at least one "Semantic Gap": a specific concept, detail, or idea the user missed that would have added depth.
        - Include this in a section titled "Semantic Gap" in the `feedback_markdown`.
        
        LEXICAL MISSION:
        - Identify 3 advanced (Band 8+) vocabulary items or idioms relevant to the *next question* you are about to ask.
        - List them in the `target_keywords` field.
        
        {format_instructions}
        """,
        input_variables=["stress_level", "fluency_trend", "consecutive_failures", "wpm", "hesitation", "coherence", "lexical_diversity", "grammar_complexity", "history", "current_part", "target_band", "weakness"],
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
            lexical_diversity=current_metrics.lexical_diversity,
            grammar_complexity=current_metrics.grammar_complexity,
            history=history_str,
            current_part=current_part,
            target_band=state.target_band,
            weakness=state.weakness
        )
        
        # We should include the formatted content in the message
        response = llm.invoke(formatted_prompt)
        
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
            keywords=["Delicious", "Versatile", "Cuisine", "Texture", "Flavor"],
            target_keywords=["culinary", "delectable", "gastronomy"]
        )
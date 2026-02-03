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

def formulate_strategy(
    state: AgentState, 
    current_metrics: SignalMetrics, 
    current_part: str = "PART_1",
    context_override: str = None,
    user_transcript: str = "",
    chronic_issues: str = ""
) -> Intervention:
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
        - CHRONIC ISSUES (Recurring errors from past sessions): {chronic_issues}
        
        USER WEAKNESS PROFILE (Historical Averages):
        - Avg Fluency: {avg_fluency:.1f} | Avg Coherence: {avg_coherence:.1f}
        - Avg Lexical: {avg_lexical:.1f} | Avg Grammar: {avg_grammar:.1f}
        - LOWEST SCORE AREA: {lowest_area}
        
        ADAPTIVE QUESTIONING MANDATE:
        - Your NEXT QUESTION must specifically target the user's LOWEST SCORE AREA ({lowest_area}).
        - If {lowest_area} is "Coherence": Ask "compare and contrast" or "cause and effect" questions.
        - If {lowest_area} is "Lexical": Ask about topics requiring specialized vocabulary.
        - If {lowest_area} is "Grammar": Ask hypothetical or conditional questions.
        - If {lowest_area} is "Fluency": Ask simpler, faster-paced questions.

        USER STATE:
        - Stress Level: {stress_level:.2f}
        - Fluency Trend: {fluency_trend}
        
        EXTRA CONTEXT:
        {context_override}

        USER TRANSCRIPT:
        {user_transcript}

        CURRENT ATTEMPT METRICS:
        - WPM: {wpm}
        - Coherence: {coherence}
        - Lexical Diversity (TTR): {lexical_diversity}
        - Grammar Complexity: {grammar_complexity}
        
        ADAPTIVE LOGIC:
        - Compare metrics against Target Band {target_band}.
        - EXAMINER PERSONALITY (Dynamic):
            * If `stress_level` > 0.7 or `fluency_trend` is "declining": Become a SUPPORTIVE MENTOR. Use encouraging, simpler language. Soften the pressure.
            * If `stress_level` < 0.4 and performance is AT/ABOVE target: Become a STRICT CHALLENGER. Use formal, professional language. Be more direct and less emotive.
        - If USER WEAKNESS is "{weakness}", focus feedback specifically on that area.
        - If user is performing BELOW target, simplify questions and be encouraging.
        - If user is performing AT/ABOVE target, challenge them with abstract/complex follow-ups.

        SCORING (0-9):
        - Provide scores for Fluency, Coherence, Lexical Resource, Grammar, and Pronunciation based on IELTS band descriptors.
        
        FEEDBACK:
        - Be constructive and specific.
        
        IDEAL RESPONSE (The Refined Version):
        - Do NOT provide a generic response.
        - REWRITE the `USER TRANSCRIPT` into a Band 9 version.
        - Maintain the user's original ideas, but upgrade the grammar to be complex and the vocabulary to be sophisticated (Band 8+).
        - Put this refined version in the `ideal_response` field.

        SEMANTIC GAP ANALYSIS:
        - Contrast the refined response with what the user actually said.
        - Identify at least one "Semantic Gap": a specific concept, detail, or idea the user missed that would have added depth.
        - Include this in a section titled "Semantic Gap" in the `feedback_markdown`.
        
        CORRECTION DRILL:
        - Identify the ONE biggest grammatical or lexical mistake in the `USER TRANSCRIPT`.
        - Create a very short "Correction Drill" in the `correction_drill` field.
        
        REASONING:
        - In the `reasoning` field, explain in ONE sentence WHY this specific correction or lexical mission matters for the IELTS Band 7+ criteria (e.g., "Using complex connectors like 'nevertheless' helps you achieve Band 7+ in Coherence and Cohesion.").
        
        LEXICAL MISSION:
        - Identify 3 advanced (Band 8+) vocabulary items or idioms relevant to the *next question* you are about to ask.
        - List them in the `target_keywords` field.
        
        NEW: SOCRATIC PROBING (v2.0):
        - If current part is "PART_3" AND (`coherence` < 0.6 or `lexical_diversity` < 0.5):
            * Set `is_probing` to true.
            * Do NOT move to a new topic.
            * Ask a follow-up ("Probe") that forces the user to explain 'Why' or 'How' in more depth.
            * Set `interjection_type` to 'ELABORATION' or 'CAUSE_EFFECT'.
        
        NEW: REFACTOR MISSIONS (v2.0):
        - If `user_transcript` has a clear grammatical error or simple vocabulary:
            * Generate a `refactor_mission`.
            * Example: "Re-say your last answer, but replace 'good' with 'extraordinary'."
            * Example: "Try that sentence again, but use a conditional (If I had... I would have...)."
            * This mission should be ONE short, actionable sentence.

        {format_instructions}
        """,
        input_variables=["stress_level", "fluency_trend", "consecutive_failures", "wpm", "hesitation", "coherence", "lexical_diversity", "grammar_complexity", "history", "current_part", "target_band", "weakness", "context_override", "user_transcript", "avg_fluency", "avg_coherence", "avg_lexical", "avg_grammar", "lowest_area", "chronic_issues"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # Calculate historical weakness profile
    avg_fluency, avg_coherence, avg_lexical, avg_grammar = 5.0, 5.0, 5.0, 5.0
    if state.history:
        fluency_scores = [h.metrics.fluency_wpm / 15 for h in state.history if h.metrics.fluency_wpm]
        coherence_scores = [h.metrics.coherence_score * 9 for h in state.history if h.metrics.coherence_score]
        lexical_scores = [h.metrics.lexical_diversity * 15 for h in state.history if h.metrics.lexical_diversity]
        grammar_scores = [h.metrics.grammar_complexity * 40 for h in state.history if h.metrics.grammar_complexity]
        
        if fluency_scores: avg_fluency = min(9, sum(fluency_scores) / len(fluency_scores))
        if coherence_scores: avg_coherence = min(9, sum(coherence_scores) / len(coherence_scores))
        if lexical_scores: avg_lexical = min(9, sum(lexical_scores) / len(lexical_scores))
        if grammar_scores: avg_grammar = min(9, sum(grammar_scores) / len(grammar_scores))
    
    # Determine lowest scoring area
    scores = {"Fluency": avg_fluency, "Coherence": avg_coherence, "Lexical": avg_lexical, "Grammar": avg_grammar}
    lowest_area = min(scores, key=scores.get)

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
            weakness=state.weakness,
            context_override=context_override or "None provided.",
            user_transcript=user_transcript or "No transcript available.",
            avg_fluency=avg_fluency,
            avg_coherence=avg_coherence,
            avg_lexical=avg_lexical,
            avg_grammar=avg_grammar,
            lowest_area=lowest_area,
            chronic_issues=chronic_issues or "None identified."
        )
        
        response = llm.invoke(formatted_prompt)
        content = response.content.strip()

        # 4. Robust JSON Extraction
        # Look for the first '{' and the last '}'
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            content = match.group(0)
        
        # 5. Parse Output
        intervention = parser.parse(content)
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
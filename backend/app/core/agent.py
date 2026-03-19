import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from app.core.state import AgentState
from app.schemas import SignalMetrics, Intervention

from app.core.config import settings

# Configure DeepInfra
llm = ChatOpenAI(
    base_url=settings.DEEPINFRA_BASE_URL,
    api_key=settings.DEEPINFRA_API_KEY,
    model=settings.EVALUATOR_MODEL,
    temperature=0.1,
    timeout=60, # Increased for stability under heavy load
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

        TOPIC CONTEXT VALIDATION:
        - Check if user's response matches the asked topic
        - If user talks about different topic, gently redirect: "I notice you're talking about [topic]. Let's focus on [original_topic]."
        - Example: If asked about music but user talks about family, redirect gently

        GRAMMAR ERROR DETECTION:
        - Look for common grammar mistakes in user transcript:
          * Subject-verb agreement: "My family is created" → "My family was" or "I was"
          * Tense confusion: "family is created" (past event with present tense)
          * Word choice: "family is created" (unnatural phrasing)
        - Provide specific correction in feedback

        CURRENT ATTEMPT METRICS:
        - WPM: {wpm}
        - Coherence: {coherence}
        - Lexical Diversity (TTR): {lexical_diversity}
        - Grammar Complexity: {grammar_complexity}
        
        ADAPTIVE LOGIC:
        - Compare metrics against Target Band {target_band}.
        - EXAMINER PERSONALITY (Dynamic):
            * If `stress_level` > {stress_inc_threshold} or `fluency_trend` is "declining": Become a SUPPORTIVE MENTOR. Use encouraging, simpler language. Soften the pressure.
            * If `stress_level` < {stress_dec_threshold} and performance is AT/ABOVE target: Become a STRICT CHALLENGER. Use formal, professional language. Be more direct and less emotive.
        - If USER WEAKNESS is "{weakness}", focus feedback specifically on that area.
        - If user is performing BELOW target, simplify questions and be encouraging.
        - If user is performing AT/ABOVE target, challenge them with abstract/complex follow-ups.

        SCORING (0-9):
        - Provide scores for Fluency, Coherence, Lexical Resource, Grammar, and Pronunciation based on IELTS band descriptors.
        
        FEEDBACK:
        - Be constructive and specific.
        - If `user_transcript` is empty or silent, provide feedback about speaking clearly and checking the recording.
        
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
        - If current part is "PART_3" AND (`coherence` < 0.6 or `lexical_diversity` < 0.5) AND "TRANSITION" not in str({context_override}):
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

        NEW: CUE COMPLIANCE (v5.0 - PART 2 ONLY):
        - If `current_part` is "PART_2", verify if the user addressed all bullet points in the cue card (provided in `context_override`).
        - If any were missed, mention it gently in the `feedback_markdown`.
        - Do NOT penalize too harshly if the talk was otherwise fluent, but note it for "Task Response".

        NEW: EXAMINER BRIDGES (v5.0):
        - If `context_override` contains "TRANSITION", your `next_task_prompt` MUST begin with a professional bridge.
        - Example P1->P2: "Thank you. Now, for Part 2, I'm going to give you a topic..."
        - Example P2->P3: "We've been talking about [Topic], and now I'd like to discuss one or two more general questions related to this..."
        
        NEW: REAL-TIME WORD BANK (v3.0):
        - Identify 5 "Power Words" (Band 8+ advanced vocabulary or idioms) that are highly relevant to the *next* question/topic you are about to ask.
        - These should be practical for use in natural speech.
        - List them in the `realtime_word_bank` field.
        - List their Indonesian translations in the `realtime_word_bank_translated` field (in the same order).

        NEW: ACTIVE RECALL QUIZ (v4.0):
        - If you identified a grammar or vocabulary error in `correction_drill`, generate a quick quiz:
            * `quiz_question`: A short question testing the specific rule (e.g., "Which sentence uses correct subject-verb agreement?")
            * `quiz_options`: 4 options (A, B, C, D). The FIRST option (index 0) must be the CORRECT answer.
            * Example: ["The group of students is here.", "The group of students are here.", "The students is here.", "The group are here."]
        - If no quiz is needed, leave these fields as null.

        {format_instructions}
        """,
        input_variables=["stress_level", "fluency_trend", "consecutive_failures", "wpm", "hesitation", "coherence", "lexical_diversity", "grammar_complexity", "history", "current_part", "target_band", "weakness", "context_override", "user_transcript", "avg_fluency", "avg_coherence", "avg_lexical", "avg_grammar", "lowest_area", "chronic_issues"],
        partial_variables={
            "format_instructions": parser.get_format_instructions(),
            "stress_inc_threshold": settings.STRESS_INCREASE_THRESHOLD,
            "stress_dec_threshold": settings.STRESS_DECREASE_THRESHOLD
        }
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
        
        # Strategy: Look for json code blocks first, then widest braces
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
        else:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                content = match.group(0)
        
        # 5. Parse Output
        try:
            intervention = parser.parse(content)
        except Exception as parse_err:
            print(f"DEBUG: Pydantic parsing failed: {parse_err}")
            print(f"DEBUG: Raw LLM output (truncated): {content[:800]}")
            try:
                raw_data = json.loads(content)
            except Exception as json_err:
                print(f"DEBUG: json.loads failed: {json_err}")
                # Re-raise to trigger the outer fallback (and keep logs)
                raise
            
            # Map raw fields safely to prevent initialization errors
            safe_data = {
                "action_id": raw_data.get("action_id", "MAINTAIN"),
                "next_task_prompt": raw_data.get("next_task_prompt", "Continue speaking."),
                "constraints": raw_data.get("constraints", {"timer": 45}),
                "ideal_response": raw_data.get("ideal_response", ""),
                "feedback_markdown": raw_data.get("feedback_markdown", "Well done, keep going."),
                "stress_level": raw_data.get("stress_level", state.stress_level)
            }
            # Only pass fields that exists in Pydantic model to avoid unexpected keyword errors
            intervention = Intervention(**safe_data)
            
        return intervention
        
    except Exception as e:
        print(f"AGENT ERROR: {e}")
        # Fallback: keep it aligned with the user's transcript to avoid confusing topic drift.
        fallback_feedback = (
            " **AI Evaluator Timeout**: Evaluasi AI sedang lambat/timeout. "
            "Saya tetap menyimpan jawaban Anda. Silakan klik submit lagi atau lanjut ke pertanyaan berikutnya."
        )
        return Intervention(
            action_id="MAINTAIN",
            next_task_prompt="Continue.",
            topic_core=None,
            constraints={"timer": 45},
            ideal_response=(user_transcript or ""),
            feedback_markdown=fallback_feedback,
            keywords=None,
            target_keywords=[]
        )

async def formulate_strategy_async(
    state: AgentState, 
    current_metrics: SignalMetrics, 
    current_part: str = "PART_1",
    context_override: str = None,
    user_transcript: str = "",
    chronic_issues: str = ""
) -> Intervention:
    """
    Decides the next intervention based on the full User Session State (Async).
    """
    
    # Calculate historical averages
    avg_fluency, avg_coherence, avg_lexical, avg_grammar = 5.0, 5.0, 5.0, 5.0
    if state.history:
        f_vals = [h.metrics.fluency_wpm / 15 for h in state.history if h.metrics.fluency_wpm]
        c_vals = [h.metrics.coherence_score * 9 for h in state.history if h.metrics.coherence_score]
        l_vals = [h.metrics.lexical_diversity * 15 for h in state.history if h.metrics.lexical_diversity]
        g_vals = [h.metrics.grammar_complexity * 40 for h in state.history if h.metrics.grammar_complexity]
        if f_vals: avg_fluency = min(9, sum(f_vals) / len(f_vals))
        if c_vals: avg_coherence = min(9, sum(c_vals) / len(c_vals))
        if l_vals: avg_lexical = min(9, sum(l_vals) / len(l_vals))
        if g_vals: avg_grammar = min(9, sum(g_vals) / len(g_vals))
    
    scores = {"Fluency": avg_fluency, "Coherence": avg_coherence, "Lexical": avg_lexical, "Grammar": avg_grammar}
    lowest_area = min(scores, key=scores.get)

    history_str = "\n".join([
        f"- Attempt {h.attempt_id}: {h.outcome} (WPM: {h.metrics.fluency_wpm}, Coherence: {h.metrics.coherence_score})" 
        for h in state.history[-3:]
    ])

    prompt_template = PromptTemplate(
        template="""
        You are an expert IELTS Speaking Examiner. 
        CURRENT PART: {current_part}
        GOAL: Assess the user's performance and provide detailed educational feedback.
        USER PROFILE:
        - Target Band: {target_band}
        - Key Weakness: {weakness}
        - CHRONIC ISSUES: {chronic_issues}
        USER WEAKNESS PROFILE:
        - Avg Fluency: {avg_fluency:.1f} | Avg Coherence: {avg_coherence:.1f}
        - Avg Lexical: {avg_lexical:.1f} | Avg Grammar: {avg_grammar:.1f}
        - LOWEST SCORE AREA: {lowest_area}
        USER STATE:
        - Stress Level: {stress_level:.2f}
        EXTRA CONTEXT:
        {context_override}
        USER TRANSCRIPT:
        {user_transcript}
        CURRENT ATTEMPT METRICS:
        - WPM: {wpm} | Coherence: {coherence}
        - Lexical: {lexical_diversity} | Grammar: {grammar_complexity}
        FEEDBACK: Be constructive. Provide a Band 9 'ideal_response'.
        {format_instructions}
        """,
        input_variables=["stress_level", "wpm", "coherence", "lexical_diversity", "grammar_complexity", "current_part", "target_band", "weakness", "user_transcript", "avg_fluency", "avg_coherence", "avg_lexical", "avg_grammar", "lowest_area", "chronic_issues", "context_override"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    try:
        formatted = prompt_template.format(
            stress_level=state.stress_level,
            wpm=current_metrics.fluency_wpm,
            coherence=current_metrics.coherence_score,
            lexical_diversity=current_metrics.lexical_diversity,
            grammar_complexity=current_metrics.grammar_complexity,
            current_part=current_part,
            target_band=state.target_band,
            weakness=state.weakness,
            user_transcript=user_transcript or "No transcript.",
            avg_fluency=avg_fluency,
            avg_coherence=avg_coherence,
            avg_lexical=avg_lexical,
            avg_grammar=avg_grammar,
            lowest_area=lowest_area,
            chronic_issues=chronic_issues or "None.",
            context_override=context_override or "None provided."
        )
        
        response = await llm.ainvoke(formatted)
        content = response.content.strip()
        
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1).strip()
        else:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                content = match.group(0)
        
        return parser.parse(content)
        
    except Exception as e:
        print(f"ASYNC AGENT ERROR: {e}")
        return Intervention(
            action_id="MAINTAIN",
            next_task_prompt="Continue.",
            constraints={"timer": 45},
            ideal_response=user_transcript or "",
            feedback_markdown="Evaluasi AI tertunda karena trafik tinggi. Teruslah berlatih."
        )
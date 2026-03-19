import asyncio
import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.agent import formulate_strategy_async
from app.core.state import AgentState
from app.schemas import SignalMetrics, Intervention

async def test_retry_logic():
    print("🚀 Testing LLM Retry Logic (Simulating 2 failures)...")
    
    # Mock parameters
    state = AgentState(session_id="test", stress_level=0.5, consecutive_failures=0, fluency_trend="stable")
    metrics = SignalMetrics(fluency_wpm=100.0, hesitation_ratio=0.1, grammar_error_count=0)
    
    fail_count = 0
    
    async def side_effect(*args, **kwargs):
        nonlocal fail_count
        if fail_count < 2:
            fail_count += 1
            print(f"   (Simulation) LLM Failure {fail_count}...")
            raise Exception("Transient DeepInfra Error")
        
        print("   (Simulation) LLM Success!")
        mock_response = MagicMock()
        mock_response.content = '{"action_id": "MAINTAIN", "next_task_prompt": "Success", "constraints": {"timer": 45}}'
        return mock_response
    
    # Replace the whole llm object with a mock
    with patch("app.core.agent.llm") as mock_llm:
        mock_llm.ainvoke.side_effect = side_effect
        
        start_time = asyncio.get_event_loop().time()
        try:
            result = await formulate_strategy_async(state, metrics)
            end_time = asyncio.get_event_loop().time()
            print(f"✅ Retry Successful. Action: {result.action_id}")
            print(f"   Took {end_time - start_time:.2f}s")
            assert fail_count == 2
        except Exception as e:
            print(f"❌ Retry Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_retry_logic())

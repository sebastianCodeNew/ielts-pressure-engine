import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.llm import get_llm
from app.core.config import settings

def test_llm_factory():
    print("🚀 Testing LLM Factory Centralization...")
    
    # Test 1: Default configuration
    llm_default = get_llm()
    assert llm_default.model_name == settings.EVALUATOR_MODEL
    assert llm_default.temperature == 0.1
    print("✅ Default LLM configuration verified.")

    # Test 2: Custom temperature
    llm_custom = get_llm(temperature=0.7)
    assert llm_custom.temperature == 0.7
    print("✅ Custom LLM temperature verified.")

    # Test 3: Timeout propagation
    llm_timeout = get_llm(timeout=30)
    assert llm_timeout.request_timeout == 30
    print("✅ LLM timeout propagation verified.")

    print("\n🎉 LLM Factory verified successfully!")

if __name__ == "__main__":
    test_llm_factory()

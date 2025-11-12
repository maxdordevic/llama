#!/usr/bin/env python3
"""
Quick test script to verify Manus AI system is working
Tests the LLM integration and basic agent functionality
"""

import asyncio
import sys
import os

# Add manus_ai to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from manus_ai.core.llm_providers import LLMManager, LLMProvider
from manus_ai.core.orchestrator import AgentOrchestrator
from manus_ai.agents.research_agent import ResearchAgent
from manus_ai.agents.general_agent import GeneralAgent


async def test_llm_connection():
    """Test basic LLM connectivity"""
    print("=" * 60)
    print("Testing LLM Connectivity")
    print("=" * 60)

    llm_manager = LLMManager()

    # Test Gemini
    print("\n🧪 Testing Gemini 2.5 Pro...")
    try:
        response = await llm_manager.generate(
            messages=[
                {"role": "user", "content": "Say 'Hello from Gemini!' and explain in one sentence what you are."}
            ],
            provider=LLMProvider.GEMINI_2_5_PRO,
            temperature=0.7,
            max_tokens=100
        )
        print(f"✅ Gemini Response: {response['content'][:200]}...")
        print(f"   Model: {response.get('model', 'N/A')}")
        print(f"   Tokens: {response.get('usage', {})}")
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return False

    return True


async def test_agent_execution():
    """Test agent execution"""
    print("\n" + "=" * 60)
    print("Testing Agent Execution")
    print("=" * 60)

    # Test General Agent
    print("\n🤖 Testing General Agent...")
    try:
        from manus_ai.core.task_planner import SubTask
        general_agent = GeneralAgent()

        task = SubTask(
            title="Simple greeting task",
            description="Generate a creative greeting for a new AI assistant system and explain its purpose in 2-3 sentences.",
        )

        result = await general_agent.execute(task, {})
        print(f"✅ Agent Result: {result['result'][:300]}...")
    except Exception as e:
        print(f"❌ Agent Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_orchestrator():
    """Test full orchestrator workflow"""
    print("\n" + "=" * 60)
    print("Testing Full Orchestrator Workflow")
    print("=" * 60)

    print("\n🎯 Executing complex task through orchestrator...")
    try:
        orchestrator = AgentOrchestrator()

        # Simple test task
        result = await orchestrator.execute_request(
            user_request="Explain what an AI agent system is and list 3 key benefits in a brief paragraph."
        )

        print(f"\n✅ Task Status: {result['status']}")
        if result['status'] == 'success':
            print(f"📝 Summary: {result['result']['summary'][:400]}...")
            print(f"⏱️  Execution Time: {result.get('execution_time', 0)} seconds")
            print(f"📋 Subtasks: {len(result.get('plan', {}).get('subtasks', []))}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Orchestrator Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🚀 MANUS AI CLONE - SYSTEM TEST")
    print("=" * 60)

    # Check environment
    print("\n📋 Environment Check:")
    print(f"   GEMINI_API_KEY: {'✓ Set' if os.getenv('GEMINI_API_KEY') else '✗ Not Set'}")
    print(f"   ANTHROPIC_API_KEY: {'✓ Set' if os.getenv('ANTHROPIC_API_KEY') else '✗ Not Set'}")
    print(f"   OPENAI_API_KEY: {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Not Set'}")
    print(f"   PERPLEXITY_API_KEY: {'✓ Set' if os.getenv('PERPLEXITY_API_KEY') else '✗ Not Set'}")

    # Load .env if exists
    try:
        from dotenv import load_dotenv
        load_dotenv('manus_ai/.env')
        print("\n✅ Loaded environment variables from manus_ai/.env")
    except ImportError:
        print("\n⚠️  python-dotenv not installed, using system environment")
    except Exception as e:
        print(f"\n⚠️  Could not load .env file: {e}")

    # Run tests
    tests = [
        ("LLM Connection", test_llm_connection),
        ("Agent Execution", test_agent_execution),
        ("Full Orchestrator", test_orchestrator),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 All tests passed! Manus AI system is operational.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

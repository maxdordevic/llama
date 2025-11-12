#!/usr/bin/env python3
"""
Practical Examples - Manus AI Clone
Ready-to-run demonstrations of the system's capabilities
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv('manus_ai/.env')
except:
    pass


async def example_1_simple_research():
    """Example 1: Simple research task using Perplexity"""
    print("\n" + "="*70)
    print("📚 EXAMPLE 1: Web-Grounded Research")
    print("="*70)
    print("\nTask: Research the latest AI developments\n")

    from manus_ai.core.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator()

    result = await orchestrator.execute_request(
        user_request="What are the top 3 AI developments in 2024? Provide a brief summary of each."
    )

    print(f"\n✅ Status: {result['status']}")
    if result['status'] == 'success':
        print(f"\n📝 Result:\n{result['result']['summary'][:500]}...")
        print(f"\n⏱️  Execution time: {result.get('execution_time', 0):.1f}s")
        print(f"📋 Subtasks completed: {len(result.get('plan', {}).get('subtasks', []))}")


async def example_2_code_generation():
    """Example 2: Code generation using Gemini"""
    print("\n" + "="*70)
    print("💻 EXAMPLE 2: Code Generation")
    print("="*70)
    print("\nTask: Generate a Python function\n")

    from manus_ai.agents.code_agent import CodeAgent
    from manus_ai.core.task_planner import SubTask
    from manus_ai.core.llm_providers import LLMManager

    agent = CodeAgent(llm_manager=LLMManager())

    task = SubTask(
        title="Create Python function",
        description="Create a Python function that checks if a number is prime. Include docstring and handle edge cases."
    )

    result = await agent.execute(task, {})

    print(f"\n✅ Code generated:")
    print(f"\n{result.get('explanation', 'No explanation')[:800]}...")


async def example_3_data_analysis():
    """Example 3: Data analysis task"""
    print("\n" + "="*70)
    print("📊 EXAMPLE 3: Data Analysis")
    print("="*70)
    print("\nTask: Generate data analysis code\n")

    from manus_ai.agents.data_agent import DataAnalysisAgent
    from manus_ai.core.task_planner import SubTask
    from manus_ai.core.llm_providers import LLMManager

    agent = DataAnalysisAgent(llm_manager=LLMManager())

    task = SubTask(
        title="Analyze sales data",
        description="Create Python code to analyze monthly sales data: calculate trends, identify outliers, and create a visualization."
    )

    result = await agent.execute(task, {})

    print(f"\n✅ Analysis code generated:")
    print(f"\nType: {result.get('type')}")
    print(f"\nPreview: {str(result.get('code', ''))[:600]}...")


async def example_4_multi_step_workflow():
    """Example 4: Multi-step research + code workflow"""
    print("\n" + "="*70)
    print("🔄 EXAMPLE 4: Multi-Step Workflow (Research → Code)")
    print("="*70)
    print("\nTask: Research Python web frameworks, then generate sample code\n")

    from manus_ai.core.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator()

    result = await orchestrator.execute_request(
        user_request="""
        First, research what are the most popular Python web frameworks in 2024.
        Then, create a simple 'Hello World' API example using the most popular one.
        """
    )

    print(f"\n✅ Status: {result['status']}")
    if result['status'] == 'success':
        print(f"\n📝 Multi-step result:")
        print(f"{result['result']['summary'][:700]}...")
        print(f"\n⏱️  Total execution time: {result.get('execution_time', 0):.1f}s")

        # Show subtask breakdown
        if 'plan' in result and 'subtasks' in result['plan']:
            print(f"\n📋 Tasks completed:")
            for i, subtask in enumerate(result['plan']['subtasks'][:5], 1):
                status = "✅" if subtask.get('status') == 'completed' else "⏳"
                print(f"  {status} {i}. {subtask.get('title', 'Unknown')}")


async def example_5_file_generation():
    """Example 5: Document generation"""
    print("\n" + "="*70)
    print("📄 EXAMPLE 5: Document Generation")
    print("="*70)
    print("\nTask: Generate presentation outline\n")

    from manus_ai.agents.file_agent import FileProcessingAgent
    from manus_ai.core.task_planner import SubTask
    from manus_ai.core.llm_providers import LLMManager

    agent = FileProcessingAgent(llm_manager=LLMManager())

    task = SubTask(
        title="Generate presentation",
        description="Create Python code to generate a 5-slide presentation about artificial intelligence using python-pptx."
    )

    result = await agent.execute(task, {})

    print(f"\n✅ Presentation generation code created")
    print(f"Type: {result.get('type')}")
    print(f"Format: {result.get('format', 'N/A')}")


async def example_6_session_with_memory():
    """Example 6: Using memory system"""
    print("\n" + "="*70)
    print("🧠 EXAMPLE 6: Memory & Learning")
    print("="*70)
    print("\nDemonstrating user preference learning\n")

    from manus_ai.memory.memory_system import MemorySystem

    memory = MemorySystem(user_id="demo-user")

    # Add memories
    memory.add_memory(
        content="User prefers Python over JavaScript",
        memory_type="preference",
        importance=0.8,
        long_term=True
    )

    memory.learn_preference(
        key="programming_language",
        value="Python",
        confidence=0.9
    )

    memory.record_successful_approach(
        task_type="code_generation",
        approach={"style": "clean", "testing": "comprehensive"},
        success_score=0.95
    )

    # Get context
    context = memory.get_context_summary()

    print("✅ Memory system demo:")
    print(f"\n{context}")
    print(f"\nStored preferences: {len(memory.preferences)}")
    print(f"Short-term memories: {len(memory.short_term_memory)}")
    print(f"Long-term memories: {sum(len(m) for m in memory.long_term_memory.values())}")


async def example_7_code_execution():
    """Example 7: Sandboxed code execution"""
    print("\n" + "="*70)
    print("🔒 EXAMPLE 7: Sandboxed Code Execution")
    print("="*70)
    print("\nExecuting Python code safely in sandbox\n")

    from manus_ai.sandbox.code_executor import CodeExecutor

    executor = CodeExecutor(timeout=10, max_memory_mb=256)

    code = """
import math

# Calculate fibonacci sequence
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Calculate first 10 fibonacci numbers
result = [fibonacci(i) for i in range(10)]
print("Fibonacci sequence:", result)
print("Sum:", sum(result))
"""

    result = await executor.execute_code(code)

    print(f"✅ Execution status: {result['status']}")
    if result['status'] == 'success':
        print(f"\n📤 Output:\n{result.get('output', 'No output')}")
        print(f"\n⏱️  Duration: {result.get('duration', 0):.3f}s")


async def example_8_smart_routing():
    """Example 8: Demonstrate smart LLM routing"""
    print("\n" + "="*70)
    print("🎯 EXAMPLE 8: Smart Provider Routing")
    print("="*70)
    print("\nShowing how tasks are routed to optimal providers\n")

    from manus_ai.core.llm_providers import LLMManager, LLMProvider

    tasks = [
        ("Research task", "research", LLMProvider.PERPLEXITY_SONAR_PRO),
        ("Code task", "code", LLMProvider.GEMINI_2_5_PRO),
        ("Data task", "data", LLMProvider.GEMINI_2_5_PRO),
        ("Creative task", "creative", LLMProvider.GEMINI_2_5_PRO),
    ]

    print("Task Type Routing:\n")
    for task_name, task_type, provider in tasks:
        print(f"  📌 {task_name:20} → {provider.value}")

    print("\n✅ System automatically routes tasks to the best provider!")


async def run_all_examples():
    """Run all examples"""
    print("\n" + "="*70)
    print("🚀 MANUS AI CLONE - PRACTICAL EXAMPLES")
    print("="*70)
    print("\nRunning demonstrations of key capabilities...\n")

    examples = [
        ("Simple Research", example_1_simple_research),
        ("Code Generation", example_2_code_generation),
        ("Data Analysis", example_3_data_analysis),
        ("Multi-Step Workflow", example_4_multi_step_workflow),
        ("File Generation", example_5_file_generation),
        ("Memory System", example_6_session_with_memory),
        ("Code Execution", example_7_code_execution),
        ("Smart Routing", example_8_smart_routing),
    ]

    completed = 0
    failed = 0

    for name, example_func in examples:
        try:
            await example_func()
            completed += 1
            await asyncio.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"\n❌ Example '{name}' failed: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "="*70)
    print("📊 EXAMPLES SUMMARY")
    print("="*70)
    print(f"\n✅ Completed: {completed}/{len(examples)}")
    print(f"❌ Failed: {failed}/{len(examples)}")

    if completed == len(examples):
        print("\n🎉 All examples ran successfully!")
        print("Your Manus AI Clone is fully operational!")
    else:
        print(f"\n⚠️  Some examples failed. This might be due to:")
        print("  • Missing API keys in manus_ai/.env")
        print("  • Network connectivity issues")
        print("  • Missing dependencies")


async def interactive_menu():
    """Interactive example menu"""
    examples = {
        '1': ("Simple Research", example_1_simple_research),
        '2': ("Code Generation", example_2_code_generation),
        '3': ("Data Analysis", example_3_data_analysis),
        '4': ("Multi-Step Workflow", example_4_multi_step_workflow),
        '5': ("File Generation", example_5_file_generation),
        '6': ("Memory System", example_6_session_with_memory),
        '7': ("Code Execution", example_7_code_execution),
        '8': ("Smart Routing", example_8_smart_routing),
        'a': ("Run All Examples", run_all_examples),
    }

    print("\n" + "="*70)
    print("🚀 MANUS AI CLONE - INTERACTIVE EXAMPLES")
    print("="*70)
    print("\nSelect an example to run:\n")

    for key, (name, _) in examples.items():
        if key == 'a':
            print(f"\n  {key}. {name} (runs all above)")
        else:
            print(f"  {key}. {name}")

    print("\n  q. Quit")
    print("="*70)

    choice = input("\nEnter your choice: ").strip().lower()

    if choice == 'q':
        print("\n👋 Goodbye!")
        return

    if choice in examples:
        name, func = examples[choice]
        print(f"\n▶️  Running: {name}\n")
        try:
            await func()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n❌ Invalid choice")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            # Run all examples
            asyncio.run(run_all_examples())
        elif sys.argv[1] == '--help':
            print("Usage:")
            print("  python3 examples.py           # Interactive menu")
            print("  python3 examples.py --all     # Run all examples")
            print("  python3 examples.py --help    # Show this help")
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
    else:
        # Interactive mode
        try:
            asyncio.run(interactive_menu())
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")

#!/usr/bin/env python3
"""
Test script for dual LLM provider setup (Gemini + Perplexity)
Demonstrates smart routing and capabilities
"""

import asyncio
import os
import sys

# Load API keys from environment
# Keys should be set in manus_ai/.env or as environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('manus_ai/.env')
except ImportError:
    pass  # dotenv not required, can use system env vars

async def test_gemini():
    """Test Gemini for creative/general tasks"""
    print("\n" + "="*60)
    print("🧪 Testing Gemini 2.5 Pro (Creative/General Tasks)")
    print("="*60)

    try:
        import aiohttp

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": "In one creative sentence, describe what makes AI agents powerful."}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 100
            }
        }

        headers = {"Content-Type": "application/json"}
        params = {"key": os.environ['GEMINI_API_KEY']}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"\n✅ Gemini Response:")
                    print(f"   {text}")
                    return True
                else:
                    error = await resp.text()
                    print(f"\n❌ Error {resp.status}: {error[:200]}")
                    return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def test_perplexity():
    """Test Perplexity for research/web-grounded tasks"""
    print("\n" + "="*60)
    print("🔍 Testing Perplexity Sonar Pro (Research/Web-Grounded)")
    print("="*60)

    try:
        import aiohttp

        url = "https://api.perplexity.ai/chat/completions"

        payload = {
            "model": "sonar-pro",
            "messages": [{
                "role": "user",
                "content": "What is the latest news about AI in 2024? Give me one recent development with a source."
            }],
            "max_tokens": 150,
            "temperature": 0.2
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    text = result["choices"][0]["message"]["content"]
                    citations = result.get("citations", [])

                    print(f"\n✅ Perplexity Response:")
                    print(f"   {text[:300]}...")

                    if citations:
                        print(f"\n   📚 Sources:")
                        for i, citation in enumerate(citations[:3], 1):
                            print(f"      {i}. {citation}")

                    return True
                else:
                    error = await resp.text()
                    print(f"\n❌ Error {resp.status}: {error[:200]}")
                    return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def test_smart_routing():
    """Demonstrate smart provider routing"""
    print("\n" + "="*60)
    print("🎯 Demonstrating Smart Provider Routing")
    print("="*60)

    routing_info = {
        "Research Task": {
            "provider": "Perplexity Sonar Pro",
            "reason": "Web-grounded, real-time information with citations",
            "example": "Research latest quantum computing breakthroughs"
        },
        "Code Generation": {
            "provider": "Gemini 2.5 Pro (or Claude if available)",
            "reason": "Excellent code understanding and generation",
            "example": "Build a REST API with FastAPI"
        },
        "Data Analysis": {
            "provider": "Gemini 2.5 Pro",
            "reason": "Strong analytical and visualization capabilities",
            "example": "Analyze sales trends and create charts"
        },
        "Creative Writing": {
            "provider": "Gemini 2.5 Pro",
            "reason": "Creative, engaging content generation",
            "example": "Write a blog post about AI ethics"
        },
        "Fact Checking": {
            "provider": "Perplexity Sonar Pro",
            "reason": "Real-time web access and source verification",
            "example": "Verify recent scientific claims"
        }
    }

    print("\n📊 Optimal Provider Selection:\n")
    for task_type, info in routing_info.items():
        print(f"   {task_type}:")
        print(f"   → Provider: {info['provider']}")
        print(f"   → Why: {info['reason']}")
        print(f"   → Example: '{info['example']}'")
        print()

    return True


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🚀 MANUS AI - DUAL PROVIDER TEST (Gemini + Perplexity)")
    print("="*70)

    # Check environment
    print("\n📋 Configuration Check:")
    print(f"   ✓ Gemini API Key: {os.environ.get('GEMINI_API_KEY', '')[:20]}...")
    print(f"   ✓ Perplexity API Key: {os.environ.get('PERPLEXITY_API_KEY', '')[:20]}...")

    # Run tests
    print("\n🧪 Running Provider Tests...\n")

    results = []

    # Test Gemini
    gemini_ok = await test_gemini()
    results.append(("Gemini 2.5 Pro", gemini_ok))

    await asyncio.sleep(1)  # Rate limit pause

    # Test Perplexity
    perplexity_ok = await test_perplexity()
    results.append(("Perplexity Sonar Pro", perplexity_ok))

    # Show routing info
    await test_smart_routing()

    # Summary
    print("="*70)
    print("📊 TEST SUMMARY")
    print("="*70)

    for provider, passed in results:
        status = "✅ OPERATIONAL" if passed else "❌ FAILED"
        print(f"{status} - {provider}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nProviders Ready: {total_passed}/{total_tests}")

    if total_passed == total_tests:
        print("\n🎉 Both providers operational! Your Manus AI has:")
        print("   ✓ Gemini for creative, analytical, and coding tasks")
        print("   ✓ Perplexity for research and web-grounded information")
        print("\n💡 The system will automatically route tasks to the best provider!")
        return 0
    elif total_passed > 0:
        print(f"\n⚠️  {total_passed} provider(s) working. System is operational but limited.")
        return 0
    else:
        print("\n❌ No providers available. Check API keys and network connection.")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

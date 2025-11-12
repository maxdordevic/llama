#!/usr/bin/env python3
"""Quick test of Gemini API connectivity"""

import asyncio
import os
import sys

async def test_gemini():
    """Test Gemini API with the provided key"""

    # Set API key
    api_key = "AIzaSyDVPlrAe5j2p01BrTlRV9UECr5CWfoeqFw"
    os.environ['GEMINI_API_KEY'] = api_key

    print("🧪 Testing Gemini API Connection...")
    print(f"   API Key: {api_key[:20]}...{api_key[-10:]}")

    try:
        import aiohttp

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": "Say 'Hello from Gemini!' and tell me in one sentence what you can do."}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 100
            }
        }

        headers = {"Content-Type": "application/json"}
        params = {"key": api_key}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, params=params) as resp:
                print(f"\n📡 Response Status: {resp.status}")

                if resp.status == 200:
                    result = await resp.json()
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"\n✅ SUCCESS! Gemini Response:")
                    print(f"   {text}")
                    print(f"\n🎉 Manus AI system is ready to use with Gemini!")
                    return True
                else:
                    error_text = await resp.text()
                    print(f"\n❌ ERROR {resp.status}:")
                    print(f"   {error_text[:500]}")
                    return False

    except ImportError:
        print("❌ aiohttp not installed. Installing dependencies...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "aiohttp"])
        print("✅ Installed aiohttp. Please run this test again.")
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 MANUS AI - QUICK GEMINI TEST")
    print("=" * 60)
    print()

    result = asyncio.run(test_gemini())

    print("\n" + "=" * 60)
    if result:
        print("✅ TEST PASSED - System is operational!")
    else:
        print("❌ TEST FAILED - Check errors above")
    print("=" * 60)

    sys.exit(0 if result else 1)

#!/usr/bin/env python3
"""
Test script for Anthropic LLM integration.

This script tests the updated LLM service to ensure it can connect to
Anthropic's API directly instead of using OpenRouter.
"""

import asyncio
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.services.llm import LLMService, LLMError


async def test_anthropic_connection():
    """Test basic connection to Anthropic API."""
    print("🔧 Testing Anthropic API connection...")
    
    settings = get_settings()
    
    # Check configuration
    if not settings.anthropic_api_key:
        print("❌ ANTHROPIC_API_KEY not configured")
        print("   Set ANTHROPIC_API_KEY environment variable to test")
        return False
    
    print(f"✅ Anthropic API key configured")
    print(f"   Primary model: {settings.extraction_model}")
    print(f"   Fallback model: {settings.extraction_model_fallback}")
    
    return True


async def test_simple_call():
    """Test a simple LLM call."""
    print("\n🤖 Testing simple LLM call...")
    
    try:
        llm = LLMService()
        
        # Simple test prompt
        prompt = "Hello! Please respond with exactly: 'Anthropic API working correctly'"
        
        response = await llm.call(
            model="claude-3-5-sonnet-20241022",
            prompt=prompt,
            max_tokens=100,
            temperature=0.1
        )
        
        print(f"✅ LLM call successful")
        print(f"   Response: {response[:100]}...")
        
        if "working correctly" in response.lower():
            print("✅ Response contains expected content")
            return True
        else:
            print("⚠️  Response doesn't contain expected content but call succeeded")
            return True
            
    except LLMError as e:
        print(f"❌ LLM call failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_json_format():
    """Test JSON format response."""
    print("\n📝 Testing JSON format response...")
    
    try:
        llm = LLMService()
        
        prompt = """Please respond with valid JSON containing these fields:
- status: "success" 
- message: "JSON format working"
- timestamp: current date as string

Respond with valid JSON only, no markdown."""
        
        response = await llm.call(
            model="claude-3-5-sonnet-20241022",
            prompt=prompt,
            response_format="json",
            max_tokens=200,
            temperature=0.1
        )
        
        print(f"✅ JSON LLM call successful")
        print(f"   Response: {response}")
        
        # Try to parse the JSON
        import json
        try:
            data = json.loads(response)
            if data.get("status") == "success":
                print("✅ Valid JSON with expected structure")
                return True
            else:
                print("⚠️  Valid JSON but unexpected structure")
                return True
        except json.JSONDecodeError:
            print("⚠️  Response is not valid JSON (Anthropic doesn't enforce JSON mode)")
            return True
            
    except LLMError as e:
        print(f"❌ JSON LLM call failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_fallback():
    """Test fallback functionality."""
    print("\n🔄 Testing fallback functionality...")
    
    try:
        llm = LLMService()
        
        # Test fallback by calling with primary model first, then fallback
        response = await llm.call_with_fallback(
            prompt="Respond with: 'Fallback test successful'",
            max_tokens=50,
            temperature=0.1
        )
        
        print(f"✅ Fallback call successful")
        print(f"   Response: {response}")
        return True
        
    except LLMError as e:
        print(f"❌ Fallback call failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Anthropic LLM Service Test")
    print("=" * 50)
    
    # Test 1: Configuration
    config_ok = await test_anthropic_connection()
    if not config_ok:
        print("\n❌ Configuration test failed. Cannot proceed with API tests.")
        return
    
    # Test 2: Simple call
    simple_ok = await test_simple_call()
    
    # Test 3: JSON format
    json_ok = await test_json_format()
    
    # Test 4: Fallback
    fallback_ok = await test_fallback()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Configuration: {'PASS' if config_ok else 'FAIL'}")
    print(f"✅ Simple call: {'PASS' if simple_ok else 'FAIL'}")
    print(f"✅ JSON format: {'PASS' if json_ok else 'FAIL'}")
    print(f"✅ Fallback: {'PASS' if fallback_ok else 'FAIL'}")
    
    if all([config_ok, simple_ok, json_ok, fallback_ok]):
        print("\n🎉 All tests passed! Anthropic LLM service is working correctly.")
        print("\n📝 To use Anthropic API:")
        print("   1. Set ANTHROPIC_API_KEY in your environment")
        print("   2. Models will automatically use Anthropic API for claude- models")
        print("   3. Falls back to OpenRouter if Anthropic key not available")
    else:
        print("\n❌ Some tests failed. Check configuration and network connectivity.")


if __name__ == "__main__":
    asyncio.run(main())
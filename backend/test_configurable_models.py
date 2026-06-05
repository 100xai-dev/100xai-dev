#!/usr/bin/env python3
"""
Test script demonstrating configurable Anthropic model selection.

This script shows how to use different Anthropic models via environment variables
instead of hardcoded model names.
"""

import asyncio
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_settings
from app.services.llm import LLMService, LLMError


def test_configuration():
    """Test current model configuration."""
    print("🔧 Testing Model Configuration...")
    
    settings = get_settings()
    
    print(f"📋 Current Model Configuration:")
    print(f"   Primary (EXTRACTION_MODEL): {settings.extraction_model}")
    print(f"   Fallback (EXTRACTION_MODEL_FALLBACK): {settings.extraction_model_fallback}")
    print(f"   Blog (BLOG_MODEL): {settings.blog_model}")
    print()
    print(f"🔑 API Keys:")
    print(f"   Anthropic: {'✅ Configured' if settings.anthropic_api_key else '❌ Not set'}")
    print(f"   OpenRouter: {'✅ Configured' if settings.openrouter_api_key else '❌ Not set'}")
    print()


async def test_model_selection(model_name: str):
    """Test a specific model."""
    print(f"🤖 Testing model: {model_name}")
    
    try:
        llm = LLMService()
        
        # Determine which API would be used
        settings = get_settings()
        api_used = "Anthropic" if settings.anthropic_api_key and model_name.startswith("claude") else "OpenRouter"
        
        print(f"   → Will use {api_used} API")
        
        # Test if we have the required API key
        if api_used == "Anthropic" and not settings.anthropic_api_key:
            print("   ❌ Anthropic API key required but not configured")
            return False
        elif api_used == "OpenRouter" and not settings.openrouter_api_key:
            print("   ❌ OpenRouter API key required but not configured")
            return False
        
        response = await llm.call(
            model=model_name,
            prompt=f"Respond with: 'Model {model_name} working correctly'",
            max_tokens=50,
            temperature=0.1
        )
        
        print(f"   ✅ Success: {response[:60]}...")
        return True
        
    except LLMError as e:
        print(f"   ❌ Failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def show_examples():
    """Show examples of how to configure different models."""
    print("📝 EXAMPLES: How to use different Anthropic models")
    print("=" * 60)
    print()
    print("You can set any of these models via environment variables:")
    print()
    
    examples = [
        ("claude-3-5-sonnet-20241022", "Latest Sonnet model (default)"),
        ("claude-3-5-haiku-20241022", "Latest fast Haiku model"),
        ("claude-3-5-sonnet", "Sonnet without date suffix"),
        ("claude-3-haiku", "Haiku without date suffix"),
        ("claude-3-opus", "Most capable Claude 3 model"),
        ("claude-2", "Previous generation Claude"),
    ]
    
    print("🔧 EXTRACTION MODELS:")
    for model, desc in examples:
        print(f"   export EXTRACTION_MODEL={model}  # {desc}")
    
    print()
    print("🔧 FALLBACK MODELS:")
    for model, desc in examples:
        print(f"   export EXTRACTION_MODEL_FALLBACK={model}  # {desc}")
    
    print()
    print("🔧 BLOG MODELS:")
    for model, desc in examples:
        print(f"   export BLOG_MODEL={model}  # {desc}")
    
    print()
    print("💡 EXAMPLE CONFIGURATIONS:")
    print()
    print("   # Use latest models:")
    print("   export EXTRACTION_MODEL=claude-3-5-sonnet-20241022")
    print("   export EXTRACTION_MODEL_FALLBACK=claude-3-5-haiku-20241022")
    print("   export BLOG_MODEL=claude-3-5-sonnet-20241022")
    print()
    print("   # Use cost-optimized setup:")
    print("   export EXTRACTION_MODEL=claude-3-5-haiku-20241022")
    print("   export EXTRACTION_MODEL_FALLBACK=claude-3-haiku")
    print("   export BLOG_MODEL=claude-3-5-haiku-20241022")
    print()
    print("   # Use maximum capability:")
    print("   export EXTRACTION_MODEL=claude-3-opus")
    print("   export EXTRACTION_MODEL_FALLBACK=claude-3-5-sonnet-20241022")
    print("   export BLOG_MODEL=claude-3-opus")
    print()


async def main():
    """Run configuration tests."""
    print("🚀 Configurable Anthropic Models Test")
    print("=" * 50)
    print()
    
    # Test 1: Show current configuration
    test_configuration()
    
    # Test 2: Test current models
    settings = get_settings()
    models_to_test = [
        settings.extraction_model,
        settings.extraction_model_fallback,
        settings.blog_model
    ]
    
    print("🧪 TESTING CURRENT MODELS:")
    print("-" * 30)
    results = []
    for model in set(models_to_test):  # Remove duplicates
        result = await test_model_selection(model)
        results.append((model, result))
    
    print()
    print("📊 TEST RESULTS:")
    print("-" * 30)
    for model, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {model}: {status}")
    
    print()
    show_examples()
    
    if all(result for _, result in results):
        print("🎉 All configured models are working!")
    else:
        print("⚠️  Some models failed - check API key configuration")
        print("   Set ANTHROPIC_API_KEY to test Anthropic models directly")


if __name__ == "__main__":
    asyncio.run(main())
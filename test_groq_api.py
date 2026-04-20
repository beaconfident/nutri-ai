#!/usr/bin/env python3
"""
Test script to verify Groq API key and check available models
"""
import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GROQ_API_KEY")

print("=" * 60)
print("GROQ API KEY VERIFICATION TEST")
print("=" * 60)

# Check if API key exists
if not api_key:
    print("❌ ERROR: GROQ_API_KEY not found in .env file")
    print("Please add GROQ_API_KEY=your_key_here to .env file")
    exit(1)

if api_key == "your_groq_api_key_here":
    print("❌ ERROR: GROQ_API_KEY is still a placeholder")
    print("Please replace with your actual API key from https://console.groq.com/keys")
    exit(1)

print(f"✓ API Key found (length: {len(api_key)} characters)")
print(f"✓ API Key starts with: {api_key[:10]}...")
print()

# Initialize client
try:
    client = Groq(api_key=api_key)
    print("✓ Groq client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Groq client: {e}")
    exit(1)

print()
print("=" * 60)
print("AVAILABLE MODELS")
print("=" * 60)

# List available models
try:
    models = client.models.list()
    
    if not models.data:
        print("❌ No models found. API key might be invalid.")
        exit(1)
    
    print(f"Found {len(models.data)} available models:\n")
    
    for model in models.data:
        print(f"  • {model.id}")
    
    print()
    print("=" * 60)
    print("TESTING API CONNECTION")
    print("=" * 60)
    print()
    
    # Try with the first available model
    if models.data:
        test_model = models.data[0].id
        print(f"Testing with model: {test_model}")
        print()
        
        try:
            response = client.chat.completions.create(
                model=test_model,
                messages=[
                    {"role": "user", "content": "Say 'Hello, API is working!' in exactly those words."}
                ],
                max_tokens=100
            )
            
            print("✓ API Connection Test PASSED")
            print(f"✓ Model Response: {response.choices[0].message.content}")
            print()
            print("=" * 60)
            print("✅ ALL TESTS PASSED - YOUR API KEY IS WORKING!")
            print("=" * 60)
            print()
            print("Recommended model for your nutrition assistant:")
            print(f"  Use: {test_model}")
            
        except Exception as e:
            print(f"❌ API connection test failed: {e}")
            exit(1)

except Exception as e:
    print(f"❌ Failed to fetch models: {e}")
    print()
    print("This usually means:")
    print("  1. API key is invalid or expired")
    print("  2. Network connectivity issue")
    print("  3. Groq service is temporarily unavailable")
    print()
    print("Please:")
    print("  1. Get a fresh API key from https://console.groq.com/keys")
    print("  2. Update the .env file with the new key")
    print("  3. Run this test again")
    exit(1)

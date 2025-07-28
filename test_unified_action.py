#!/usr/bin/env python3
"""
Simple test script for the unified LLM action
"""

import os
from dotenv import load_dotenv

load_dotenv()

def test_environment():
    """Test if environment variables are set"""
    print("🔍 Testing Environment Setup...")
    
    api_key = os.getenv("TOGETHER_API_KEY")
    mongo_uri = os.getenv("MONGODB_URI")
    
    if api_key:
        print("✅ TOGETHER_API_KEY is set")
    else:
        print("❌ TOGETHER_API_KEY is not set")
    
    if mongo_uri:
        print("✅ MONGODB_URI is set")
    else:
        print("⚠️  MONGODB_URI is not set (will use mock data)")
    
    print()

def test_rasa_config():
    """Test if Rasa configuration is correct"""
    print("🔍 Testing Rasa Configuration...")
    
    # Check if domain.yml exists and has the right action
    try:
        with open("domain.yml", "r") as f:
            content = f.read()
            if "action_unified_llm" in content:
                print("✅ action_unified_llm found in domain.yml")
            else:
                print("❌ action_unified_llm not found in domain.yml")
    except FileNotFoundError:
        print("❌ domain.yml not found")
    
    # Check if stories.yml exists and has the right action
    try:
        with open("data/stories.yml", "r") as f:
            content = f.read()
            if "action_unified_llm" in content:
                print("✅ action_unified_llm found in stories.yml")
            else:
                print("❌ action_unified_llm not found in stories.yml")
    except FileNotFoundError:
        print("❌ data/stories.yml not found")
    
    print()

def test_action_file():
    """Test if the unified action file exists"""
    print("🔍 Testing Action File...")
    
    if os.path.exists("actions/unified_llm_action.py"):
        print("✅ unified_llm_action.py exists")
        
        # Check file size
        size = os.path.getsize("actions/unified_llm_action.py")
        print(f"📁 File size: {size} bytes")
        
        # Check if it's a reasonable size (not empty)
        if size > 1000:
            print("✅ File appears to have content")
        else:
            print("⚠️  File seems small, might be incomplete")
    else:
        print("❌ unified_llm_action.py not found")
    
    print()

def main():
    """Run all tests"""
    print("🧪 Testing HomeLead Project Setup")
    print("=" * 50)
    
    test_environment()
    test_rasa_config()
    test_action_file()
    
    print("🎯 Next Steps:")
    print("1. Set your TOGETHER_API_KEY environment variable")
    print("2. Set your MONGODB_URI (optional)")
    print("3. Run: rasa train")
    print("4. Run: rasa run actions")
    print("5. In another terminal: rasa shell")
    print("6. Test with: 'Show me brokers in Mumbai'")

if __name__ == "__main__":
    main() 
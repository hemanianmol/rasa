import os
import requests
import json

# Mock MongoDB data (for demo)
brokers = [
    {"name": "Horizon Group", "city": "Mumbai", "phone": "+91 9213434545"},
    {"name": "Prime Investments", "city": "Delhi", "phone": "+91 9876543210"},
    {"name": "Legacy Partners", "city": "Mumbai", "phone": "+91 9123456789"},
]

def call_llama3_together(prompt, api_key):
    url = "https://api.together.xyz/v1/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/Llama-3-8b-chat-hf",
        "prompt": prompt,
        "max_tokens": 200,
        "temperature": 0.0,
        "top_p": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["text"].strip()

if __name__ == "__main__":
    api_key = os.getenv("TOGETHER_API_KEY")
    user_message = "Show me total number of brokers in Mumbai"

    # 1. LLM generates MongoDB query
    prompt_query = f"""
Given the user question and the following MongoDB collection schema:
Collection: brokers(name, city, phone)
Write a MongoDB filter (as a Python dict) to answer the question.
User question: {user_message}
Filter:
"""
    llm_query = call_llama3_together(prompt_query, api_key)
    print("[LLM] Generated MongoDB filter:", llm_query)
    try:
        mongo_filter = json.loads(llm_query)
        # Validate fields
        allowed_fields = {"city", "name"}
        if not isinstance(mongo_filter, dict) or not set(mongo_filter.keys()).issubset(allowed_fields):
            raise ValueError("Unsafe query fields")
    except Exception as e:
        print("[ERROR] Could not parse or validate LLM output:", e)
        mongo_filter = {}

    # 2. Execute query (mocked)
    results = [b for b in brokers if all(str(b.get(k, "")).lower() == str(v).lower() for k, v in mongo_filter.items())]
    print("[MongoDB] Query results:", results)

    # 3. LLM summarizes result
    prompt_summarize = f"""
Given the following data and the user's question, summarize the answer in natural language.
Data: {results}
User question: {user_message}
"""
    summary = call_llama3_together(prompt_summarize, api_key)
    print("[LLM] Final answer:", summary) 
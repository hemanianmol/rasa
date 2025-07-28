import requests
import json

def extract_intent_entities_llm(user_message, api_key):
    prompt = (
        "Extract the intent and entities from the following user message. "
        "Return as JSON: {\"intent\": \"...\", \"entities\": [{\"entity\": \"...\", \"value\": \"...\"}]}\n"
        f"Message: \"{user_message}\""
    )
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
    text = response.json()["choices"][0]["text"].strip()
    try:
        result = json.loads(text)
    except Exception as e:
        print("[DEBUG] LLM NLU parse error:", e)
        result = {"intent": "search_database", "entities": []}
    return result

# Example usage:
if __name__ == "__main__":
    api_key = "YOUR_TOGETHER_API_KEY"
    user_message = "Show me the average minBudget for commercial properties in BLOCK B"
    nlu_result = extract_intent_entities_llm(user_message, api_key)
    print(nlu_result) 
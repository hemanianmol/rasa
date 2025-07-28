# actions/action_llama_query.py
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import os, json, requests

class ActionQueryLlamaMongo(Action):
    def name(self):
        return "action_llama_query"

    def call_llama3_together(self, prompt, api_key):
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
        r = requests.post(url, headers=headers, json=data)
        r.raise_for_status()
        return r.json()["choices"][0]["text"].strip()

    def run(self, dispatcher, tracker, domain):
        api_key = os.getenv("TOGETHER_API_KEY")
        user_message = tracker.latest_message.get("text")

        # Step 1: Ask LLaMA to build Mongo query
        prompt_query = f"""
Given the user question and the following MongoDB schema:
Collection: brokers(name, city, phone)
Write a MongoDB filter (as a Python dict) to answer the question.
User question: {user_message}
Filter:
"""
        llm_query = self.call_llama3_together(prompt_query, api_key)

        # Step 2: Apply query to fake/mock data
        brokers = [
            {"name": "Horizon Group", "city": "Mumbai", "phone": "+91 9213434545"},
            {"name": "Prime Investments", "city": "Delhi", "phone": "+91 9876543210"},
            {"name": "Legacy Partners", "city": "Mumbai", "phone": "+91 9123456789"},
        ]
        try:
            mongo_filter = json.loads(llm_query)
            allowed_fields = {"city", "name"}
            if not isinstance(mongo_filter, dict) or not set(mongo_filter).issubset(allowed_fields):
                raise ValueError("Unsafe query fields")
        except:
            mongo_filter = {}

        results = [b for b in brokers if all(str(b.get(k, "")).lower() == str(v).lower() for k, v in mongo_filter.items())]

        # Step 3: Ask LLaMA to summarize result
        prompt_summary = f"""
Given the data and user's question, summarize answer in natural language.
User: {user_message}
Data: {results}
"""
        summary = self.call_llama3_together(prompt_summary, api_key)

        # Final response
        dispatcher.utter_message(text=summary)
        return []

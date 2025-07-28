from typing import Any, Dict, List, Text
from rasa.engine.graph import GraphComponent, ExecutionContext
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.constants import INTENT, ENTITIES
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
import requests
import json
import os

@DefaultV1Recipe.register("LLMIntentEntityGraphComponent", is_trainable=False)
class LLMIntentEntityGraphComponent(GraphComponent):
    @classmethod
    def create(
        cls,
        config: Dict[Text, Any],
        model_storage: ModelStorage,
        resource: Resource,
        execution_context: ExecutionContext,
    ) -> "LLMIntentEntityGraphComponent":
        return cls(config)

    def __init__(self, config: Dict[Text, Any]) -> None:
        self.api_key = os.getenv("TOGETHER_API_KEY") or config.get("api_key", "TOGETHER_API_KEY")

    def process(self, messages: List[Message]) -> List[Message]:
        print("[LLM NLU DEBUG] TOGETHER_API_KEY loaded:", (self.api_key[:4] + "..." if self.api_key else None))
        for message in messages:
            user_message = message.get("text")
            print("[LLM NLU DEBUG] User message:", user_message)
            prompt = (M
                "Extract the intent and entities from the following user message. "
                "Return as JSON: {\"intent\": \"...\", \"entities\": [{\"entity\": \"...\", \"value\": \"...\"}]}\n"
                f"Message: \"{user_message}\""
            )
            url = "https://api.together.xyz/v1/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "meta-llama/Llama-3-8b-chat-hf",
                "prompt": prompt,
                "max_tokens": 200,
                "temperature": 0.0,
                "top_p": 0.7
            }
            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                text = response.json()["choices"][0]["text"].strip()
                result = json.loads(text)
                message.set(INTENT, {"name": result.get("intent", "search_database"), "confidence": 1.0})
                message.set(ENTITIES, result.get("entities", []))
            except Exception as e:
                print("[LLM NLU Graph Component ERROR]", e)
                message.set(INTENT, {"name": "search_database", "confidence": 0.5})
                message.set(ENTITIES, [])
        return messages 
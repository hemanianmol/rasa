from typing import Any, Dict, List, Text
from rasa.engine.graph import GraphComponent, ExecutionContext
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.constants import INTENT
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
        for message in messages:
            user_message = message.get("text")
            
            # Simple intent classification without entities
            if any(word in user_message.lower() for word in ["hi", "hello", "hey", "good morning", "good evening"]):
                intent = "greet"
            elif any(word in user_message.lower() for word in ["bye", "goodbye", "see you", "talk to you"]):
                intent = "goodbye"
            else:
                intent = "search_database"
            
            message.set(INTENT, {"name": intent, "confidence": 1.0})
            
        return messages 
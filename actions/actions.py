# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

import os
import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv()
import difflib

def call_llama3_together(prompt, api_key):
    url = "https://api.together.xyz/v1/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/Llama-3-8b-chat-hf",
        "prompt": prompt,
        "max_tokens": 100,
        "temperature": 0.7,
        "top_p": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["text"].strip()

class ActionSearchDatabase(Action):
    def name(self):
        return "action_search_database"

    def run(self, dispatcher, tracker, domain):
        user_message = tracker.latest_message.get("text")
        intent = tracker.latest_message.get("intent", {}).get("name")
        print("[DEBUG] Extracted intent:", intent)
        greeting_phrases = ["hi", "hello", "hey", "good morning", "good evening"]
        if any(phrase in user_message.lower() for phrase in greeting_phrases):
            dispatcher.utter_message(response="utter_greet")
            return []
        if intent == "greet":
            dispatcher.utter_message(response="utter_greet")
            return []
        if intent == "goodbye":
            dispatcher.utter_message(response="utter_goodbye")
            return []
        print("[DEBUG] User message:", user_message)
        mongo_uri = os.getenv("MONGODB_URI")
        mongo_db = os.getenv("MONGODB_DB", "homelead")
        print("[DEBUG] MongoDB URI:", mongo_uri)
        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        api_key = os.getenv("TOGETHER_API_KEY")
        user_message_lower = user_message.lower()
        # Print extracted entities
        entities = tracker.latest_message.get("entities", [])
        print("[DEBUG] Extracted entities:", entities)

        # Helper to extract entity value by type
        def get_entity_value(entity_type):
            for ent in entities:
                if ent.get("entity") == entity_type:
                    return ent.get("value")
            return None

        # Helper to extract likely name from message
        import re
        def extract_likely_name(msg, keywords):
            for kw in keywords:
                pattern = rf"(.+?)\s*{kw}"
                match = re.search(pattern, msg, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            return None

        # List queries with optional city/category filter
        if "list" in user_message_lower or "all" in user_message_lower:
            if "broker" in user_message_lower:
                query = {}
                for field in ["city", "company"]:
                    if field in user_message_lower:
                        query[field] = {"$regex": user_message, "$options": "i"}
                brokers = list(db["brokers"].find(query))
                print("[DEBUG] Brokers found:", brokers)
                if brokers:
                    def broker_display_name(b):
                        return b.get("name") or str(b.get("_id"))
                    names = [broker_display_name(b) for b in brokers]
                    dispatcher.utter_message(text="Brokers: " + ", ".join(names))
                    return []
            if "property" in user_message_lower:
                query = {}
                for field in ["city", "category", "projectStatus"]:
                    if field in user_message_lower:
                        query[field] = {"$regex": user_message, "$options": "i"}
                properties = list(db["properties"].find(query))
                print("[DEBUG] Properties found:", properties)
                if properties:
                    def property_display_name(p):
                        if p.get("name"):
                            return p["name"]
                        return f"{p.get('propertyType', '')} Block {p.get('blockName', '')} Floor {p.get('floorName', '')} Shop {p.get('shopNo', '')}".strip()
                    names = [property_display_name(p) for p in properties]
                    dispatcher.utter_message(text="Properties: " + ", ".join(names))
                    return []
            if "project" in user_message_lower:
                query = {}
                for field in ["city", "category", "projectStatus"]:
                    if field in user_message_lower:
                        query[field] = {"$regex": user_message, "$options": "i"}
                projects = list(db["projects"].find(query))
                print("[DEBUG] Projects found:", projects)
                if projects:
                    def project_display_name(p):
                        return p.get("name") or str(p.get("_id"))
                    names = [project_display_name(p) for p in projects]
                    dispatcher.utter_message(text="Projects: " + ", ".join(names))
                    return []

        # Load all data from MongoDB collections
        all_brokers = list(db["brokers"].find())
        all_properties = list(db["properties"].find())
        all_projects = list(db["projects"].find())

        # --- Robust fuzzy matching for specific queries ---
        # Properties
        prop_fields = ["propertyType", "blockName", "floorName", "series", "shopNo", "furnishedStatus", "minBudget", "maxBudget", "facing", "vastuCompliant", "carpetArea", "builtUpArea", "superBuiltUpArea", "carpetAreaType", "builtUpAreaType", "superBuiltUpAreaType", "noOfBalconies", "noOfBathRooms", "noOfBedRooms", "noOfKitchens", "noOfDrawingRooms", "noOfParkingLots"]
        prop_query_value = get_entity_value("property_name") or extract_likely_name(user_message, ["property"]) or user_message
        print("[DEBUG] Property search value:", prop_query_value)
        property_blobs = []
        property_docs = []
        for doc in all_properties:
            blob = " ".join([str(v).lower() for k, v in doc.items() if k in prop_fields and isinstance(v, (str, int, float))])
            property_blobs.append(blob)
            property_docs.append(doc)
        prop = None
        matches = difflib.get_close_matches(prop_query_value.lower(), property_blobs, n=1, cutoff=0.5)
        if matches:
            idx = property_blobs.index(matches[0])
            prop = property_docs[idx]
        print("[DEBUG] Fuzzy-matched property:", prop)

        # Projects
        proj_fields = ["name", "slug", "category", "projectStatus", "minBudget", "maxBudget", "startDate", "completionDate", "countryCode", "phone", "email", "address", "zipCode", "reraRegistrationNumber", "projectRegistrationNumber", "projectType", "projectUnitSubType", "layoutPlanImages"]
        proj_query_value = get_entity_value("project_name") or extract_likely_name(user_message, ["project"]) or user_message
        print("[DEBUG] Project search value:", proj_query_value)
        project_blobs = []
        project_docs = []
        for doc in all_projects:
            blob = " ".join([str(v).lower() for k, v in doc.items() if k in proj_fields and isinstance(v, (str, int, float))])
            project_blobs.append(blob)
            project_docs.append(doc)
        proj = None
        matches = difflib.get_close_matches(proj_query_value.lower(), project_blobs, n=1, cutoff=0.5)
        if matches:
            idx = project_blobs.index(matches[0])
            proj = project_docs[idx]
        print("[DEBUG] Fuzzy-matched project:", proj)

        # Brokers
        brok_fields = ["name", "company", "countryCode", "phone", "city", "state", "address", "zipCode", "commissionPercent", "bankDetails", "realEstateLicenseDetails", "yearStartedInRealEstate", "status"]
        brok_query_value = get_entity_value("broker_name") or extract_likely_name(user_message, ["broker"]) or user_message
        print("[DEBUG] Broker search value:", brok_query_value)
        broker_blobs = []
        broker_docs = []
        for doc in all_brokers:
            blob = " ".join([str(v).lower() for k, v in doc.items() if k in brok_fields and isinstance(v, (str, int, float))])
            broker_blobs.append(blob)
            broker_docs.append(doc)
        brok = None
        matches = difflib.get_close_matches(brok_query_value.lower(), broker_blobs, n=1, cutoff=0.5)
        if matches:
            idx = broker_blobs.index(matches[0])
            brok = broker_docs[idx]
        print("[DEBUG] Fuzzy-matched broker:", brok)

        # --- Specific queries: use extracted entity, then likely name, then fallback ---
        # Try properties (search across multiple fields)
        prop_fields = ["name", "address", "category", "city", "blockName", "series", "projectStatus"]
        prop_query_value = get_entity_value("property_name") or extract_likely_name(user_message, ["property"]) or user_message
        print("[DEBUG] Property search value:", prop_query_value)
        def build_or_query(fields, value):
            return {"$or": [{field: {"$regex": value, "$options": "i"}} for field in fields]}
        prop = None
        # Search through all_properties for the best match
        for doc in all_properties:
            if any(prop_query_value.lower() in str(v).lower() for k, v in doc.items() if k in prop_fields and isinstance(v, str)):
                prop = doc
                break
        print("[DEBUG] Property found:", prop)
        if prop:
            prompt = (
                f"You are a property assistant. Only answer using the following property data. "
                f"If the answer is not present, say: 'Sorry, I can only answer questions about properties in my database.'\n"
                f"Property data: {prop}\n"
                f"User question: {user_message}\n"
            )
            if api_key:
                try:
                    llama_response = call_llama3_together(prompt, api_key)
                    dispatcher.utter_message(text=llama_response)
                except Exception as e:
                    print("[DEBUG] Llama 3 API error:", e)
                    dispatcher.utter_message(text="Sorry, there was an error generating the answer.")
            else:
                dispatcher.utter_message(text="Sorry, the Llama 3 API key is not set.")
            return []
        print("[DEBUG] No specific property match found.")

        # Try projects (search across multiple fields)
        proj_fields = ["name", "address", "category", "city", "projectStatus"]
        proj_query_value = get_entity_value("project_name") or extract_likely_name(user_message, ["project"]) or user_message
        print("[DEBUG] Project search value:", proj_query_value)
        proj = None
        for doc in all_projects:
            if any(proj_query_value.lower() in str(v).lower() for k, v in doc.items() if k in proj_fields and isinstance(v, str)):
                proj = doc
                break
        print("[DEBUG] Project found:", proj)
        if proj:
            prompt = (
                f"You are a property assistant. Only answer using the following project data. "
                f"If the answer is not present, say: 'Sorry, I can only answer questions about projects in my database.'\n"
                f"Project data: {proj}\n"
                f"User question: {user_message}\n"
            )
            if api_key:
                try:
                    llama_response = call_llama3_together(prompt, api_key)
                    dispatcher.utter_message(text=llama_response)
                except Exception as e:
                    print("[DEBUG] Llama 3 API error:", e)
                    dispatcher.utter_message(text="Sorry, there was an error generating the answer.")
            else:
                dispatcher.utter_message(text="Sorry, the Llama 3 API key is not set.")
            return []
        print("[DEBUG] No specific project match found.")

        # Try brokers (search across multiple fields)
        brok_fields = ["name", "address", "city", "company"]
        brok_query_value = get_entity_value("broker_name") or extract_likely_name(user_message, ["broker"]) or user_message
        print("[DEBUG] Broker search value:", brok_query_value)
        brok = None
        for doc in all_brokers:
            if any(brok_query_value.lower() in str(v).lower() for k, v in doc.items() if k in brok_fields and isinstance(v, str)):
                brok = doc
                break
        print("[DEBUG] Broker found:", brok)
        if brok:
            prompt = (
                f"You are a property assistant. Only answer using the following broker data. "
                f"If the answer is not present, say: 'Sorry, I can only answer questions about brokers in my database.'\n"
                f"Broker data: {brok}\n"
                f"User question: {user_message}\n"
            )
            if api_key:
                try:
                    llama_response = call_llama3_together(prompt, api_key)
                    dispatcher.utter_message(text=llama_response)
                except Exception as e:
                    print("[DEBUG] Llama 3 API error:", e)
                    dispatcher.utter_message(text="Sorry, there was an error generating the answer.")
            else:
                dispatcher.utter_message(text="Sorry, the Llama 3 API key is not set.")
            return []
        print("[DEBUG] No specific broker match found.")

        dispatcher.utter_message(response="utter_fallback")
        print("[DEBUG] No match found, fallback triggered.")
        return []
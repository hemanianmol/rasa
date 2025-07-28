# Unified LLM Action - Combines LLM Query Generation with Real MongoDB Integration
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import os, json, requests, re
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class UnifiedLLMAction(Action):
    def name(self):
        return "action_unified_llm"

    def call_llama3_together(self, prompt, api_key):
        """Call Llama 3 via Together AI API"""
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
        try:
            r = requests.post(url, headers=headers, json=data)
            r.raise_for_status()
            return r.json()["choices"][0]["text"].strip()
        except Exception as e:
            print(f"[ERROR] LLM API call failed: {e}")
            return None

    def extract_json_from_response(self, response):
        """Extract JSON from LLM response and simplify complex queries"""
        # Clean the response first
        response = response.strip()
        
        # Remove comments and explanations (everything after #)
        if '#' in response:
            response = response.split('#')[0].strip()
        
        # Remove any trailing text after the JSON
        if '}' in response:
            last_brace = response.rfind('}')
            response = response[:last_brace + 1]
        
        # Convert single quotes to double quotes for valid JSON
        response = response.replace("'", '"')
        
        # Try to find JSON pattern in the response
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, response)
        
        if matches:
            # Try each match
            for match in matches:
                try:
                    # Clean up the match
                    match = match.strip()
                    if match.startswith('```'):
                        match = match[3:]
                    if match.endswith('```'):
                        match = match[:-3]
                    if match.startswith('python'):
                        match = match[6:]
                    
                    result = json.loads(match)
                    
                    # Simplify complex queries
                    if isinstance(result, dict):
                        # If it has a 'query' key, extract and simplify it
                        if 'query' in result:
                            query = result['query']
                            return self.simplify_query(query)
                        else:
                            return self.simplify_query(result)
                    
                    return result
                except:
                    continue
        
        # If no JSON found, try to parse the entire response
        try:
            # Clean up the response
            clean_response = response
            if clean_response.startswith('```'):
                clean_response = clean_response.split('\n', 1)[1] if '\n' in clean_response else clean_response[3:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            result = json.loads(clean_response)
            if isinstance(result, dict):
                return self.simplify_query(result)
            return result
        except:
            # Last resort: try to extract simple key-value pairs
            try:
                # Look for simple patterns like {"city": "Mumbai"}
                simple_pattern = r'\{[^}]*"[^"]*"[^}]*\}'
                simple_matches = re.findall(simple_pattern, response)
                if simple_matches:
                    result = json.loads(simple_matches[0])
                    if isinstance(result, dict):
                        return self.simplify_query(result)
                    return result
            except:
                pass
        
        return None

    def simplify_query(self, query):
        """Simplify complex MongoDB queries by removing $exists and complex operators"""
        if not isinstance(query, dict):
            return query
        
        simplified = {}
        
        # Handle nested structures
        if '$and' in query:
            # Extract simple conditions from $and
            for condition in query['$and']:
                if isinstance(condition, dict):
                    for key, value in condition.items():
                        if key not in ['$exists', '$or'] and not isinstance(value, dict) or '$exists' not in value:
                            simplified[key] = value
        elif '$or' in query:
            # Extract simple conditions from $or
            for condition in query['$or']:
                if isinstance(condition, dict):
                    for key, value in condition.items():
                        if key not in ['$exists'] and not isinstance(value, dict) or '$exists' not in value:
                            simplified[key] = value
        else:
            # Direct conditions
            for key, value in query.items():
                if key not in ['$exists', '$and', '$or']:
                    if isinstance(value, dict) and '$exists' not in value:
                        simplified[key] = value
                    elif not isinstance(value, dict):
                        simplified[key] = value
        
        return simplified if simplified else {}

    def extract_query_from_text(self, user_message):
        """Intelligent fallback method that understands ANY query context"""
        user_message_lower = user_message.lower()
        query = {}
        
        # Handle total/count queries first
        if any(word in user_message_lower for word in ["total", "count", "all", "list all"]):
            return {}
        
        # Handle 'all <collection>' queries
        if re.match(r'all\s+(properties|leads|brokers|projects|lands)', user_message_lower):
            return {}
        
        # Handle 'lead no X' or 'show lead X' queries
        lead_no_match = re.search(r'(lead no|show lead)\s*(\d+)', user_message_lower)
        if lead_no_match:
            lead_no = int(lead_no_match.group(2))
            # Try both 'leadNo' and 'id' fields for flexibility
            return {"$or": [{"leadNo": lead_no}, {"id": lead_no}]}
        
        # Handle simple 'lead X' queries (without 'no' or 'show')
        simple_lead_match = re.search(r'lead\s+(\d+)', user_message_lower)
        if simple_lead_match:
            lead_no = int(simple_lead_match.group(1))
            return {"$or": [{"leadNo": lead_no}, {"id": lead_no}]}
        
        # Generalize for any collection: 'property no X', 'broker no X', etc.
        collection_types = ['lead', 'property', 'broker', 'project', 'land']
        for ctype in collection_types:
            pattern = rf'({ctype} no|show {ctype})\s*(\d+)'
            match = re.search(pattern, user_message_lower)
            if match:
                num = int(match.group(2))
                # Try both '<collection>No' and 'id' fields
                field_name = f"{ctype}No"
                return {"$or": [{field_name: num}, {"id": num}]}
            
            # Handle simple 'property X', 'broker X', etc. queries
            simple_pattern = rf'{ctype}\s+(\d+)'
            simple_match = re.search(simple_pattern, user_message_lower)
            if simple_match:
                num = int(simple_match.group(1))
                field_name = f"{ctype}No"
                return {"$or": [{field_name: num}, {"id": num}]}
        
        # Intelligent context-aware extraction
        import re
        
        # 1. Location extraction (any city/area)
        location_pattern = r'\b(mumbai|delhi|bangalore|pune|chennai|hyderabad|kolkata|ahmedabad|jaipur|noida|gurgaon|faridabad|ghaziabad)\b'
        location_match = re.search(location_pattern, user_message_lower)
        if location_match:
            query["address"] = {"$regex": location_match.group(1).title(), "$options": "i"}
        
        # 2. Property type extraction
        if "commercial" in user_message_lower:
            query["propertyType"] = "Commercial"
        elif "residential" in user_message_lower:
            query["propertyType"] = "Residential"
        
        # 3. Budget extraction (improved)
        budget_patterns = [
            r'(\d+)\s*(lakh|lakhs)',
            r'(\d+)\s*(crore|crores)',
            r'(\d+)\s*(k|thousand)',
            r'(\d+)\s*(million)',
            r'under\s*(\d+)',
            r'less\s*than\s*(\d+)',
            r'upto\s*(\d+)',
            r'budget\s*(\d+)',  # New pattern for "budget 10 lakh"
            r'range\s*(\d+)\s*-\s*(\d+)',  # Budget range pattern
        ]
        
        # Handle "less budget" queries
        if "less budget" in user_message_lower or "lower budget" in user_message_lower:
            query["maxBudget"] = {"$lte": 1000000}  # Properties under 10 lakhs
        elif "budget range" in user_message_lower:
            # Extract range from "budget range 120000 - 1500000"
            range_match = re.search(r'range\s*(\d+)\s*-\s*(\d+)', user_message_lower)
            if range_match:
                min_budget = int(range_match.group(1))
                max_budget = int(range_match.group(2))
                query["minBudget"] = {"$gte": min_budget}
                query["maxBudget"] = {"$lte": max_budget}
        
        for pattern in budget_patterns:
            budget_match = re.search(pattern, user_message_lower)
            if budget_match:
                amount = int(budget_match.group(1))
                if "lakh" in pattern:
                    max_budget = amount * 100000
                elif "crore" in pattern:
                    max_budget = amount * 10000000
                elif "k" in pattern or "thousand" in pattern:
                    max_budget = amount * 1000
                elif "million" in pattern:
                    max_budget = amount * 1000000
                else:
                    max_budget = amount
                
                query["maxBudget"] = {"$lte": max_budget}
                break
        
        # 4. Project category extraction
        if "residential" in user_message_lower and "project" in user_message_lower:
            query["category"] = "Residential"
        elif "commercial" in user_message_lower and "project" in user_message_lower:
            query["category"] = "Commercial"
        
        # 5. Status extraction (multiple status fields)
        status_keywords = {
            "active": "Active",
            "available": "Available", 
            "ready": "Ready",
            "completed": "Completed",
            "finished": "Finished",
            "ongoing": "Ongoing",
            "under construction": "Under Construction",
            "converted": "Converted"
        }
        
        for keyword, status_value in status_keywords.items():
            if keyword in user_message_lower:
                # Try different status fields based on context
                if "project" in user_message_lower:
                    query["projectStatus"] = {"$regex": status_value, "$options": "i"}
                elif "property" in user_message_lower:
                    query["propertyStatus"] = status_value
                elif "lead" in user_message_lower:
                    query["leadStatus"] = status_value
                else:
                    query["status"] = status_value
                break
        
        # 5. Budget extraction (any format)
        budget_patterns = [
            r'(\d+)\s*(lakh|lakhs)',
            r'(\d+)\s*(crore|crores)',
            r'(\d+)\s*(k|thousand)',
            r'(\d+)\s*(million)',
            r'under\s*(\d+)',
            r'less\s*than\s*(\d+)',
            r'upto\s*(\d+)'
        ]
        
        for pattern in budget_patterns:
            budget_match = re.search(pattern, user_message_lower)
            if budget_match:
                amount = int(budget_match.group(1))
                if "lakh" in pattern:
                    max_budget = amount * 100000
                elif "crore" in pattern:
                    max_budget = amount * 10000000
                elif "k" in pattern or "thousand" in pattern:
                    max_budget = amount * 1000
                elif "million" in pattern:
                    max_budget = amount * 1000000
                else:
                    max_budget = amount
                
                query["maxBudget"] = {"$lte": max_budget}
                break
        
        # 6. Commission extraction
        commission_patterns = [
            r'(\d+)%\s*commission',
            r'commission\s*(\d+)%',
            r'(\d+)\s*percent\s*commission'
        ]
        
        for pattern in commission_patterns:
            commission_match = re.search(pattern, user_message_lower)
            if commission_match:
                commission = int(commission_match.group(1))
                query["commissionPercent"] = commission
                break
        
        # 7. Phone number extraction (any format)
        phone_patterns = [
            r'\b\d{10}\b',
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\b\d{5}[-.\s]?\d{5}\b'
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, user_message_lower)
            if phone_match:
                phone = re.sub(r'[-.\s]', '', phone_match.group(0))
                query["phone"] = phone
                break
        
        # 8. Name extraction (intelligent)
        if not query:
            # Extract potential names/companies
            words = user_message.split()
            if len(words) <= 4:  # Likely a name search
                # Remove common words
                common_words = {"show", "me", "find", "get", "list", "all", "the", "a", "an", "in", "with", "of", "for", "to", "and", "or", "but"}
                name_words = [word for word in words if word.lower() not in common_words]
                if name_words:
                    name_query = " ".join(name_words)
                    query["name"] = {"$regex": name_query, "$options": "i"}
        
        # 9. Special case: Horizon Group (common in your data)
        if "horizon" in user_message_lower:
            query["name"] = {"$regex": "Horizon", "$options": "i"}
        
        return query

    def determine_collection(self, user_message):
        """Determine which collection to query based on user message"""
        user_message_lower = user_message.lower()
        
        # Keywords for each collection with weights
        collection_keywords = {
            "properties": {
                "primary": ["property", "properties", "flat", "apartment", "house", "shop", "unit"],
                "secondary": ["commercial", "residential", "block", "floor", "bedroom", "bathroom", "budget", "price"],
                "weight": 1.0
            },
            "projects": {
                "primary": ["project", "projects", "development", "society", "complex", "tower", "phase"],
                "secondary": ["ready", "completed", "ongoing", "construction"],
                "weight": 1.0
            },
            "brokers": {
                "primary": ["broker", "brokers", "agent", "agents", "real estate", "commission"],
                "secondary": ["horizon", "silverstone", "phone", "contact"],
                "weight": 1.0
            },
            "leads": {
                "primary": ["lead", "leads", "customer", "buyer", "inquiry", "prospect"],
                "secondary": ["converted", "source", "timeline"],
                "weight": 1.0
            },
            "lands": {
                "primary": ["land", "plot", "acre", "gaj", "sq ft", "square feet"],
                "secondary": ["vacant", "occupied", "agricultural"],
                "weight": 1.0
            }
        }
        
        # Calculate scores with weights
        scores = {}
        for collection, config in collection_keywords.items():
            primary_matches = sum(1 for kw in config["primary"] if kw in user_message_lower)
            secondary_matches = sum(1 for kw in config["secondary"] if kw in user_message_lower)
            
            # Primary keywords have higher weight
            score = (primary_matches * 2 + secondary_matches) * config["weight"]
            scores[collection] = score
        
        # Find the best collection
        if any(scores.values()):
            best_collection = max(scores.items(), key=lambda x: x[1])
            return best_collection[0]
        else:
            # Advanced context-aware fallback
            # Check for specific collection keywords in any context
            if "lead" in user_message_lower:
                return "leads"
            elif "property" in user_message_lower or "flat" in user_message_lower or "apartment" in user_message_lower:
                return "properties"
            elif "project" in user_message_lower or "development" in user_message_lower:
                return "projects"
            elif "land" in user_message_lower or "plot" in user_message_lower:
                return "lands"
            elif "broker" in user_message_lower or "agent" in user_message_lower:
                return "brokers"
            
            # Check for common query patterns
            if any(word in user_message_lower for word in ["total", "all", "list", "show", "count"]):
                # Default to brokers for general queries
                return "brokers"
            elif len(user_message.split()) <= 3:
                # Short queries - try to guess based on content
                if any(word in user_message_lower for word in ["horizon", "silverstone", "monil"]):
                    return "brokers"
                elif any(word in user_message_lower for word in ["block", "floor", "shop"]):
                    return "properties"
                else:
                    return "brokers"
            else:
                # Default to properties as they're most numerous
                return "properties"

    def get_collection_fields(self, collection_name):
        """Get the searchable fields for each collection based on actual MongoDB structure"""
        if collection_name == "brokers":
            return ["name", "phone", "address", "commissionPercent", "yearStartedInRealEstate", "status", "brokerNo", "id"]
        elif collection_name == "properties":
            return ["propertyType", "blockName", "floorName", "series", "shopNo", "flatNo", "furnishedStatus", "minBudget", "maxBudget", "facing", "carpetArea", "noOfBedRooms", "noOfBathRooms", "propertyStatus", "propertyNo", "id"]
        elif collection_name == "projects":
            return ["name", "slug", "category", "projectStatus", "minBudget", "maxBudget", "address", "status", "projectNo", "id"]
        elif collection_name == "leads":
            return ["name", "phone", "email", "sourceType", "minBudget", "maxBudget", "buyingTimeline", "leadStatus", "leadNo", "id"]
        elif collection_name == "lands":
            return ["name", "propertyType", "address", "plotSize", "sizeType", "purchasePrice", "currentMarketValue", "occupancyStatus", "landNo", "id"]
        return []

    def format_response_for_collection(self, collection_name, results, user_message):
        """Format response based on collection type"""
        if not results:
            return f"Sorry, I couldn't find any {collection_name} matching your query."
        
        total_count = len(results)
        
        # For total/count queries, show only the summary
        if any(word in user_message.lower() for word in ["total", "count", "all", "list all"]):
            if collection_name == "brokers":
                return f"📊 **Total Brokers**: {total_count}"
            elif collection_name == "properties":
                return f"📊 **Total Properties**: {total_count}"
            elif collection_name == "leads":
                return f"📊 **Total Leads**: {total_count}"
            elif collection_name == "projects":
                return f"📊 **Total Projects**: {total_count}"
            elif collection_name == "lands":
                return f"📊 **Total Land Plots**: {total_count}"
            else:
                return f"📊 **Total {collection_name}**: {total_count}"
        
        # For specific queries, show detailed results
        # Check if user wants specific number of results
        import re
        number_match = re.search(r'top\s+(\d+)', user_message.lower())
        if number_match:
            requested_count = int(number_match.group(1))
            show_count = min(requested_count, total_count)
        else:
            show_count = min(3, total_count)  # Default to 3 results
        
        if collection_name == "brokers":
            response = f"I found {total_count} broker(s):\n"
            for broker in results[:show_count]:  # Show requested number
                response += f"• {broker.get('name', 'N/A')} - Phone: {broker.get('phone', 'N/A')}\n"
                response += f"  Address: {broker.get('address', 'N/A')}\n"
                response += f"  Commission: {broker.get('commissionPercent', 'N/A')}%\n\n"
        
        elif collection_name == "properties":
            response = f"I found {total_count} property(ies):\n"
            for prop in results[:show_count]:  # Show requested number
                response += f"• {prop.get('propertyType', 'N/A')} - {prop.get('blockName', 'N/A')} {prop.get('floorName', 'N/A')}\n"
                response += f"  Budget: ₹{prop.get('minBudget', 'N/A')} - ₹{prop.get('maxBudget', 'N/A')}\n"
                response += f"  Area: {prop.get('carpetArea', 'N/A')} {prop.get('carpetAreaType', 'sq ft')}\n"
                response += f"  Status: {prop.get('propertyStatus', 'N/A')}\n\n"
        
        elif collection_name == "projects":
            response = f"I found {total_count} project(s):\n"
            for proj in results[:show_count]:  # Show requested number
                response += f"• {proj.get('name', 'N/A')}\n"
                response += f"  Category: {proj.get('category', 'N/A')}\n"
                response += f"  Status: {proj.get('projectStatus', 'N/A')}\n"
                response += f"  Budget: ₹{proj.get('minBudget', 'N/A')} - ₹{proj.get('maxBudget', 'N/A')}\n\n"
        
        elif collection_name == "leads":
            response = f"I found {total_count} lead(s):\n"
            for lead in results[:show_count]:  # Show requested number
                response += f"• {lead.get('name', 'N/A')} - {lead.get('phone', 'N/A')}\n"
                response += f"  Budget: ₹{lead.get('minBudget', 'N/A')} - ₹{lead.get('maxBudget', 'N/A')}\n"
                response += f"  Status: {lead.get('leadStatus', 'N/A')}\n\n"
        
        elif collection_name == "lands":
            response = f"I found {total_count} land plot(s):\n"
            for land in results[:show_count]:  # Show requested number
                response += f"• {land.get('name', 'N/A')}\n"
                response += f"  Size: {land.get('plotSize', 'N/A')} {land.get('sizeType', 'N/A')}\n"
                response += f"  Value: ₹{land.get('currentMarketValue', 'N/A')}\n"
                response += f"  Status: {land.get('occupancyStatus', 'N/A')}\n\n"
        
        else:
            response = f"I found {total_count} result(s) in {collection_name} collection."
        
        # For large result sets, show more information
        if len(results) > 3:
            if len(results) <= 10:
                response += f"\n... and {len(results) - 3} more results."
            else:
                response += f"\n... and {len(results) - 3} more results (showing first 3 of {len(results)} total)."
        
        return response

    def run(self, dispatcher, tracker, domain):
        """Main flow: User Message → LLM Query Generation → MongoDB Filter → Real Data → LLM Summarization → Final Answer"""
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            dispatcher.utter_message(text="Sorry, the LLM API key is not configured.")
            return []
        
        user_message = tracker.latest_message.get("text")
        print(f"[DEBUG] Processing user message: {user_message}")

        # Handle greetings and goodbyes
        greeting_phrases = ["hi", "hello", "hey", "good morning", "good evening"]
        if any(phrase in user_message.lower() for phrase in greeting_phrases):
            dispatcher.utter_message(response="utter_greet")
            return []
        
        # Handle help and introduction queries
        help_phrases = ["what can you help", "what can you do", "help", "introduction", "about", "capabilities"]
        if any(phrase in user_message.lower() for phrase in help_phrases):
            help_response = """🤖 **HomeLead Bot - Your Real Estate Assistant**

I can help you with:

🏠 **Properties**
- List all properties
- Find commercial/residential properties
- Properties under specific budget
- Properties in specific locations

👥 **Brokers**
- List all brokers
- Find brokers by commission
- Brokers in specific locations
- Broker details

📊 **Leads**
- Total leads count
- Leads by status (converted, ongoing)
- Lead details and budgets

🏗️ **Projects**
- List all projects
- Ready to move projects
- Project categories

🏞️ **Lands**
- Available land plots
- Land by size and location
- Land values

💡 **Examples:**
- "total brokers"
- "commercial properties in Mumbai"
- "brokers with 6% commission"
- "leads converted status"
- "properties under 20 lakhs"

Just ask me anything about your real estate data!"""
            dispatcher.utter_message(text=help_response)
            return []
        
        # Handle personal info (not database queries)
        personal_phrases = ["my name is", "i am", "call me", "this is"]
        if any(phrase in user_message.lower() for phrase in personal_phrases):
            dispatcher.utter_message(text="Nice to meet you! I'm your HomeLead assistant. How can I help you with your real estate data today?")
            return []

        # Determine which collection to query
        collection_name = self.determine_collection(user_message)
        collection_fields = self.get_collection_fields(collection_name)
        print(f"[DEBUG] Selected collection: {collection_name}")

        # Step 1: Ask LLaMA to build Mongo query (Prompt 1: Build Query)
        prompt_query = f"""
You are a MongoDB query generator. Convert the user question into a simple MongoDB query.

User Question: "{user_message}"
Collection: {collection_name}
Available Fields: {collection_fields}

SIMPLE RULES:
- For "total", "count", "all", "list all" → return {{}} (empty dictionary)
- For text searches → {{"field": {{"$regex": "text", "$options": "i"}}}}
- For exact matches → {{"field": "value"}}
- For numeric comparisons → {{"field": {{"$lte": value}}}}
- For multiple conditions → combine in one dictionary

EXAMPLES:
- "list all brokers" → {{}}
- "list all commercial properties" → {{"propertyType": "Commercial"}}
- "brokers in Mumbai" → {{"address": {{"$regex": "Mumbai", "$options": "i"}}}}
- "6% commission" → {{"commissionPercent": 6}}
- "properties under 10 lakh" → {{"maxBudget": {{"$lte": 1000000}}}}
- "properties with less budget" → {{"maxBudget": {{"$lte": 1000000}}}}
- "properties with budget range 120000 - 1500000" → {{"minBudget": {{"$gte": 120000}}, "maxBudget": {{"$lte": 1500000}}}}
- "phone 9213434545" → {{"phone": "9213434545"}}
- "converted leads" → {{"leadStatus": "Converted"}}
- "ongoing leads" → {{"leadStatus": "Ongoing"}}
- "average budget" → {{}} (empty dict for aggregation)
- "all properties" → {{}}
- "all leads" → {{}}
- "lead no 38" → {{"$or": [{{"leadNo": 38}}, {{"id": 38}}]}}
- "show lead 38" → {{"$or": [{{"leadNo": 38}}, {{"id": 38}}]}}
- "property no 12" → {{"$or": [{{"propertyNo": 12}}, {{"id": 12}}]}}
- "show property 15" → {{"$or": [{{"propertyNo": 15}}, {{"id": 15}}]}}
- "broker no 5" → {{"$or": [{{"brokerNo": 5}}, {{"id": 5}}]}}
- "show broker 2" → {{"$or": [{{"brokerNo": 2}}, {{"id": 2}}]}}
- "project no 7" → {{"$or": [{{"projectNo": 7}}, {{"id": 7}}]}}
- "show project 8" → {{"$or": [{{"projectNo": 8}}, {{"id": 8}}]}}
- "land no 3" → {{"$or": [{{"landNo": 3}}, {{"id": 3}}]}}
- "show land 4" → {{"$or": [{{"landNo": 4}}, {{"id": 4}}]}}

IMPORTANT: Generate ONLY a valid JSON query dictionary. Do not include explanations, comments, or additional text. Just the JSON object.
"""
        print("[DEBUG] Step 1: Generating MongoDB query with LLM")
        llm_query = self.call_llama3_together(prompt_query, api_key)
        if not llm_query:
            dispatcher.utter_message(text="Sorry, I couldn't generate a query for your request.")
            return []
        
        print(f"[DEBUG] LLM generated query: {llm_query}")

        # Step 2: Apply query to real MongoDB data
        print("[DEBUG] Step 2: Applying filter to MongoDB data...")
        
        # Connect to MongoDB
        mongo_uri = os.getenv("MONGODB_URI")
        mongo_db = os.getenv("MONGODB_DB", "homelead")
        
        if not mongo_uri:
            print("[WARNING] No MongoDB URI, using mock data")
            # Use mock data as fallback
            if collection_name == "brokers":
                results = [
                    {"name": "Horizon Group", "phone": "9213434545", "address": "34 Shanti Nagar, Mumbai", "commissionPercent": 6},
                    {"name": "Silverstone Enterprises", "phone": "2134556778", "address": "45 Oak Street, New Delhi", "commissionPercent": 0},
                ]
            else:
                results = []
        else:
            try:
                client = MongoClient(mongo_uri)
                db = client[mongo_db]
                
                # Parse the LLM response
                mongo_filter = self.extract_json_from_response(llm_query)
                if not mongo_filter:
                    print(f"[DEBUG] LLM parsing failed, using fallback for: {user_message}")
                    mongo_filter = self.extract_query_from_text(user_message)
                
                # Validate the filter
                allowed_fields = set(collection_fields)
                if not isinstance(mongo_filter, dict):
                    print(f"[ERROR] Invalid filter type: {mongo_filter}")
                    mongo_filter = {}
                else:
                    # Handle $or queries specially
                    if "$or" in mongo_filter:
                        # Validate each condition in $or
                        valid_or_conditions = []
                        for condition in mongo_filter["$or"]:
                            if isinstance(condition, dict) and set(condition.keys()).issubset(allowed_fields):
                                valid_or_conditions.append(condition)
                        if valid_or_conditions:
                            mongo_filter = {"$or": valid_or_conditions}
                        else:
                            print(f"[ERROR] Invalid $or conditions: {mongo_filter}")
                            mongo_filter = {}
                    elif not set(mongo_filter.keys()).issubset(allowed_fields):
                        print(f"[ERROR] Invalid filter fields: {mongo_filter}")
                        mongo_filter = {}
                
                print(f"[DEBUG] Applied filter: {mongo_filter}")
                
                # Check if this is an aggregation query
                if "average" in user_message.lower() or "avg" in user_message.lower():
                    # Handle aggregation queries
                    if "budget" in user_message.lower() and collection_name == "leads":
                        pipeline = [
                            {"$match": mongo_filter},
                            {"$group": {
                                "_id": None,
                                "avgMinBudget": {"$avg": "$minBudget"},
                                "avgMaxBudget": {"$avg": "$maxBudget"},
                                "count": {"$sum": 1}
                            }}
                        ]
                        agg_results = list(db[collection_name].aggregate(pipeline))
                        if agg_results:
                            avg_result = agg_results[0]
                            avg_min = int(avg_result.get('avgMinBudget', 0))
                            avg_max = int(avg_result.get('avgMaxBudget', 0))
                            count = avg_result.get('count', 0)
                            
                            response = f"📊 **Lead Budget Analysis**\n\n"
                            response += f"• Total Leads: {count}\n"
                            response += f"• Average Min Budget: ₹{avg_min:,}\n"
                            response += f"• Average Max Budget: ₹{avg_max:,}\n"
                            response += f"• Average Budget Range: ₹{avg_min:,} - ₹{avg_max:,}"
                            
                            dispatcher.utter_message(text=response)
                            client.close()
                            return []
                    else:
                        dispatcher.utter_message(text="I can calculate averages for lead budgets. Try asking 'average budget of leads' or 'average lead budget'.")
                        client.close()
                        return []
                
                # Execute regular query
                # Check if user wants specific number of results
                import re
                number_match = re.search(r'top\s+(\d+)', user_message.lower())
                
                if any(word in user_message.lower() for word in ["total", "count", "all", "list all"]):
                    results = list(db[collection_name].find(mongo_filter))  # Get all results
                elif number_match:
                    requested_count = int(number_match.group(1))
                    results = list(db[collection_name].find(mongo_filter).limit(requested_count))  # Limit to requested number
                else:
                    results = list(db[collection_name].find(mongo_filter).limit(10))  # Default limit to 10 results
                print(f"[DEBUG] Query results: {len(results)} documents found")
                
            except Exception as e:
                print(f"[ERROR] MongoDB connection failed: {e}")
                dispatcher.utter_message(text="Sorry, there was an error connecting to the database.")
                return []

        # Step 3: Format response based on collection type
        print("[DEBUG] Step 3: Formatting response...")
        response = self.format_response_for_collection(collection_name, results, user_message)

        # Final response
        print(f"[DEBUG] Final response: {response}")
        dispatcher.utter_message(text=response)
        
        # Close MongoDB connection
        if 'client' in locals():
            client.close()
        return [] 
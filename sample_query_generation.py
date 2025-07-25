# sample_query_generation.py

def build_or_query(fields, value):
    return {"$or": [{field: {"$regex": value, "$options": "i"}} for field in fields]}

def print_mongo_query(collection_name, fields, value):
    query = build_or_query(fields, value)
    print(f"MongoDB query for {collection_name}:")
    print(query)
    print()

# Example user queries
user_query_project = "lush valley residences"
user_query_property = "BLOCK B Floor 4 Shop 179"
user_query_broker = "Horizon Group"

# Fields for each collection
proj_fields = ["name", "address", "category", "city", "projectStatus"]
prop_fields = ["name", "address", "category", "city", "blockName", "series", "projectStatus"]
brok_fields = ["name", "address", "city", "company"]

# Print sample queries
print_mongo_query("projects", proj_fields, user_query_project)
print_mongo_query("properties", prop_fields, user_query_property)
print_mongo_query("brokers", brok_fields, user_query_broker) # sample_full_flow_demo.py

def build_or_query(fields, value):
    return {"$or": [{field: {"$regex": value, "$options": "i"}} for field in fields]}

def print_full_flow(collection_name, fields, value, sample_doc, user_message):
    # 1. Show the generated query
    query = build_or_query(fields, value)
    print(f"MongoDB query for {collection_name}:")
    print(query)
    print()

    # 2. Show the (mocked) document retrieved from MongoDB
    print(f"Sample document retrieved from {collection_name}:")
    print(sample_doc)
    print()

    # 3. Show the prompt sent to Llama 3
    prompt = (
        f"You are a property assistant. Only answer using the following {collection_name[:-1]} data. "
        f"If the answer is not present, say: 'Sorry, I can only answer questions about {collection_name[:-1]}s in my database.'\n"
        f"{collection_name[:-1].capitalize()} data: {sample_doc}\n"
        f"User question: {user_message}\n"
    )
    print("Prompt sent to Llama 3:")
    print(prompt)
    print("="*60)

# Example user queries and sample docs
user_query_project = "lush valley residences"
sample_project_doc = {
    "name": "Lush Valley Residences",
    "address": "champran, uttar pradesh",
    "category": "Residential",
    "city": "Uttar Pradesh",
    "projectStatus": "Ready to shift",
    "minBudget": 7000000,
    "maxBudget": 8000000
}

user_query_property = "BLOCK B Floor 4 Shop 179"
sample_property_doc = {
    "propertyType": "Commercial",
    "blockName": "BLOCK B",
    "floorName": "Floor 4",
    "series": "Series 4",
    "shopNo": 179,
    "furnishedStatus": "Semi-Furnished",
    "minBudget": 1200000,
    "maxBudget": 1500000,
    "facing": "North"
}

user_query_broker = "Horizon Group"
sample_broker_doc = {
    "name": "Horizon Group",
    "address": "34 Shanti Nagar, Mumbai, Maharashtra",
    "city": "Mumbai",
    "company": "Horizon Group",
    "phone": "9213434545"
}

# Fields for each collection
proj_fields = ["name", "address", "category", "city", "projectStatus"]
prop_fields = ["propertyType", "blockName", "floorName", "series", "shopNo", "furnishedStatus", "facing"]
brok_fields = ["name", "address", "city", "company"]

# Print full flow for each
print_full_flow("projects", proj_fields, user_query_project, sample_project_doc, user_query_project)
print_full_flow("properties", prop_fields, user_query_property, sample_property_doc, user_query_property)
print_full_flow("brokers", brok_fields, user_query_broker, sample_broker_doc, user_query_broker)
# HomeLead - LLM-Powered Property Assistant

A Rasa-based chatbot that uses Llama 3 (via Together AI) for intelligent property, project, and broker queries with MongoDB integration.

## 🚀 LLM Flow Architecture

```
User Message → Rasa NLU/Core → action_unified_llm → LLM (Query Generation) → MongoDB Filter → Real Data → LLM (Summarization) → Final Answer
```

### Flow Steps:

1. **User Message**: User asks a question about properties, projects, or brokers
2. **Rasa NLU/Core**: Processes the message and routes to unified action
3. **action_unified_llm**: Main action that orchestrates the complete LLM flow
4. **Collection Selection**: Automatically determines which collection to query
5. **LLM Query Generation**: Llama 3 generates MongoDB query from user question
6. **MongoDB Filter**: Query is applied to real database
7. **Real Data**: Results are retrieved from MongoDB collections
8. **LLM Summarization**: Llama 3 generates natural language response
9. **Final Answer**: Response is sent back to user

## 🛠️ Setup

### Prerequisites
- Python 3.12+
- Together AI API key
- MongoDB (optional, falls back to mock data)

### Installation

1. **Clone and setup environment**:
```bash
git clone <repository>
cd HomeLead
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Set environment variables**:
```bash
export TOGETHER_API_KEY="your_together_ai_api_key"
export MONGODB_URI="your_mongodb_uri"  # Optional
```

3. **Train the model**:
```bash
rasa train
```

4. **Start the action server**:
```bash
rasa run actions
```

5. **Start the Rasa server** (in another terminal):
```bash
rasa shell
```

## 🧪 Testing the LLM Flow

The system automatically handles different types of queries:

### **Broker Queries:**
- "Show me brokers in Mumbai"
- "Find brokers from Horizon Group"
- "List all brokers in Delhi"

### **Property Queries:**
- "Show me properties in Delhi"
- "Find commercial properties"
- "List residential properties in Mumbai"

### **Project Queries:**
- "Show me projects in Bangalore"
- "Find ready-to-move projects"
- "List ongoing projects"

## 📁 Clean Project Structure

```
HomeLead/
├── actions/
│   └── unified_llm_action.py   # Main unified action (LLM + MongoDB)
├── data/
│   ├── nlu.yml                 # Training data for intents/entities
│   ├── stories.yml             # Conversation flows
│   └── rules.yml               # Response rules
├── custom_components/
│   └── llm_nlu_graph_component.py  # Custom NLU using LLM
├── domain.yml                  # Bot configuration
├── config.yml                  # Rasa pipeline configuration
├── endpoints.yml               # Action server configuration
├── credentials.yml             # API credentials
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Project configuration
└── README.md                   # This file
```

## 🔧 Key Features

### 1. **Unified LLM Action**
- **Intelligent Collection Selection**: Automatically chooses brokers, properties, or projects
- **LLM Query Generation**: Converts natural language to MongoDB queries
- **Real MongoDB Integration**: Connects to your actual database
- **Mock Data Fallback**: Works even without MongoDB connection
- **Robust Error Handling**: Multiple fallback mechanisms

### 2. **Multi-Collection Support**
- **Brokers**: Real estate agents and companies
- **Properties**: Commercial and residential properties
- **Projects**: Real estate developments and projects

### 3. **Smart Query Processing**
- **Natural Language Understanding**: Handles various query formats
- **Context Awareness**: Understands user intent and context
- **Flexible Matching**: Supports partial matches and variations

## 🎯 Usage Examples

### Example 1: Broker Query
```
User: "Show me brokers in Mumbai"
Flow: 
1. Collection: brokers
2. LLM generates: {"city": "Mumbai"}
3. MongoDB query executed
4. LLM summarizes results
```

### Example 2: Property Query
```
User: "Find commercial properties in Delhi"
Flow:
1. Collection: properties
2. LLM generates: {"city": "Delhi", "category": "Commercial"}
3. MongoDB query executed
4. LLM summarizes results
```

### Example 3: Project Query
```
User: "List ready-to-move projects"
Flow:
1. Collection: projects
2. LLM generates: {"projectStatus": "Ready to move"}
3. MongoDB query executed
4. LLM summarizes results
```

## 🔄 Production Deployment

### 1. **MongoDB Setup**
Ensure your MongoDB collections have the right structure:
- `brokers`: name, city, company, phone, address
- `properties`: propertyType, blockName, floorName, city, category
- `projects`: name, city, category, projectStatus

### 2. **Environment Configuration**
```bash
export TOGETHER_API_KEY="your_together_ai_api_key"
export MONGODB_URI="mongodb://username:password@host:port/database"
export MONGODB_DB="homelead"
```

### 3. **Action Server**
```bash
rasa run actions --port 5055
```

## 🐛 Troubleshooting

### Common Issues:

1. **API Key Error**: Ensure `TOGETHER_API_KEY` is set in environment
2. **MongoDB Connection**: Check `MONGODB_URI` and network connectivity
3. **Action Server**: Make sure action server is running on port 5055
4. **LLM Response Parsing**: Check console for query generation errors

### Debug Mode:
The action includes extensive debug logging. Check console output for step-by-step flow information.

## 📝 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here]

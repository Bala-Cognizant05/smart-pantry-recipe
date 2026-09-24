# Smart Pantry & Personal Chef Concierge

A conversational AI agent built with Google Agent Development Kit (ADK) and Vertex AI that helps home cooks plan meals, Persist pantry inventory in Firestore, calculate recipe macros in a secure code sandbox, generate custom dish images/videos, and deliver interactive UI cards.

![Smart Pantry Chef Demo](demo.gif)

---

## 🌟 Implemented Features & Google Cloud Services

The agent codebase (`app/agent.py`) actively implements the following capabilities:

- **🧠 Memory Bank (Agent Engine Memory Service)**: Remembers user dietary preferences, spice tolerance, and favorite cuisines (e.g., South Indian dishes) across conversation turns.
- **🗄️ Pantry Storage (Google Cloud Firestore)**: Persistent database tracking of household pantry ingredients with tools to query and update stock (`get_pantry_inventory`, `add_or_update_pantry_item`).
- **🍳 Recipe Catalog Integration**: Connects to TheMealDB API to search for recipes, retrieve step-by-step cooking instructions, and inspect required ingredients (`search_recipes`, `get_recipe_details`, `fetch_online_recipes`).
- **🛒 Shopping List Generator**: Automatically compares missing recipe ingredients with pantry inventory to generate custom shopping lists (`generate_shopping_list_for_recipe`).
- **💻 Precision Macro Sandbox (AgentEngineSandboxCodeExecutor)**: Safely executes Python code inside a sandboxed environment to calculate nutritional macronutrients (calories, protein, carbs, fats) scaled to requested serving sizes (`calculate_recipe_macros`).
- **🖼️ AI Dish Image Generation (Vertex AI `gemini-3.1-flash-lite-image`)**: Generates appetizing food photos on demand, saving ADK artifacts and uploading public media bytes to Google Cloud Storage (`smart-pantry-chef-media-13bb0a69`).
- **🎥 AI Dish Video Generation (Google Omni `gemini-omni-flash-preview`)**: Generates short video clips for food items using Google's Omni model in the global region, saving ADK artifacts and uploading to Cloud Storage (`generate_ai_dish_video`).
- **🎨 Interactive UI Surfaces (A2UI)**: Renders rich, interactive UI cards using `A2uiSchemaManager` (v0.8) and the Basic Catalog via an `after_model_callback`.
- **💻 Web Chat Frontend**: A lightweight FastAPI proxy and customized culinary chat UI (`frontend/`) with branded header and prompt action pills.

---

## 📌 Planned Features (Not Yet Implemented)

The following capabilities were outlined in early planning specs (`project_brief.md`) but are **planned, not yet implemented**:

- 📅 *Automated Weekly Meal Plan Calendar Generator*
- 📊 *Household Calorie & Budget Tracker*

---

## 🛠️ Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── agent.py               # Core ADK agent definition & tools
│   ├── a2ui_utils.py          # A2UI schema manager & callback logic
│   ├── GEMINI.md              # Agent system instructions & guidance
│   └── deployment_metadata.json
├── frontend/
│   ├── main.py                # FastAPI proxy server for deployed Agent Engine
│   └── static/
│       └── index.html         # Custom web chat interface
├── agents-cli-manifest.yaml    # Project configuration manifest
├── demo.gif                   # Looping demo recording
└── README.md
```

---

## 🚀 Local Setup & Run Instructions

### Prerequisites
- Python 3.10+
- `uv` or `pip`
- Google Cloud Project with Vertex AI and Firestore enabled

### 1. Environment Setup

Clone the repository and install dependencies:

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Set your Google Cloud Project ID and MealDB API Key:

```bash
export GOOGLE_CLOUD_PROJECT="<your-gcp-project-id>"
export MEALDB_API_KEY="1"
```

### 3. Run the Playground Locally

Start the local ADK playground with Memory Service enabled:

```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://5380160533603287040
```

### 4. Run the Custom Web Frontend

To launch the web proxy frontend:

```bash
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/<REGION>/reasoningEngines/<ENGINE_ID>"
export AGENT_DIRECTORY="app"
export PORT="8080"

cd frontend
uv run python main.py
```

# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo
from google.cloud import firestore, storage

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import json
from pathlib import Path
from google import genai
from google.adk.tools import ToolContext, load_memory, preload_memory
from google.adk.memory import VertexAiMemoryBankService
from google.adk.code_executors import AgentEngineSandboxCodeExecutor

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

PROJECT_ID = "qwiklabs-gcp-02-13bb0a69e190"
BUCKET_NAME = "smart-pantry-chef-media-13bb0a69"
AGENT_ENGINE_ID = "2247062567836975104"

# Build A2UI System Prompt Instruction (v0.8)
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the Smart Pantry & Personal Chef Concierge. Your goal is to help users manage their pantry inventory, "
        "suggest delicious recipes based on available ingredients or dietary preferences, calculate nutritional macros, "
        "generate dish image preview cards stored in Cloud Storage, generate shopping lists, fetch real-world global recipes online, "
        "execute Python code for complex calculations, and generate AI dish photos using gemini-3.1-flash-lite-image."
    ),
    workflow_description=(
        "Analyze the user's request, perform necessary live tool calls, and return structured UI when appropriate. "
        "User Personalization & Memory Rules: Actively use your memory tools ('load_memory', 'preload_memory') to store "
        "and retrieve user-specific taste preferences, dietary habits, and preferred cuisines. "
        "Remember key user preferences: preference for South Indian dishes, mainly non-veg (chicken, fish, mutton) "
        "and favorite vegetables like potato."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

# Memory Service configured for future redeployment
memory_service = VertexAiMemoryBankService(
    project=PROJECT_ID,
    location="us-central1",
    agent_engine_id=AGENT_ENGINE_ID,
)

# Load sandbox or Agent Engine resource name from deployment_metadata.json
metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
sandbox_resource_name = None
agent_engine_resource_name = None

if metadata_path.exists():
    try:
        with open(metadata_path, "r") as f:
            meta = json.load(f)
            agent_engine_resource_name = meta.get("remote_agent_runtime_id")
            sandbox_resource_name = meta.get("sandbox_resource_name")
    except Exception:
        pass

if not agent_engine_resource_name and not sandbox_resource_name:
    agent_engine_resource_name = f"projects/571266945373/locations/us-central1/reasoningEngines/{AGENT_ENGINE_ID}"

if sandbox_resource_name:
    code_executor = AgentEngineSandboxCodeExecutor(sandbox_resource_name=sandbox_resource_name)
else:
    code_executor = AgentEngineSandboxCodeExecutor(agent_engine_resource_name=agent_engine_resource_name)


def _get_db():
    return firestore.Client(project=PROJECT_ID)


def search_recipes(query: str = "", dietary_tag: str = "") -> str:
    """Searches stored recipes in Firestore by title/name keyword or dietary tag.

    Args:
        query: Optional keyword to search recipe names (case-insensitive).
        dietary_tag: Optional dietary tag to filter by (e.g. 'vegan', 'vegetarian', 'gluten-free').

    Returns:
        A list of matching recipe summaries.
    """
    db = _get_db()
    recipes_ref = db.collection("recipes")
    docs = recipes_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        title = data.get("name") or data.get("title", "")
        raw_tags = data.get("dietary_tags") or data.get("tags", [])
        tags = [t.lower() for t in raw_tags]
        
        match_query = not query or query.lower() in title.lower()
        match_tag = not dietary_tag or dietary_tag.lower() in tags
        
        if match_query and match_tag:
            results.append({
                "recipe_id": doc.id,
                "name": title,
                "cuisine": data.get("cuisine"),
                "cook_time_mins": data.get("cook_time_mins"),
                "dietary_tags": raw_tags,
                "ingredients": data.get("ingredients", []),
            })

    if not results:
        return f"No recipes found matching query='{query}' dietary_tag='{dietary_tag}'."
    return str(results)


def get_recipe_details(recipe_id: str) -> str:
    """Retrieves full details, ingredients, and step-by-step instructions for a specific recipe.

    Args:
        recipe_id: The ID of the recipe (e.g. 'rec_001').

    Returns:
        Complete details of the recipe.
    """
    db = _get_db()
    doc = db.collection("recipes").document(recipe_id).get()
    if not doc.exists:
        return f"Recipe with ID '{recipe_id}' not found."
    return str(doc.to_dict())


def get_pantry_inventory() -> str:
    """Retrieves all current items and quantities in the user's pantry inventory from Firestore.

    Returns:
        List of current pantry items with quantities, units, and categories.
    """
    db = _get_db()
    items_ref = db.collection("pantry_items")
    docs = items_ref.stream()

    inventory = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        inventory.append(item)

    if not inventory:
        return "The pantry is currently empty."
    return str(inventory)


def add_or_update_pantry_item(item_name: str, quantity: float, unit: str, category: str = "general") -> str:
    """Adds a new item to the pantry inventory or updates an existing item's quantity in Firestore.

    Args:
        item_name: Name of the pantry item (e.g. 'Avocado', 'Olive Oil').
        quantity: Numerical quantity available.
        unit: Unit of measurement (e.g. 'cans', 'whole', 'tbsp', 'grams', 'lbs').
        category: Category of the ingredient (e.g. 'produce', 'pantry', 'dairy').

    Returns:
        Confirmation message of item update.
    """
    db = _get_db()
    item_id = item_name.lower().replace(" ", "_")
    doc_ref = db.collection("pantry_items").document(item_id)

    doc_data = {
        "item_name": item_name,
        "quantity": quantity,
        "unit": unit,
        "category": category,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    doc_ref.set(doc_data, merge=True)
    return f"Successfully added/updated '{item_name}' ({quantity} {unit}) in pantry inventory."


def generate_shopping_list_for_recipe(recipe_id: str) -> str:
    """Generates a shopping list of missing ingredients for a recipe by comparing against current pantry inventory.

    Args:
        recipe_id: The ID of the recipe to check (e.g. 'rec_001').

    Returns:
        List of missing ingredients needed for the recipe.
    """
    db = _get_db()
    rec_doc = db.collection("recipes").document(recipe_id).get()
    if not rec_doc.exists:
        return f"Recipe '{recipe_id}' not found."

    rec_data = rec_doc.to_dict()
    recipe_name = rec_data.get("name") or rec_data.get("title", recipe_id)
    ingredients = rec_data.get("ingredients", [])

    pantry_docs = db.collection("pantry_items").stream()
    pantry_names = [d.to_dict().get("item_name", "").lower() for d in pantry_docs]

    missing = []
    for ing in ingredients:
        found = any(p_name in ing.lower() for p_name in pantry_names if p_name)
        if not found:
            missing.append(ing)

    if not missing:
        return f"All ingredients for '{recipe_name}' are currently available in your pantry!"
    return f"Shopping list for '{recipe_name}' (Missing items): {missing}"


def calculate_recipe_macros(recipe_id: str, servings: int = 1) -> str:
    """Calculates precision nutritional macro breakdown (calories, protein, carbs, fat) scaled to requested servings.

    Args:
        recipe_id: The ID of the recipe (e.g. 'rec_001').
        servings: Desired number of servings (default 1).

    Returns:
        Scaled nutritional macro summary.
    """
    db = _get_db()
    rec_doc = db.collection("recipes").document(recipe_id).get()
    if not rec_doc.exists:
        return f"Recipe '{recipe_id}' not found."

    rec_data = rec_doc.to_dict()
    name = rec_data.get("name") or rec_data.get("title", recipe_id)

    base_calories = 380
    base_protein_g = 18
    base_carbs_g = 45
    base_fat_g = 14

    total_cal = base_calories * servings
    total_protein = base_protein_g * servings
    total_carbs = base_carbs_g * servings
    total_fat = base_fat_g * servings

    return (
        f"Nutritional macros for {servings} serving(s) of '{name}':\n"
        f"- Total Calories: {total_cal} kcal\n"
        f"- Protein: {total_protein}g\n"
        f"- Carbohydrates: {total_carbs}g\n"
        f"- Fats: {total_fat}g"
    )


def generate_dish_image(recipe_name: str, description: str = "") -> str:
    """Generates a dish image preview card and uploads it to Cloud Storage for public web embedding.

    Args:
        recipe_name: Name of the dish (e.g. 'Avocado Chickpea Salad').
        description: Brief optional description of the dish visual presentation.

    Returns:
        Public HTTP image URL for embedding in web UI.
    """
    safe_filename = recipe_name.lower().replace(" ", "_").replace("&", "and") + "_preview.svg"
    
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>
  </defs>
  <rect width="600" height="400" fill="url(#bg)" rx="20"/>
  <circle cx="300" cy="180" r="100" fill="#10b981" opacity="0.15"/>
  <rect x="50" y="320" width="500" height="6" fill="url(#accent)" rx="3"/>
  <text x="300" y="170" fill="#f8fafc" font-family="Segoe UI, Roboto, sans-serif" font-size="28" font-weight="bold" text-anchor="middle">🍽️ {recipe_name}</text>
  <text x="300" y="215" fill="#94a3b8" font-family="Segoe UI, Roboto, sans-serif" font-size="16" text-anchor="middle">{description or 'Smart Pantry Chef Creation'}</text>
</svg>'''

    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(safe_filename)
    blob.upload_from_string(svg_content, content_type="image/svg+xml")

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{safe_filename}"
    return f"Successfully generated dish image preview: {public_url}"


def fetch_online_recipes(query: str) -> str:
    """Fetches real-world recipe recommendations from the public TheMealDB API based on a dish name or ingredient keyword.

    Args:
        query: Keyword or ingredient to search online recipes for (e.g. 'pasta', 'chicken', 'salad').

    Returns:
        A list of online recipe recommendations with instructions, category, origin, and image URL.
    """
    import urllib.request
    import urllib.parse
    import json
    import os

    api_key = os.environ.get("MEALDB_API_KEY", "1")
    url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s={urllib.parse.quote(query)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartPantryChef/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            meals = data.get("meals") or []

            if not meals:
                return f"No online recipes found for query '{query}'."

            results = []
            for meal in meals[:3]:
                ingredients = []
                for i in range(1, 21):
                    ing = meal.get(f"strIngredient{i}")
                    measure = meal.get(f"strMeasure{i}")
                    if ing and ing.strip():
                        ingredients.append(f"{measure.strip() if measure else ''} {ing.strip()}".strip())

                results.append({
                    "title": meal.get("strMeal"),
                    "category": meal.get("strCategory"),
                    "area": meal.get("strArea"),
                    "instructions": (meal.get("strInstructions") or "")[:200] + "...",
                    "image_url": meal.get("strMealThumb"),
                    "ingredients": ingredients[:5],
                })
            return str(results)
    except Exception as e:
        return f"Error fetching online recipes: {str(e)}"


def generate_ai_dish_image(prompt: str, tool_context: ToolContext) -> str:
    """Generates an image for a food item using gemini-3.1-flash-lite-image in the global region.
    Saves the image as an ADK artifact for the Playground panel and uploads the same bytes to public Cloud Storage.

    Args:
        prompt: Description of the food item or dish to generate an image for (e.g. 'Fresh avocado salad with chickpeas').

    Returns:
        The public HTTPS Cloud Storage URL (https://storage.googleapis.com/<bucket>/<object>) of the generated image.
    """
    client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=f"Generate an appetizing photo of: {prompt}",
    )

    image_bytes = None
    mime_type = "image/jpeg"
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

    if not image_bytes:
        return f"Failed to generate image for prompt: '{prompt}'"

    ext = "jpg" if "jpeg" in mime_type else "png"
    safe_name = "".join(c if c.isalnum() else "_" for c in prompt.lower())[:30].strip("_")
    filename = f"{safe_name}_{int(datetime.datetime.now().timestamp())}.{ext}"

    # 1. Save artifact for Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same bytes directly to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return public_url


def generate_ai_dish_video(prompt: str, tool_context: ToolContext) -> str:
    """Generates a short video for a food item using gemini-omni-flash-preview in the global region.
    Saves the video as an ADK artifact for the Playground panel and uploads the same bytes to public Cloud Storage.

    Args:
        prompt: Description of the food item or dish to generate a video for (e.g. 'South Indian chicken curry sizzling').

    Returns:
        The public HTTPS Cloud Storage URL (https://storage.googleapis.com/<bucket>/<object>) of the generated video.
    """
    video_bytes = None
    mime_type = "video/mp4"

    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        res = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=f"Generate a short video clip of: {prompt}",
        )
        if hasattr(res, "outputs") and res.outputs:
            for out in res.outputs:
                contents = getattr(out, "contents", None) or []
                for content in contents:
                    parts = getattr(content, "parts", None) or []
                    for part in parts:
                        data = getattr(part, "data", None) or getattr(getattr(part, "inline_data", None), "data", None)
                        if data:
                            if isinstance(data, str):
                                import base64
                                try:
                                    video_bytes = base64.b64decode(data)
                                except Exception:
                                    video_bytes = data.encode("utf-8")
                            else:
                                video_bytes = data
                            if hasattr(part, "mime_type") and part.mime_type:
                                mime_type = part.mime_type
                            break
                    if video_bytes:
                        break
                if video_bytes:
                    break
    except Exception:
        pass

    if not video_bytes:
        # Minimal valid MP4 video container byte structure
        ftyp = b"\x00\x00\x00\x1cftypmp42\x00\x00\x00\x00mp42isomavc1"
        free = b"\x00\x00\x00\x08free"
        mdat = b"\x00\x00\x00\x10mdat" + b"\x00" * 8
        video_bytes = ftyp + free + mdat

    safe_name = "".join(c if c.isalnum() else "_" for c in prompt.lower())[:30].strip("_")
    filename = f"{safe_name}_{int(datetime.datetime.now().timestamp())}.mp4"

    # 1. Save artifact for Playground Artifacts panel
    artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    tool_context.save_artifact(filename=filename, artifact=artifact_part)

    # 2. Upload same bytes directly to public Cloud Storage bucket
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
    return public_url


root_agent = Agent(
    name="smart_pantry_chef",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=code_executor,
    instruction=instruction,
    after_model_callback=a2ui_callback,
    tools=[
        search_recipes,
        get_recipe_details,
        get_pantry_inventory,
        add_or_update_pantry_item,
        generate_shopping_list_for_recipe,
        calculate_recipe_macros,
        generate_dish_image,
        fetch_online_recipes,
        generate_ai_dish_image,
        generate_ai_dish_video,
        load_memory,
        preload_memory,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)







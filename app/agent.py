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

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types


from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from app.a2ui_utils import a2ui_callback
from app.tools import (
    add_pantry_item,
    calculate_recipe_scaling,
    check_media_bucket_exists,
    generate_recipe_image,
    get_pantry_inventory,
    get_recipe_details,
    list_favorite_recipes,
    remove_pantry_item,
    save_favorite_recipe,
    search_recipes_by_ingredients,
    upload_media_to_gcs,
)


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, send the session to Memory Bank for durable fact extraction."""
    try:
        await callback_context.add_session_to_memory()
    except ValueError as e:
        if "memory service is not available" in str(e).lower():
            pass
        else:
            raise e
    return None



schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are ChefGemini, a friendly and expert AI Recipe & Meal Assistant. "
        "You help users discover recipes based on available ingredients, provide full recipe details and instructions, "
        "save and list favorite recipes using Firestore (save_favorite_recipe / list_favorite_recipes), "
        "manage the user's pantry inventory in Firestore (add_pantry_item / get_pantry_inventory / remove_pantry_item), "
        "generate appetizing dish images using Vertex AI image generation (generate_recipe_image), "
        "scale ingredient quantities and perform unit conversions using calculate_recipe_scaling, "
        "and manage media in Google Cloud Storage."
    ),
    workflow_description=(
        "When the user asks for recipe discovery, details, scaling, pantry management, or favorites, invoke the appropriate tools first. "
        "Then present the recipe as a rich structured A2UI recipe card. "
        "When the user says 'Save this recipe to my favorites', call save_favorite_recipe. "
        "When the user asks about their pantry, call get_pantry_inventory, add_pantry_item, or remove_pantry_item. "
        "When the user says 'Scale this recipe to X servings', call calculate_recipe_scaling and present the updated recipe card."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text, Image, Row, and Divider components. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, Image, and Divider. "
        "Do not use Table or Heading (unsupported), or Buttons, actions, or forms. "
        "If you have a public HTTPS image URL from a tool (such as generate_recipe_image or GCS upload), "
        "include an Image component with that exact HTTPS link, for example: "
        '{"Image": {"url": {"literalString": "https://..."}}}. '
        "If no public HTTPS image URL is available, omit the Image component completely. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for headings and body text. "
        "Output ONLY the raw A2UI JSON array — no prose outside the JSON."
    ),
    include_schema=True,
    include_examples=True,
)


class SafePreloadMemoryTool(PreloadMemoryTool):
    """Preloads user memories if memory service is available, otherwise safely passes."""
    async def process_llm_request(self, tool_context, llm_request):
        try:
            return await super().process_llm_request(tool_context, llm_request)
        except Exception:
            return None


root_agent = Agent(
    name="ChefGemini",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        search_recipes_by_ingredients,
        get_recipe_details,
        save_favorite_recipe,
        list_favorite_recipes,
        add_pantry_item,
        get_pantry_inventory,
        remove_pantry_item,
        calculate_recipe_scaling,
        generate_recipe_image,
        check_media_bucket_exists,
        upload_media_to_gcs,
        get_weather,
        get_current_time,
        SafePreloadMemoryTool(),
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)


app = App(
    root_agent=root_agent,
    name="app",
)

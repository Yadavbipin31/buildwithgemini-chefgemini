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
import os
import re
import uuid
from typing import Any, Dict, List, Optional
from google.cloud import firestore

_db_client: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    """Returns a singleton Firestore client instance using ADC and GCP config."""
    global _db_client
    if _db_client is None:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        if project_id and not project_id.isdigit():
            _db_client = firestore.Client(project=project_id)
        else:
            _db_client = firestore.Client()
    return _db_client


def save_favorite_recipe(
    name: str,
    description: str,
    ingredients: List[str],
    instructions: List[str],
    prep_time: str = "",
    cook_time: str = "",
    servings: int = 1,
    dietary_tags: Optional[List[str]] = None,
    recipe_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Saves a favorite recipe to the 'favorites' collection in Firestore.

    Args:
        name: Name of the recipe (e.g., 'Spaghetti Carbonara').
        description: Brief description of the recipe.
        ingredients: List of ingredients with quantities.
        instructions: Step-by-step cooking instructions.
        prep_time: Preparation time (e.g., '15 mins').
        cook_time: Cooking time (e.g., '20 mins').
        servings: Number of servings.
        dietary_tags: Optional list of dietary tags (e.g., ['vegetarian', 'gluten-free']).
        recipe_id: Optional unique recipe identifier. Generated if not provided.

    Returns:
        A dictionary with status and saved recipe details.
    """
    try:
        db = get_firestore_client()
        
        if not recipe_id:
            # Generate clean slug from name or UUID fallback
            clean_name = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
            recipe_id = clean_name if clean_name else f"recipe_{uuid.uuid4().hex[:8]}"

        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        recipe_data = {
            "recipe_id": recipe_id,
            "name": name,
            "description": description,
            "ingredients": ingredients,
            "instructions": instructions,
            "prep_time": prep_time,
            "cook_time": cook_time,
            "servings": servings,
            "dietary_tags": dietary_tags or [],
            "created_at": created_at,
        }

        doc_ref = db.collection("favorites").document(recipe_id)
        doc_ref.set(recipe_data)

        return {
            "status": "success",
            "message": f"Recipe '{name}' saved to favorites with ID '{recipe_id}'.",
            "recipe": recipe_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to save favorite recipe: {str(e)}",
        }


def get_favorite_recipes(
    recipe_id: Optional[str] = None,
    name_query: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves saved favorite recipes from the 'favorites' collection in Firestore.

    Args:
        recipe_id: Optional specific recipe ID to fetch.
        name_query: Optional search keyword to filter recipes by name (case-insensitive).

    Returns:
        A dictionary with status and list of retrieved favorite recipes.
    """
    try:
        db = get_firestore_client()
        collection_ref = db.collection("favorites")

        if recipe_id:
            doc = collection_ref.document(recipe_id).get()
            if doc.exists:
                return {
                    "status": "success",
                    "recipes": [doc.to_dict()],
                }
            return {
                "status": "success",
                "message": f"No favorite recipe found with ID '{recipe_id}'.",
                "recipes": [],
            }

        docs = collection_ref.stream()
        recipes = []
        for doc in docs:
            data = doc.to_dict()
            if name_query:
                if name_query.lower() in data.get("name", "").lower():
                    recipes.append(data)
            else:
                recipes.append(data)

        return {
            "status": "success",
            "count": len(recipes),
            "recipes": recipes,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve favorite recipes: {str(e)}",
            "recipes": [],
        }


def add_pantry_item(
    item_name: str,
    quantity: str = "",
    category: str = "general",
) -> Dict[str, Any]:
    """Adds or updates an ingredient in the user's Firestore pantry inventory.

    Args:
        item_name: Name of the pantry item (e.g., 'Olive Oil', 'Garlic', 'Spaghetti').
        quantity: Optional quantity or amount (e.g., '2 bottles', '1 lb', '5 cloves').
        category: Optional food category (e.g., 'produce', 'spices', 'oils', 'pasta').

    Returns:
        A dictionary with status and details of the saved pantry item.
    """
    try:
        db = get_firestore_client()
        clean_id = re.sub(r"[^a-zA-Z0-9]+", "_", item_name.strip().lower()).strip("_")
        if not clean_id:
            clean_id = f"item_{uuid.uuid4().hex[:8]}"

        updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        item_data = {
            "item_id": clean_id,
            "item_name": item_name.strip(),
            "quantity": quantity.strip(),
            "category": category.strip().lower() or "general",
            "updated_at": updated_at,
        }

        doc_ref = db.collection("pantry").document(clean_id)
        doc_ref.set(item_data)

        return {
            "status": "success",
            "message": f"Added/updated '{item_name}' in pantry inventory.",
            "item": item_data,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to add pantry item: {str(e)}",
        }


def get_pantry_inventory(
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves all ingredients currently stored in the user's Firestore pantry inventory.

    Args:
        category: Optional category filter (e.g., 'produce', 'spices').

    Returns:
        A dictionary with status, item count, and list of pantry items.
    """
    try:
        db = get_firestore_client()
        collection_ref = db.collection("pantry")
        docs = collection_ref.stream()

        items = []
        for doc in docs:
            data = doc.to_dict()
            if category:
                if data.get("category", "").lower() == category.lower():
                    items.append(data)
            else:
                items.append(data)

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve pantry inventory: {str(e)}",
            "items": [],
        }


def remove_pantry_item(
    item_name: str,
) -> Dict[str, Any]:
    """Removes an ingredient from the user's Firestore pantry inventory.

    Args:
        item_name: Name of the pantry item to remove (e.g., 'Olive Oil').

    Returns:
        A dictionary with status and message.
    """
    try:
        db = get_firestore_client()
        clean_id = re.sub(r"[^a-zA-Z0-9]+", "_", item_name.strip().lower()).strip("_")
        
        doc_ref = db.collection("pantry").document(clean_id)
        doc_ref.delete()

        return {
            "status": "success",
            "message": f"Removed '{item_name}' from pantry inventory.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to remove pantry item: {str(e)}",
        }


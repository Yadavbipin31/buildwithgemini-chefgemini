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

import asyncio
import os
import re
from typing import Any, Dict, List, Optional
import aiohttp
from dotenv import load_dotenv

from .firestore_tools import get_favorite_recipes, save_favorite_recipe

load_dotenv()

# Curated local recipe database for fallback & offline development
CURATED_RECIPES: List[Dict[str, Any]] = [
    {
        "recipe_id": "garlic_butter_pasta",
        "name": "Garlic Butter Pasta",
        "description": "A comforting, quick pasta dish tossed with roasted garlic, butter, parmesan, and fresh herbs.",
        "ingredients": [
            "8 oz spaghetti or linguine",
            "4 cloves garlic, minced",
            "3 tbsp unsalted butter",
            "1 tbsp olive oil",
            "1/2 cup grated parmesan cheese",
            "2 tbsp fresh parsley, chopped",
            "Salt and black pepper to taste",
        ],
        "instructions": [
            "Boil spaghetti in salted water until al dente, reserving 1/2 cup pasta water.",
            "Melt butter with olive oil in a skillet over medium heat.",
            "Add minced garlic and sauté for 1-2 minutes until fragrant and lightly golden.",
            "Toss cooked pasta into the skillet along with reserved pasta water and parmesan cheese.",
            "Garnish with chopped parsley and fresh ground black pepper before serving.",
        ],
        "prep_time": "5 mins",
        "cook_time": "12 mins",
        "servings": 2,
        "dietary_tags": ["vegetarian", "quick"],
    },
    {
        "recipe_id": "mediterranean_chickpea_salad",
        "name": "Mediterranean Chickpea Salad",
        "description": "A vibrant, refreshing salad loaded with chickpeas, crisp cucumbers, tomatoes, feta, and lemon dressing.",
        "ingredients": [
            "1 can (15 oz) chickpeas, rinsed and drained",
            "1 cup English cucumber, diced",
            "1 cup cherry tomatoes, halved",
            "1/4 cup red onion, finely chopped",
            "1/2 cup crumbled feta cheese",
            "2 tbsp olive oil",
            "1 tbsp fresh lemon juice",
            "1 tsp dried oregano",
            "Salt and pepper to taste",
        ],
        "instructions": [
            "In a large bowl, combine chickpeas, cucumber, cherry tomatoes, and red onion.",
            "Whisk olive oil, lemon juice, dried oregano, salt, and pepper in a small bowl.",
            "Pour dressing over the salad and toss gently.",
            "Top with crumbled feta cheese and serve chilled.",
        ],
        "prep_time": "10 mins",
        "cook_time": "0 mins",
        "servings": 3,
        "dietary_tags": ["vegetarian", "gluten-free", "healthy", "quick"],
    },
    {
        "recipe_id": "spinach_feta_omelette",
        "name": "Spinach & Feta Omelette",
        "description": "A protein-packed fluffy omelette filled with fresh baby spinach, feta cheese, and garlic.",
        "ingredients": [
            "3 large eggs",
            "1 cup fresh baby spinach",
            "2 tbsp feta cheese, crumbled",
            "1 tbsp olive oil or butter",
            "1/2 tsp garlic powder",
            "Salt and pepper to taste",
        ],
        "instructions": [
            "Whisk eggs with a splash of water, salt, and pepper in a bowl.",
            "Heat olive oil in a non-stick skillet over medium heat.",
            "Add spinach and cook for 1 minute until wilted.",
            "Pour whisked eggs into the pan, cooking until set.",
            "Sprinkle crumbled feta over half of the omelette, fold over, and cook for another 30 seconds.",
        ],
        "prep_time": "5 mins",
        "cook_time": "5 mins",
        "servings": 1,
        "dietary_tags": ["vegetarian", "gluten-free", "keto", "quick", "breakfast"],
    },
    {
        "recipe_id": "creamy_tomato_basil_soup",
        "name": "Creamy Tomato Basil Soup",
        "description": "A velvety rich tomato soup infused with garlic, fresh basil, and a touch of heavy cream.",
        "ingredients": [
            "1 can (28 oz) crushed tomatoes",
            "2 tbsp butter",
            "1 small yellow onion, chopped",
            "2 cloves garlic, minced",
            "2 cups vegetable broth",
            "1/4 cup heavy cream or coconut milk",
            "1/4 cup fresh basil leaves",
            "Salt and black pepper to taste",
        ],
        "instructions": [
            "Melt butter in a pot over medium heat and sauté onion and garlic until soft.",
            "Add crushed tomatoes and vegetable broth; bring to a gentle simmer for 15 minutes.",
            "Blend soup with an immersion blender or blender until smooth.",
            "Stir in heavy cream and fresh basil leaves, seasoning with salt and pepper.",
        ],
        "prep_time": "10 mins",
        "cook_time": "20 mins",
        "servings": 4,
        "dietary_tags": ["vegetarian", "gluten-free"],
    },
    {
        "recipe_id": "avocado_chickpea_toast",
        "name": "Avocado Chickpea Mash Toast",
        "description": "Crispy toasted sourdough topped with mashed ripe avocado, seasoned chickpeas, and chili flakes.",
        "ingredients": [
            "2 slices sourdough bread",
            "1 ripe avocado",
            "1/2 cup canned chickpeas, rinsed",
            "1 tbsp lemon juice",
            "1/4 tsp red chili flakes",
            "Salt and black pepper to taste",
        ],
        "instructions": [
            "Toast sourdough bread slices until golden crisp.",
            "In a bowl, mash avocado and chickpeas together with lemon juice, salt, and pepper.",
            "Spread the avocado-chickpea mixture generously onto the toasted bread.",
            "Garnish with red chili flakes and extra olive oil drizzle if desired.",
        ],
        "prep_time": "5 mins",
        "cook_time": "3 mins",
        "servings": 2,
        "dietary_tags": ["vegan", "vegetarian", "healthy", "quick"],
    },
]


def _get_mealdb_base_url() -> str:
    """Returns base API URL for TheMealDB from environment."""
    return os.environ.get(
        "THEMEALDB_API_BASE_URL", "https://www.themealdb.com/api/json/v1/1"
    )


def _normalize_mealdb_meal(meal: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes raw meal dictionary from TheMealDB into ChefGemini standard recipe schema."""
    ingredients = []
    for i in range(1, 21):
        ing = meal.get(f"strIngredient{i}")
        measure = meal.get(f"strMeasure{i}")
        if ing and ing.strip():
            formatted = f"{measure.strip()} {ing.strip()}".strip() if measure else ing.strip()
            ingredients.append(formatted)

    raw_instructions = meal.get("strInstructions", "") or ""
    instructions = [
        step.strip()
        for step in re.split(r"\r?\n+", raw_instructions)
        if step.strip()
    ]

    tags = []
    category = meal.get("strCategory")
    if category:
        tags.append(category.lower())
    if category and category.lower() in ["vegetarian", "vegan", "seafood", "pasta", "dessert"]:
        tags.append(category.lower())

    raw_tags = meal.get("strTags")
    if raw_tags:
        for t in raw_tags.split(","):
            if t.strip():
                tags.append(t.strip().lower())

    area = meal.get("strArea", "")
    description = f"A delicious {area} {category or 'dish'}." if area else f"A delicious {category or 'dish'}."

    return {
        "recipe_id": str(meal.get("idMeal", "")),
        "name": meal.get("strMeal", "Untitled Recipe"),
        "description": description,
        "ingredients": ingredients,
        "instructions": instructions,
        "prep_time": "10 mins",
        "cook_time": "20 mins",
        "servings": 4,
        "dietary_tags": list(set(tags)),
        "image_url": meal.get("strMealThumb", ""),
    }


def _search_curated_recipes(
    ingredients: List[str],
    dietary_constraints: Optional[List[str]] = None,
    max_results: int = 5,
) -> Dict[str, Any]:
    """Searches local CURATED_RECIPES dataset as fallback."""
    user_ings = [ing.strip().lower() for ing in ingredients if ing.strip()]
    user_dietary = [tag.strip().lower() for tag in (dietary_constraints or []) if tag.strip()]

    matched_candidates = []

    for recipe in CURATED_RECIPES:
        recipe_tags = [tag.lower() for tag in recipe.get("dietary_tags", [])]
        if user_dietary and not all(diet in recipe_tags for diet in user_dietary):
            continue

        recipe_ings_flat = " ".join(recipe.get("ingredients", [])).lower()
        matching_ings = [
            user_ing for user_ing in user_ings if user_ing in recipe_ings_flat
        ]

        matched_candidates.append({
            "recipe_id": recipe["recipe_id"],
            "name": recipe["name"],
            "description": recipe["description"],
            "prep_time": recipe["prep_time"],
            "cook_time": recipe["cook_time"],
            "servings": recipe["servings"],
            "dietary_tags": recipe["dietary_tags"],
            "matched_ingredients": matching_ings,
            "total_ingredients_count": len(recipe["ingredients"]),
            "match_score": len(matching_ings),
        })

    matched_candidates.sort(key=lambda x: x["match_score"], reverse=True)
    results = matched_candidates[:max_results]

    return {
        "status": "success",
        "source": "curated_catalog",
        "query_ingredients": ingredients,
        "dietary_constraints": dietary_constraints or [],
        "count": len(results),
        "recipes": results,
    }


async def search_recipes_by_ingredients(
    ingredients: List[str],
    dietary_constraints: Optional[List[str]] = None,
    max_results: int = 5,
    force_fallback: bool = False,
) -> Dict[str, Any]:
    """Searches for recipes based on user ingredients and dietary constraints, using TheMealDB API with local fallback.

    Args:
        ingredients: List of available user ingredients (e.g. ['chicken', 'garlic']).
        dietary_constraints: Optional list of dietary requirements (e.g. ['vegetarian']).
        max_results: Maximum recipe candidates to return.
        force_fallback: If True, skips external API and uses local CURATED_RECIPES fallback.

    Returns:
        A dictionary with search status, source ('themealdb' or 'curated_catalog'), and matching recipes.
    """
    if force_fallback or not ingredients:
        return _search_curated_recipes(ingredients, dietary_constraints, max_results)

    base_url = _get_mealdb_base_url()
    primary_ingredient = ingredients[0].strip().replace(" ", "_")

    try:
        timeout = aiohttp.ClientTimeout(total=5.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            filter_url = f"{base_url}/filter.php?i={primary_ingredient}"
            async with session.get(filter_url) as resp:
                if resp.status != 200:
                    return _search_curated_recipes(ingredients, dietary_constraints, max_results)

                data = await resp.json()
                meals = data.get("meals")
                if not meals:
                    return _search_curated_recipes(ingredients, dietary_constraints, max_results)

                # Fetch full recipe details for top matching meals
                detail_tasks = []
                for meal in meals[:max_results]:
                    meal_id = meal.get("idMeal")
                    if meal_id:
                        lookup_url = f"{base_url}/lookup.php?i={meal_id}"
                        detail_tasks.append(session.get(lookup_url))

                responses = await asyncio.gather(*detail_tasks, return_exceptions=True)

                normalized_recipes = []
                user_dietary = [tag.strip().lower() for tag in (dietary_constraints or []) if tag.strip()]

                for res in responses:
                    if isinstance(res, Exception) or res.status != 200:
                        continue
                    detail_data = await res.json()
                    detail_meals = detail_data.get("meals")
                    if detail_meals:
                        norm_recipe = _normalize_mealdb_meal(detail_meals[0])
                        
                        # Apply dietary constraints if specified
                        if user_dietary:
                            recipe_tags = [t.lower() for t in norm_recipe.get("dietary_tags", [])]
                            if not all(diet in recipe_tags for diet in user_dietary):
                                continue

                        normalized_recipes.append(norm_recipe)

                if not normalized_recipes:
                    return _search_curated_recipes(ingredients, dietary_constraints, max_results)

                return {
                    "status": "success",
                    "source": "themealdb",
                    "query_ingredients": ingredients,
                    "dietary_constraints": dietary_constraints or [],
                    "count": len(normalized_recipes),
                    "recipes": normalized_recipes,
                }
    except Exception:
        # Seamless error handling fallback
        return _search_curated_recipes(ingredients, dietary_constraints, max_results)


async def get_recipe_details(
    recipe_id_or_name: str,
) -> Dict[str, Any]:
    """Retrieves full details for a recipe from local catalog, Firestore favorites, or TheMealDB API.

    Args:
        recipe_id_or_name: Recipe identifier or name (e.g. '52772', 'garlic_butter_pasta', 'Arrabiata').

    Returns:
        A dictionary containing recipe status, data source, and recipe details.
    """
    try:
        query_str = recipe_id_or_name.strip().lower()

        # 1. Search local curated catalog
        for recipe in CURATED_RECIPES:
            if recipe["recipe_id"].lower() == query_str or query_str in recipe["name"].lower():
                return {
                    "status": "success",
                    "source": "curated_catalog",
                    "recipe": recipe,
                }

        # 2. Search Firestore favorites
        favorites = get_favorite_recipes(name_query=recipe_id_or_name)
        if favorites.get("status") == "success" and favorites.get("recipes"):
            return {
                "status": "success",
                "source": "firestore_favorites",
                "recipe": favorites["recipes"][0],
            }

        # 3. Query TheMealDB API
        base_url = _get_mealdb_base_url()
        timeout = aiohttp.ClientTimeout(total=5.0)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            if query_str.isdigit():
                url = f"{base_url}/lookup.php?i={query_str}"
            else:
                url = f"{base_url}/search.php?s={recipe_id_or_name.strip()}"

            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    meals = data.get("meals")
                    if meals:
                        norm_recipe = _normalize_mealdb_meal(meals[0])
                        return {
                            "status": "success",
                            "source": "themealdb",
                            "recipe": norm_recipe,
                        }

        return {
            "status": "not_found",
            "message": f"No recipe found matching '{recipe_id_or_name}'.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get recipe details: {str(e)}",
        }


def list_favorite_recipes(
    name_query: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves all saved favorite recipes from the user's Firestore favorites collection.

    Args:
        name_query: Optional search keyword to filter saved favorite recipes by name.

    Returns:
        A dictionary with status, count, and list of saved favorite recipes.
    """
    return get_favorite_recipes(name_query=name_query)


__all__ = [
    "search_recipes_by_ingredients",
    "get_recipe_details",
    "save_favorite_recipe",
    "list_favorite_recipes",
]

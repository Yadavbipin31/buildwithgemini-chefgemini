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

from fractions import Fraction
import math
import re
from typing import Any, Dict, List, Optional, Tuple


def _parse_numeric_quantity(q_str: str) -> Optional[Fraction]:
    """Parses integers, decimals, simple fractions (1/2), or mixed fractions (1 1/2) into a Fraction."""
    q_str = q_str.strip()
    try:
        if " " in q_str and "/" in q_str:
            parts = q_str.split()
            whole = int(parts[0])
            num, denom = map(int, parts[1].split("/"))
            if denom == 0:
                return None
            return Fraction(whole * denom + num, denom)
        elif "/" in q_str:
            num, denom = map(int, q_str.split("/"))
            if denom == 0:
                return None
            return Fraction(num, denom)
        else:
            val = float(q_str)
            return Fraction(val).limit_denominator(1000)
    except (ValueError, ArithmeticError):
        return None


def _format_quantity(q: Fraction) -> str:
    """Formats a Fraction into a human-readable quantity string (e.g. '1', '1 1/2', '0.5')."""
    if q.denominator == 1:
        return str(q.numerator)
    whole = q.numerator // q.denominator
    rem = q.numerator % q.denominator
    if whole == 0:
        return f"{rem}/{q.denominator}"
    else:
        return f"{whole} {rem}/{q.denominator}"


def _convert_units(q: Fraction, unit: str) -> Tuple[Fraction, str]:
    """Applies dimensionally safe unit conversions (volume-to-volume, weight-to-weight only)."""
    if not unit:
        return q, unit

    unit_clean = unit.strip().lower()

    # Volume Conversions (strictly volume)
    if unit_clean in ["tsp", "teaspoon", "teaspoons"]:
        if q >= 3 and q % 3 == 0:
            converted = q / 3
            return converted, "tbsp"
    elif unit_clean in ["tbsp", "tablespoon", "tablespoons"]:
        if q >= 16 and q % 16 == 0:
            converted = q / 16
            return converted, "cup" if converted == 1 else "cups"
    elif unit_clean in ["ml", "milliliter", "milliliters"]:
        if q >= 1000 and q % 1000 == 0:
            converted = q / 1000
            return converted, "l"

    # Weight Conversions (strictly weight - treat 'oz' as weight oz only)
    elif unit_clean in ["oz", "ounce", "ounces"]:
        if q >= 16 and q % 16 == 0:
            converted = q / 16
            return converted, "lb" if converted == 1 else "lbs"
    elif unit_clean in ["g", "gram", "grams"]:
        if q >= 1000 and q % 1000 == 0:
            converted = q / 1000
            return converted, "kg"

    # Discrete, unknown, or non-convertible units remain unchanged
    return q, unit


_QUANTITY_REGEX = re.compile(
    r"^\s*(?P<quantity>\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)?\s*(?P<item>.+)?$"
)


def calculate_recipe_scaling(
    ingredients: List[str],
    original_servings: float,
    target_servings: float,
) -> Dict[str, Any]:
    """Scales ingredient quantities from original servings to target servings and performs dimensionally safe unit conversions using deterministic arithmetic.

    Args:
        ingredients: List of ingredient strings with quantities (e.g. ['8 oz spaghetti', '4 cloves garlic', '2 tbsp olive oil']).
        original_servings: Original recipe serving count (must be > 0).
        target_servings: Desired target serving count (must be > 0).

    Returns:
        A dictionary containing scaling status, scale_factor, original_servings, target_servings, and scaled_ingredients list.
    """
    if not isinstance(ingredients, list):
        return {
            "status": "error",
            "message": "Ingredients must be provided as a list of strings.",
        }

    if original_servings <= 0 or target_servings <= 0:
        return {
            "status": "error",
            "message": "Original and target servings must be positive numbers greater than 0.",
        }

    scale_factor = target_servings / original_servings
    scale_fraction = Fraction(target_servings) / Fraction(original_servings)

    scaled_ingredients = []

    for ingredient in ingredients:
        if not isinstance(ingredient, str) or not ingredient.strip():
            continue

        ing_str = ingredient.strip()
        match = _QUANTITY_REGEX.match(ing_str)

        if not match:
            # Non-quantified or non-matching ingredient (e.g. "salt and pepper to taste")
            scaled_ingredients.append({
                "original": ing_str,
                "scaled": ing_str,
                "quantity": None,
                "unit": None,
                "item": ing_str,
            })
            continue

        raw_q = match.group("quantity")
        parsed_q = _parse_numeric_quantity(raw_q)

        if parsed_q is None:
            # Fallback if quantity couldn't be parsed safely
            scaled_ingredients.append({
                "original": ing_str,
                "scaled": ing_str,
                "quantity": None,
                "unit": None,
                "item": ing_str,
            })
            continue

        unit = match.group("unit") or ""
        item = (match.group("item") or "").strip()

        # Scale quantity exactly
        scaled_q_raw = parsed_q * scale_fraction

        # Apply dimensionally safe unit conversions
        conv_q, conv_unit = _convert_units(scaled_q_raw, unit)

        formatted_q = _format_quantity(conv_q)
        unit_part = f" {conv_unit}" if conv_unit else ""
        item_part = f" {item}" if item else ""

        scaled_str = f"{formatted_q}{unit_part}{item_part}".strip()

        scaled_ingredients.append({
            "original": ing_str,
            "scaled": scaled_str,
            "quantity": float(conv_q),
            "unit": conv_unit if conv_unit else None,
            "item": item if item else None,
        })

    return {
        "status": "success",
        "original_servings": original_servings,
        "target_servings": target_servings,
        "scale_factor": scale_factor,
        "scaled_ingredients": scaled_ingredients,
    }


__all__ = ["calculate_recipe_scaling"]

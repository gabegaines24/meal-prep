import json
import os
from datetime import date

import resend as resend_sdk

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _api_key() -> str:
    key = os.getenv("RESEND_API_KEY", "")
    if not key:
        raise RuntimeError("RESEND_API_KEY is not set")
    return key


def _recipient() -> str:
    email = os.getenv("EMAIL_RECIPIENT", "")
    if not email:
        raise RuntimeError("EMAIL_RECIPIENT is not set")
    return email


def _build_shopping_list(slots: list) -> list[str]:
    """Aggregate all ingredients across a week's meal slots, de-duplicated."""
    seen: set[str] = set()
    items: list[str] = []
    for slot in slots:
        if slot.recipe and slot.recipe.ingredients_json:
            try:
                ingredients = json.loads(slot.recipe.ingredients_json)
                for item in ingredients:
                    key = item.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        items.append(item)
            except json.JSONDecodeError:
                pass
    return sorted(items)


def _render_html(week_start: date, slots: list, weekly_macros: dict) -> str:
    rows = ""
    for day_idx in range(7):
        day_name = DAYS[day_idx]
        day_slots = [s for s in slots if s.day_of_week == day_idx]
        for meal_type in ("breakfast", "lunch", "dinner"):
            slot = next((s for s in day_slots if s.meal_type == meal_type), None)
            recipe_name = slot.recipe.title if slot and slot.recipe else "—"
            rows += f"<tr><td>{day_name}</td><td>{meal_type.capitalize()}</td><td>{recipe_name}</td></tr>\n"

    shopping = _build_shopping_list(slots)
    shopping_html = "".join(f"<li>{item}</li>" for item in shopping)

    return f"""
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 640px; margin: auto; color: #333; }}
    h1 {{ color: #2d6a4f; }}
    h2 {{ color: #40916c; border-bottom: 1px solid #eee; padding-bottom: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
    th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #eee; }}
    th {{ background: #f0f4f1; }}
    .macros {{ background: #f9f9f9; padding: 12px 16px; border-radius: 6px; margin-bottom: 24px; }}
    ul {{ padding-left: 20px; columns: 2; }}
  </style>
</head>
<body>
  <h1>Meal Plan — Week of {week_start.strftime("%B %d, %Y")}</h1>

  <h2>Meal Schedule</h2>
  <table>
    <thead><tr><th>Day</th><th>Meal</th><th>Recipe</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Weekly Macro Summary</h2>
  <div class="macros">
    <strong>Calories:</strong> {weekly_macros.get('calories', 0):.0f} kcal &nbsp;|&nbsp;
    <strong>Protein:</strong> {weekly_macros.get('protein', 0):.0f} g &nbsp;|&nbsp;
    <strong>Carbs:</strong> {weekly_macros.get('carbs', 0):.0f} g &nbsp;|&nbsp;
    <strong>Fat:</strong> {weekly_macros.get('fat', 0):.0f} g
  </div>

  <h2>Shopping List</h2>
  <ul>{shopping_html}</ul>
</body>
</html>
"""


def send_digest(week_start: date, slots: list, weekly_macros: dict) -> dict:
    resend_sdk.api_key = _api_key()
    recipient = _recipient()
    html = _render_html(week_start, slots, weekly_macros)

    return resend_sdk.Emails.send({
        "from": "Meal Planner <onboarding@resend.dev>",
        "to": [recipient],
        "subject": f"Your Meal Plan — Week of {week_start.strftime('%B %d, %Y')}",
        "html": html,
    })

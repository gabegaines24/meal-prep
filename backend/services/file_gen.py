"""
Generates standalone HTML documents for a given week's meal plan:

  grocery_list_html()  — printable ingredient checklist
  recipe_book_html()   — full recipes with macros and step-by-step instructions
"""

import json
from datetime import date

from backend.services.grocery import build_grocery_list

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_BASE_STYLE = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
         max-width: 760px; margin: 40px auto; padding: 0 24px; color: #1a1a1a; }
  h1 { font-size: 1.8rem; color: #2d6a4f; margin-bottom: 6px; }
  h2 { font-size: 1.2rem; color: #40916c; border-bottom: 2px solid #d8f3dc;
       padding-bottom: 6px; margin: 32px 0 12px; }
  h3 { font-size: 1rem; color: #333; margin: 20px 0 6px; }
  p.sub { color: #666; font-size: 0.9rem; margin-bottom: 24px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
  th { background: #d8f3dc; text-align: left; padding: 8px 10px; font-size: 0.85rem; }
  td { padding: 7px 10px; border-bottom: 1px solid #f0f0f0; font-size: 0.9rem; }
  tr:last-child td { border-bottom: none; }
  .macro-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px;
                margin: 8px 0 16px; }
  .macro-cell { background: #f6fef9; border: 1px solid #d8f3dc; border-radius: 6px;
                padding: 8px; text-align: center; }
  .macro-cell .val { font-size: 1.1rem; font-weight: 700; color: #2d6a4f; }
  .macro-cell .lbl { font-size: 0.7rem; color: #666; margin-top: 2px; }
  ol.steps { padding-left: 20px; }
  ol.steps li { margin-bottom: 8px; font-size: 0.9rem; line-height: 1.5; }
  .recipe-img { width: 100%; max-height: 220px; object-fit: cover;
                border-radius: 8px; margin-bottom: 12px; }
  .page-break { page-break-after: always; }
  @media print { body { margin: 20px; } }
</style>
"""


def grocery_list_html(week_start: date, slots: list) -> str:
    """Generate a printable grocery list HTML document."""
    data = build_grocery_list(week_start, slots)
    sections = ""

    for category in data["categories"]:
        rows = "".join(
            f"<tr><td>☐ {item['name']}</td>"
            f"<td style='color:#888;font-size:.8rem'>{', '.join(item['recipes'])}</td></tr>\n"
            for item in category["items"]
        )
        sections += f"""
        <h2>{category['name']}</h2>
        <table>
          <thead><tr><th>Ingredient</th><th>Used in</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        """

    if not sections:
        sections = "<p>No ingredients found. Assign recipes with ingredient data first.</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Grocery List — {week_start.strftime('%B %d, %Y')}</title>
{_BASE_STYLE}
</head>
<body>
  <h1>Grocery List</h1>
  <p class="sub">Week of {week_start.strftime('%B %d, %Y')} · {len(data['items'])} items</p>
  {sections}
</body>
</html>"""


def recipe_book_html(week_start: date, slots: list) -> str:
    """Generate the recipe book HTML document."""
    seen_ids: set[int] = set()
    unique_recipes = []
    for slot in slots:
        if slot.recipe and slot.recipe.id not in seen_ids:
            seen_ids.add(slot.recipe.id)
            unique_recipes.append(slot.recipe)

    if not unique_recipes:
        return f"""<!DOCTYPE html><html><body>
        <h1>Recipe Book — Week of {week_start.strftime('%B %d, %Y')}</h1>
        <p>No recipes planned for this week.</p></body></html>"""

    sections = ""
    for i, recipe in enumerate(unique_recipes):
        def m(v): return f"{v:.0f}" if v is not None else "—"
        macros = f"""
        <div class="macro-grid">
          <div class="macro-cell"><div class="val">{m(recipe.calories)}</div><div class="lbl">Calories</div></div>
          <div class="macro-cell"><div class="val">{m(recipe.protein)}g</div><div class="lbl">Protein</div></div>
          <div class="macro-cell"><div class="val">{m(recipe.carbs)}g</div><div class="lbl">Carbs</div></div>
          <div class="macro-cell"><div class="val">{m(recipe.fat)}g</div><div class="lbl">Fat</div></div>
        </div>"""

        ingredients: list[str] = []
        if recipe.ingredients_json:
            try:
                ingredients = json.loads(recipe.ingredients_json)
            except json.JSONDecodeError:
                pass
        ing_rows = "".join(f"<tr><td>• {ing}</td></tr>" for ing in ingredients)
        ing_table = f"<table><tbody>{ing_rows}</tbody></table>" if ing_rows else "<p>—</p>"

        steps: list[str] = []
        if recipe.instructions_json:
            try:
                steps = json.loads(recipe.instructions_json)
            except json.JSONDecodeError:
                pass
        if steps:
            steps_html = "<ol class='steps'>" + "".join(f"<li>{s}</li>" for s in steps) + "</ol>"
        elif recipe.source_url:
            steps_html = f'<p>Full instructions at: <a href="{recipe.source_url}">{recipe.source_url}</a></p>'
        else:
            steps_html = "<p>Instructions not available.</p>"

        img_html = (
            f'<img class="recipe-img" src="{recipe.image_url}" alt="{recipe.title}">'
            if recipe.image_url else ""
        )
        page_break = '<div class="page-break"></div>' if i < len(unique_recipes) - 1 else ""

        sections += f"""
        <section>
          {img_html}
          <h2>{recipe.title}</h2>
          {macros}
          <h3>Ingredients</h3>
          {ing_table}
          <h3>Instructions</h3>
          {steps_html}
        </section>
        {page_break}
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Recipe Book — {week_start.strftime('%B %d, %Y')}</title>
{_BASE_STYLE}
</head>
<body>
  <h1>Recipe Book</h1>
  <p class="sub">Week of {week_start.strftime('%B %d, %Y')} · {len(unique_recipes)} recipes</p>
  {sections}
</body>
</html>"""

"""
Generates two standalone HTML documents for a given week's meal plan:

  grocery_list_html()  — itemised shopping list with Kroger prices and budget summary
  recipe_book_html()   — full recipes with macros and step-by-step instructions
"""

import json
from datetime import date

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
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
           font-size: 0.75rem; font-weight: 600; }
  .green { background: #d8f3dc; color: #1b4332; }
  .red   { background: #ffe0e0; color: #7f1d1d; }
  .total-row td { font-weight: 700; background: #f6fef9; }
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


def _dedup_ingredients(slots: list) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for slot in slots:
        if slot.recipe and slot.recipe.ingredients_json:
            try:
                for ing in json.loads(slot.recipe.ingredients_json):
                    key = ing.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        items.append(ing)
            except json.JSONDecodeError:
                pass
    return sorted(items)


def grocery_list_html(
    week_start: date,
    slots: list,
    store_name: str = "",
    weekly_budget: float = 0.0,
    ingredient_prices: dict | None = None,
) -> str:
    """
    Generate the grocery list HTML document.

    ingredient_prices: optional dict mapping ingredient string → float (USD) from Kroger.
    """
    prices = ingredient_prices or {}
    ingredients = _dedup_ingredients(slots)

    rows = ""
    total_known = 0.0
    for ing in ingredients:
        price = prices.get(ing)
        if price is not None:
            total_known += price
            price_cell = f"${price:.2f}"
        else:
            price_cell = "—"
        rows += f"<tr><td>☐ {ing}</td><td style='text-align:right'>{price_cell}</td></tr>\n"

    budget_html = ""
    if weekly_budget > 0 and total_known > 0:
        over = total_known > weekly_budget
        cls = "red" if over else "green"
        label = "Over budget" if over else "Within budget"
        budget_html = f"""
        <h2>Budget Summary</h2>
        <table>
          <tr><td>Estimated total</td><td style='text-align:right'><strong>${total_known:.2f}</strong></td></tr>
          <tr><td>Weekly budget</td><td style='text-align:right'>${weekly_budget:.2f}</td></tr>
          <tr class='total-row'>
            <td>Status</td>
            <td style='text-align:right'><span class='badge {cls}'>{label}</span></td>
          </tr>
        </table>
        """

    store_line = f" · {store_name}" if store_name else ""
    price_note = " · Prices from Kroger" if prices else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Grocery List — {week_start.strftime('%B %d, %Y')}</title>
{_BASE_STYLE}
</head>
<body>
  <h1>Grocery List</h1>
  <p class="sub">Week of {week_start.strftime('%B %d, %Y')}{store_line}{price_note}</p>

  {budget_html}

  <h2>Items ({len(ingredients)})</h2>
  <table>
    <thead><tr><th>Ingredient</th><th style='text-align:right'>Est. Price</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
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
        # Macros
        def m(v): return f"{v:.0f}" if v is not None else "—"
        macros = f"""
        <div class="macro-grid">
          <div class="macro-cell"><div class="val">{m(recipe.calories)}</div><div class="lbl">Calories</div></div>
          <div class="macro-cell"><div class="val">{m(recipe.protein)}g</div><div class="lbl">Protein</div></div>
          <div class="macro-cell"><div class="val">{m(recipe.carbs)}g</div><div class="lbl">Carbs</div></div>
          <div class="macro-cell"><div class="val">{m(recipe.fat)}g</div><div class="lbl">Fat</div></div>
        </div>"""

        # Ingredients
        ingredients: list[str] = []
        if recipe.ingredients_json:
            try:
                ingredients = json.loads(recipe.ingredients_json)
            except json.JSONDecodeError:
                pass
        ing_rows = "".join(f"<tr><td>• {ing}</td></tr>" for ing in ingredients)
        ing_table = f"<table><tbody>{ing_rows}</tbody></table>" if ing_rows else "<p>—</p>"

        # Instructions
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

        img_html = f'<img class="recipe-img" src="{recipe.image_url}" alt="{recipe.title}">' if recipe.image_url else ""
        page_break = '<div class="page-break"></div>' if i < len(unique_recipes) - 1 else ""

        cost_html = f"<p style='color:#666;font-size:.85rem;margin-bottom:8px'>Est. cost: ${recipe.estimated_cost:.2f}</p>" if recipe.estimated_cost else ""

        sections += f"""
        <section>
          {img_html}
          <h2>{recipe.title}</h2>
          {cost_html}
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

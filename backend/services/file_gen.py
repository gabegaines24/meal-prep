"""
Generates standalone HTML documents for a given week's meal plan:

  grocery_list_html()  — printable ingredient checklist
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
  .red { background: #ffe0e0; color: #7f1d1d; }
  .total-row td { font-weight: 700; background: #f6fef9; }
  .footer-note { font-size: 0.8rem; color: #888; margin-top: 24px; }
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


def grocery_list_html(week_start: date, grocery_data: dict) -> str:
    """Generate a printable grocery list HTML document with optional pricing."""
    data = grocery_data
    budget = data.get("budget_summary", {})
    sections = ""

    if budget.get("budget", 0) > 0:
        over = budget.get("over_budget", False)
        cls = "red" if over else "green"
        label = "Over budget" if over else "Within budget"
        sections += f"""
        <h2>Budget Summary</h2>
        <table>
          <tr><td>Estimated total</td><td style='text-align:right'><strong>${budget.get('estimated_total', 0):.2f}</strong></td></tr>
          <tr><td>Weekly budget</td><td style='text-align:right'>${budget.get('budget', 0):.2f}</td></tr>
          <tr class='total-row'><td>Status</td><td style='text-align:right'><span class='badge {cls}'>{label}</span></td></tr>
        </table>
        """

    for category in data.get("categories", []):
        rows = ""
        for item in category["items"]:
            price_cell = f"${item['price']:.2f}" if item.get("price") is not None else "—"
            stale = " *" if item.get("stale") else ""
            rows += (
                f"<tr><td>☐ {item['name']}{stale}</td>"
                f"<td style='text-align:right'>{price_cell}</td>"
                f"<td style='color:#888;font-size:.8rem'>{', '.join(item['recipes'])}</td></tr>\n"
            )
        subtotal = ""
        if category.get("subtotal"):
            subtotal = f" · subtotal ${category['subtotal']:.2f}"
        sections += f"""
        <h2>{category['name']}{subtotal}</h2>
        <table>
          <thead><tr><th>Ingredient</th><th style='text-align:right'>Est. Price</th><th>Used in</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        """

    if not sections:
        sections = "<p>No ingredients found. Assign recipes with ingredient data first.</p>"

    store_line = ""
    zip_code = budget.get("zip_code") or ""
    if zip_code:
        store_line = f" · Estimated Walmart prices for ZIP {zip_code}"
    elif budget.get("store_name"):
        store_line = f" · {budget['store_name']}"
    prices_note = ""
    if budget.get("prices_as_of"):
        prices_note = f" · Prices as of {budget['prices_as_of'][:10]}"
        if budget.get("stale"):
            prices_note += " (estimated)"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Grocery List — {week_start.strftime('%B %d, %Y')}</title>
{_BASE_STYLE}
</head>
<body>
  <h1>Grocery List</h1>
  <p class="sub">Week of {week_start.strftime('%B %d, %Y')} · {len(data.get('items', []))} items{store_line}{prices_note}</p>
  {sections}
  <p class="footer-note">Estimated Walmart prices — verify in store before shopping. * Stale or fallback estimate.</p>
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

        cost_html = ""
        if getattr(recipe, "estimated_cost_per_serving", None) is not None:
            src = getattr(recipe, "price_source", None) or "estimated"
            cost_html = (
                f"<p style='color:#666;font-size:.85rem;margin-bottom:8px'>"
                f"Est. ${recipe.estimated_cost_per_serving:.2f}/serving ({src})</p>"
            )

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

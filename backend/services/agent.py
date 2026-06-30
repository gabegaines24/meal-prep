"""
Claude agent loop with tool-use for the meal planning copilot.

Each tool maps to an existing backend capability. The loop streams tokens and
tool events to the chat route via async generators.
"""

from __future__ import annotations

import json
import os
from datetime import date
from typing import AsyncIterator

import anthropic
from sqlalchemy.orm import Session

from backend.models.models import MacroGoals, MealPlan, MealType, Recipe, UserProfile
from backend.routes.meals import (
    DAYS,
    SlotIn,
    _compute_macro_gaps,
    _compute_macros,
    _monday,
    autogenerate,
    assign_slot,
    clear_slot,
)
from backend.routes.recipes import _load_filters, _to_out, _upsert_recipe
from backend.services import embeddings as embed_svc
from backend.services import spoonacular
from backend.services.grocery import build_grocery_list

MODEL = "claude-opus-4-5"
MAX_TOOL_ROUNDS = 8
MEMORY_CONDENSE_EVERY = 10

SYSTEM_PROMPT = """You are a helpful meal planning copilot for a personal nutrition app.

You help users plan weekly meals, hit macro goals, search recipes, build grocery lists,
and make substitutions. You have tools to read and modify their meal plan.

Guidelines:
- Use day numbers 0–6 (Monday=0 … Sunday=6) when calling plan tools.
- Prefer semantic recipe search for substitutions; use Spoonacular search for fresh ideas.
- Respect the user's diet type and allergens from get_profile before suggesting recipes.
- When you assign meals or autogenerate a week, briefly confirm what you did.
- Cite recipe titles when you retrieve them from search.
- Be concise and practical."""

DAY_ALIASES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

TOOLS: list[dict] = [
    {
        "name": "get_current_week",
        "description": "Get the current week's meal plan slots and macro totals.",
        "input_schema": {
            "type": "object",
            "properties": {
                "week_start": {
                    "type": "string",
                    "description": "Week start date YYYY-MM-DD (Monday). Omit for current week.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_macro_goals",
        "description": "Get daily macro targets (calories, protein, carbs, fat).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_recipes_semantic",
        "description": "Semantic search over cached recipes using natural language.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query."},
                "limit": {"type": "integer", "description": "Max results (default 6)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_recipes_spoonacular",
        "description": "Search Spoonacular for fresh recipe ideas (respects diet/allergens).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "assign_slot",
        "description": "Assign a recipe to a day and meal slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "day": {
                    "type": "integer",
                    "description": "Day of week 0–6 (Monday=0).",
                },
                "meal_type": {
                    "type": "string",
                    "enum": ["breakfast", "lunch", "dinner"],
                },
                "recipe_id": {"type": "integer", "description": "Cached recipe ID."},
                "week_start": {"type": "string", "description": "Optional week start YYYY-MM-DD."},
            },
            "required": ["day", "meal_type", "recipe_id"],
        },
    },
    {
        "name": "clear_slot",
        "description": "Clear a meal slot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "day": {"type": "integer"},
                "meal_type": {"type": "string", "enum": ["breakfast", "lunch", "dinner"]},
                "week_start": {"type": "string"},
            },
            "required": ["day", "meal_type"],
        },
    },
    {
        "name": "autogenerate_week",
        "description": "Fill empty slots for the week using macro goals (favorites-first).",
        "input_schema": {
            "type": "object",
            "properties": {
                "week_start": {"type": "string", "description": "Optional week start YYYY-MM-DD."},
            },
            "required": [],
        },
    },
    {
        "name": "get_grocery_list",
        "description": "Get the aggregated grocery list for the current week.",
        "input_schema": {
            "type": "object",
            "properties": {
                "week_start": {"type": "string"},
            },
            "required": [],
        },
    },
    {
        "name": "get_profile",
        "description": "Get user diet type and allergen list.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "search_documents",
        "description": "Search user-uploaded documents (recipes, notes) by meaning.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
]


def _client() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=key)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _slot_summary(slots: list[MealPlan]) -> list[dict]:
    rows = []
    for slot in slots:
        rows.append(
            {
                "day": slot.day_of_week,
                "day_name": DAYS[slot.day_of_week],
                "meal_type": slot.meal_type.value,
                "recipe_id": slot.recipe_id,
                "recipe_title": slot.recipe.title if slot.recipe else None,
                "calories": slot.recipe.calories if slot.recipe else None,
                "protein": slot.recipe.protein if slot.recipe else None,
            }
        )
    return rows


async def execute_tool(
    name: str,
    tool_input: dict,
    db: Session,
) -> tuple[dict, list[dict]]:
    """Run a tool and return (result_json, ui_events)."""
    ui_events: list[dict] = []

    if name == "get_current_week":
        start = _monday(_parse_date(tool_input.get("week_start")) or date.today())
        slots = db.query(MealPlan).filter(MealPlan.week_start_date == start).all()
        daily, weekly = _compute_macros(slots)
        goals = db.query(MacroGoals).filter(MacroGoals.id == 1).first()
        gaps = _compute_macro_gaps(weekly, goals) if goals else []
        return (
            {
                "week_start_date": str(start),
                "slots": _slot_summary(slots),
                "daily_macros": daily,
                "weekly_macros": weekly,
                "macro_gaps": [g.model_dump() for g in gaps],
            },
            ui_events,
        )

    if name == "get_macro_goals":
        goals = db.query(MacroGoals).filter(MacroGoals.id == 1).first()
        if not goals:
            goals = MacroGoals(id=1)
            db.add(goals)
            db.commit()
            db.refresh(goals)
        return (
            {
                "calories": goals.calories,
                "protein": goals.protein,
                "carbs": goals.carbs,
                "fat": goals.fat,
            },
            ui_events,
        )

    if name == "search_recipes_semantic":
        hits = embed_svc.query_recipes(
            tool_input["query"],
            n_results=int(tool_input.get("limit") or 6),
        )
        recipes = []
        for hit in hits:
            recipes.append(
                {
                    "recipe_id": hit.get("recipe_id"),
                    "title": hit.get("title"),
                    "calories": hit.get("calories"),
                    "protein": hit.get("protein"),
                    "carbs": hit.get("carbs"),
                    "fat": hit.get("fat"),
                    "favorited": hit.get("favorited"),
                    "distance": hit.get("distance"),
                }
            )
            ui_events.append(
                {
                    "type": "citation",
                    "recipe_id": hit.get("recipe_id"),
                    "title": hit.get("title"),
                }
            )
        return {"recipes": recipes}, ui_events

    if name == "search_recipes_spoonacular":
        diet, allergens = _load_filters(db)
        results = await spoonacular.search_recipes(
            tool_input["query"], diet=diet, intolerances=allergens
        )
        recipes = [_to_out(_upsert_recipe(db, r)).model_dump() for r in results]
        for r in recipes:
            ui_events.append(
                {"type": "citation", "recipe_id": r["id"], "title": r["title"]}
            )
        return {"recipes": recipes}, ui_events

    if name == "assign_slot":
        day = int(tool_input["day"])
        meal_type = MealType(tool_input["meal_type"])
        week_start = _parse_date(tool_input.get("week_start"))
        slot = await assign_slot(
            day=day,
            meal_type=meal_type,
            payload=SlotIn(recipe_id=int(tool_input["recipe_id"])),
            week_start=week_start,
            db=db,
        )
        title = slot.recipe.title if slot.recipe else "Recipe"
        ui_events.append(
            {
                "type": "action",
                "action": "assign_slot",
                "day": day,
                "day_name": DAYS[day],
                "meal_type": meal_type.value,
                "recipe_id": tool_input["recipe_id"],
                "recipe_title": title,
            }
        )
        return {
            "assigned": True,
            "day": day,
            "meal_type": meal_type.value,
            "recipe_id": tool_input["recipe_id"],
            "recipe_title": title,
        }, ui_events

    if name == "clear_slot":
        day = int(tool_input["day"])
        meal_type = MealType(tool_input["meal_type"])
        week_start = _parse_date(tool_input.get("week_start"))
        clear_slot(day=day, meal_type=meal_type, week_start=week_start, db=db)
        ui_events.append(
            {
                "type": "action",
                "action": "clear_slot",
                "day": day,
                "day_name": DAYS[day],
                "meal_type": meal_type.value,
            }
        )
        return {"cleared": True, "day": day, "meal_type": meal_type.value}, ui_events

    if name == "autogenerate_week":
        week_start = _parse_date(tool_input.get("week_start"))
        week = await autogenerate(week_start=week_start, db=db)
        ui_events.append({"type": "action", "action": "autogenerate_week"})
        return week.model_dump(), ui_events

    if name == "get_grocery_list":
        start = _monday(_parse_date(tool_input.get("week_start")) or date.today())
        slots = db.query(MealPlan).filter(MealPlan.week_start_date == start).all()
        if not slots:
            return {"error": "No meal plan for this week."}, ui_events
        return build_grocery_list(start, slots), ui_events

    if name == "get_profile":
        profile = db.query(UserProfile).filter(UserProfile.id == 1).first()
        allergens: list[str] = []
        diet = ""
        if profile:
            diet = profile.diet_type or ""
            try:
                allergens = json.loads(profile.allergens_json or "[]")
            except json.JSONDecodeError:
                pass
        return {"diet_type": diet, "allergens": allergens}, ui_events

    if name == "search_documents":
        hits = embed_svc.query_documents(
            tool_input["query"],
            n_results=int(tool_input.get("limit") or 4),
        )
        chunks = [
            {
                "filename": h.get("filename"),
                "chunk": h.get("chunk"),
                "text": h.get("document"),
                "distance": h.get("distance"),
            }
            for h in hits
        ]
        for h in hits:
            ui_events.append(
                {
                    "type": "citation",
                    "source": "document",
                    "filename": h.get("filename"),
                    "chunk": h.get("chunk"),
                }
            )
        return {"chunks": chunks}, ui_events

    return {"error": f"Unknown tool: {name}"}, ui_events


def build_rag_context(user_message: str, scan_ingredients: list[str] | None = None) -> str:
    """Retrieve RAG context to prepend to the system prompt."""
    sections: list[str] = []

    memories = embed_svc.query_memory(user_message)
    if memories:
        sections.append("User preferences from past conversations:\n" + "\n".join(f"- {m}" for m in memories))

    recipe_hits = embed_svc.query_recipes(user_message, n_results=4)
    if recipe_hits:
        lines = [
            f"- {h.get('title')} (id={h.get('recipe_id')}, {h.get('protein', 0):.0f}g protein)"
            for h in recipe_hits
        ]
        sections.append("Relevant cached recipes:\n" + "\n".join(lines))

    doc_hits = embed_svc.query_documents(user_message, n_results=3)
    if doc_hits:
        lines = [f"- [{h.get('filename')}] {h.get('document', '')[:200]}…" for h in doc_hits]
        sections.append("Relevant uploaded documents:\n" + "\n".join(lines))

    if scan_ingredients:
        sections.append(
            "Fridge scan ingredients (use these when planning):\n"
            + ", ".join(scan_ingredients)
        )

    if not sections:
        return ""
    return "\n\n".join(sections)


async def condense_memory(session_id: str, messages: list[dict]) -> str | None:
    """Summarize recent conversation and store in the memory collection."""
    if not messages:
        return None

    transcript = []
    for msg in messages[-20:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = json.dumps(content)
        transcript.append(f"{role}: {content}")

    client = _client()
    summary_msg = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": (
                    "Summarize this meal-planning conversation in 2–4 sentences. "
                    "Focus on food preferences, dislikes, dietary notes, and goals mentioned. "
                    "Write in third person about the user.\n\n"
                    + "\n".join(transcript)
                ),
            }
        ],
    )
    summary = summary_msg.content[0].text.strip()
    embed_svc.upsert_memory(session_id, summary)
    return summary


async def run_agent(
    db: Session,
    messages: list[dict],
    rag_context: str = "",
) -> AsyncIterator[dict]:
    """
    Run the agent loop, yielding SSE event dicts:
    token | tool_call | tool_result | action | citation | error | done
    """
    client = _client()
    system = SYSTEM_PROMPT
    if rag_context:
        system += f"\n\n--- Retrieved context ---\n{rag_context}"

    working_messages = list(messages)

    for _ in range(MAX_TOOL_ROUNDS):
        current_text = ""

        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                system=system,
                messages=working_messages,
                tools=TOOLS,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta" and delta.text:
                            current_text += delta.text
                            yield {"type": "token", "content": delta.text}

                final = stream.get_final_message()
        except Exception as exc:
            yield {"type": "error", "content": str(exc)}
            yield {"type": "done"}
            return

        assistant_content: list[dict] = []
        tool_uses: list[dict] = []
        for block in final.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
                tool_uses.append(
                    {"id": block.id, "name": block.name, "input": block.input}
                )

        working_messages.append({"role": "assistant", "content": assistant_content})

        if final.stop_reason != "tool_use":
            yield {"type": "done", "content": current_text}
            return

        tool_result_blocks: list[dict] = []
        for tu in tool_uses:
            tid = tu["id"]

            yield {
                "type": "tool_call",
                "name": tu["name"],
                "input": tu["input"],
            }

            try:
                result, ui_events = await execute_tool(tu["name"], tu["input"], db)
            except Exception as exc:
                result = {"error": str(exc)}

            yield {
                "type": "tool_result",
                "name": tu["name"],
                "result": result,
            }
            for ev in ui_events:
                yield ev

            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tid,
                    "content": json.dumps(result, default=str),
                }
            )

        working_messages.append({"role": "user", "content": tool_result_blocks})

    yield {"type": "error", "content": "Too many tool rounds."}
    yield {"type": "done"}

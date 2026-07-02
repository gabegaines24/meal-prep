---
name: Meal Planner App
overview: "Personal meal planning app with nutrition-driven meal planning, grocery lists, and a RAG-powered meal-planning copilot. React/Vite frontend, FastAPI + SQLite backend, Spoonacular for recipes, Claude for fridge scanning and agent reasoning, ChromaDB for vector search, Resend for weekly digest."
todos:
  - id: phase1-scaffold
    content: "Backend + frontend scaffold, core routes, planner UI, scanner, email digest, config files"
    status: completed
  - id: remove-pricing
    content: "Remove Kroger integration, BudgetTracker, estimated_cost, and store/budget fields from Profile"
    status: completed
  - id: nutrition-autogenerate
    content: "Improve /meals/autogenerate to optimize weekly plan against all macro goals with favorites-first"
    status: completed
  - id: recipe-discovery
    content: "Search respects diet/allergens, fetch full nutrition on assign, favorites tab in planner drawer"
    status: completed
  - id: grocery-list-core
    content: "Grocery list JSON endpoint, categorization, in-app GroceryList view with checkboxes"
    status: completed
  - id: grocery-list-email
    content: "Simplify email digest and file exports to nutrition-focused grocery list (no prices)"
    status: completed
  - id: cleanup-deps
    content: "Remove unused Zustand dependency; update README and .env.example"
    status: completed
  - id: rag-index
    content: "Embed cached recipes into ChromaDB; index title, macros, ingredients, instructions per document"
    status: completed
  - id: rag-agent-tools
    content: "Define Claude tool-use functions mirroring existing FastAPI routes for the agent to call"
    status: completed
  - id: rag-chat-route
    content: "Build POST /chat streaming SSE route — retrieves context from Chroma, invokes agent loop"
    status: completed
  - id: rag-doc-ingest
    content: "Route + UI for uploading custom documents (PDFs, text) into the vector store"
    status: completed
  - id: rag-chat-ui
    content: "Chat panel component + Chat page wired to /chat SSE; show citations and action confirmations"
    status: completed
  - id: rag-scan-agent
    content: "Upgrade fridge scanner to launch the agent with scan results instead of returning a static list"
    status: completed
  - id: rag-memory
    content: "Persist condensed conversation summaries per session; retrieve on new chat for preference memory"
    status: completed
isProject: false
---

# Meal Planner App — Build Plan

## Current Status

**Phase 1 and Phase 2 are complete.** The app focuses on nutrition-driven meal planning and grocery lists. Store pricing has been removed.

**Phase 3 is complete.** RAG-powered copilot with chat UI, agent tool-use, document ingest, fridge scan handoff, and conversation memory.

**Phase 4 is complete.** Budget-aware pricing with zip-based Walmart estimates (Apify), Spoonacular `maxPrice` filtering, USDA fallback, AP-style price cache, priced grocery lists, and budget-aware autogenerate.

---

## Product Focus

| In scope | Out of scope (for now) |
|----------|------------------------|
| Search and cache recipes with full nutrition data | Multi-retailer store picker |
| Set daily macro goals (calories, protein, carbs, fat) | Real-time cart checkout |
| Auto-generate a week that hits macro targets | GPS geolocation (zip only) |
| Build grocery lists from planned meals | |
| Diet type + allergen filters on search | |
| Weekly budget + per-meal price filtering | |
| Walmart price estimates by zip (Apify) + priced grocery lists | |
| USDA commodity price fallback (AP cache) | |
| Fridge scan → ingredient-based recipe suggestions | |
| RAG over recipe cache + custom documents | |
| Agent copilot with tool-use (plan, assign, generate) | |
| Preference memory across conversations | |

---

## Architecture

```mermaid
flowchart TD
    subgraph frontend [React / Vite Frontend]
        WeeklyPlanner[WeeklyPlanner]
        MacroSummary[MacroSummary]
        GroceryList[GroceryList]
        FridgeScanner[FridgeScanner]
        Chat[ChatPanel]
        GoalsPage[Goals]
    end

    subgraph backend [FastAPI Backend]
        meals_route["/meals"]
        recipes_route["/recipes"]
        goals_route["/goals"]
        profile_route["/profile"]
        scan_route["/scan"]
        files_route["/files"]
        email_route["/email"]
        chat_route["/chat (SSE)"]
        ingest_route["/ingest"]
    end

    subgraph services [Services]
        spoonacular[spoonacular.py]
        claude[claude.py]
        resend_svc[resend.py]
        file_gen[file_gen.py]
        grocery[grocery.py]
        agent[agent.py]
        embeddings[embeddings.py]
    end

    subgraph vector [Vector Store]
        chroma[(ChromaDB)]
        recipe_collection[recipes collection]
        docs_collection[documents collection]
        memory_collection[conversation memory]
    end

    subgraph db [SQLite via SQLAlchemy]
        MealPlan[meal_plans]
        Recipe[recipes]
        MacroGoals[macro_goals]
        UserProfile[user_profile]
        ChatHistory[chat_history]
    end

    Chat --> chat_route
    FridgeScanner --> scan_route
    WeeklyPlanner --> meals_route

    chat_route --> agent
    agent --> embeddings
    agent --> claude
    agent --> meals_route
    agent --> recipes_route
    agent --> goals_route
    agent --> files_route

    embeddings --> chroma
    chroma --> recipe_collection
    chroma --> docs_collection
    chroma --> memory_collection

    scan_route --> agent
    ingest_route --> embeddings

    meals_route --> MealPlan
    recipes_route --> Recipe
    chat_route --> ChatHistory
```

---

## Project Structure

```
meal-prep/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models/models.py          # Recipe, MealPlan, MacroGoals, UserProfile, ChatHistory
│   ├── routes/
│   │   ├── meals.py              # Week CRUD + autogenerate
│   │   ├── recipes.py            # Search, fetch, favorite
│   │   ├── goals.py              # Macro targets
│   │   ├── profile.py            # Diet + allergens
│   │   ├── scan.py               # Fridge photo → agent
│   │   ├── files.py              # Grocery list + recipe book exports
│   │   ├── email.py              # Weekly digest
│   │   ├── chat.py               # SSE chat endpoint, session management
│   │   └── ingest.py             # Upload + embed custom documents
│   └── services/
│       ├── spoonacular.py
│       ├── claude.py             # Image detection + agent LLM calls
│       ├── resend.py
│       ├── file_gen.py           # HTML generators
│       ├── grocery.py            # Ingredient aggregation + categorization
│       ├── agent.py              # Agent loop, tool dispatch, response streaming
│       └── embeddings.py         # ChromaDB client, upsert/query helpers
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── WeeklyPlanner.tsx
│       │   ├── MacroSummary.tsx
│       │   ├── RecipeCard.tsx
│       │   ├── FridgeScanner.tsx
│       │   ├── GroceryList.tsx
│       │   └── ChatPanel.tsx     # Message thread, streaming tokens, action cards
│       ├── pages/
│       │   ├── Planner.tsx
│       │   ├── Goals.tsx
│       │   ├── Scanner.tsx
│       │   ├── Profile.tsx
│       │   └── Chat.tsx          # Full chat page with doc upload
│       └── api/
│           ├── meals.ts
│           ├── recipes.ts
│           ├── files.ts
│           ├── profile.ts
│           └── chat.ts           # SSE client wrapper
├── .env.example
├── .gitignore
└── README.md
```

---

## Database Schema

**Existing (unchanged):**
- **recipes** — `id`, `spoonacular_id`, `title`, `image_url`, `calories`, `protein`, `carbs`, `fat`, `ingredients_json`, `instructions_json`, `favorited`, `source_url`
- **meal_plans** — `id`, `week_start_date`, `day_of_week` (0–6), `meal_type` (breakfast/lunch/dinner), `recipe_id` (FK)
- **macro_goals** — `id`, `calories`, `protein`, `carbs`, `fat` (single-row)
- **user_profile** — `id`, `allergens_json`, `diet_type`

**New for Phase 3:**
- **chat_history** — `id`, `session_id`, `role` (user/assistant/tool), `content`, `created_at`
- **chat_memory** — `id`, `session_id`, `summary`, `created_at` (condensed per-session preference summaries)

**Vector collections (ChromaDB):**
- **recipes** — one document per cached recipe; metadata: `recipe_id`, `title`, `calories`, `protein`, `carbs`, `fat`, `diet_type`, `favorited`
- **documents** — user-uploaded files chunked into ~500-token passages; metadata: `filename`, `page`, `source`
- **memory** — condensed conversation summaries per session

---

## Phase 1 — Completed

1. Backend scaffolding (`database.py`, models, `main.py`, CORS, APScheduler Sunday 18:00 cron)
2. Meals + recipes routes + Spoonacular service
3. React frontend: Vite, WeeklyPlanner, RecipeCard, API wrappers
4. MacroGoals page + MacroSummary component
5. FridgeScanner + Claude scan route
6. Weekly email via Resend + manual send from planner
7. `.env.example`, `.gitignore`, README
8. File exports (grocery list HTML, recipe book HTML)
9. User profile with diet/allergens

---

## Phase 2 — Completed

1. Removed Kroger pricing, BudgetTracker, store/budget profile fields
2. Multi-macro autogenerate (protein-weighted scoring, favorites-first, Spoonacular seeding)
3. Recipe flow — full nutrition on assign, favorites tab in planner drawer, macro gap banner
4. Grocery list — JSON endpoint, in-app categorized view with localStorage checkboxes
5. Simplified email/exports — ingredient checklist, no pricing
6. Removed Zustand, updated README and `.env.example`

---

## Phase 3 — RAG Copilot

### Overview

Add a persistent chat panel powered by a Claude agent with tool-use. The agent retrieves context from ChromaDB (recipe embeddings + user-uploaded documents + conversation memory) before responding, and can take actions on the meal plan directly through tool calls.

**Example interactions:**
- "What am I making Thursday?" → reads meal plan
- "High protein week, no dairy" → calls autogenerate with profile context
- "Swap Tuesday dinner for something under 500 cal" → semantic recipe search → assigns slot
- "I scanned my fridge — plan 3 dinners from what I have" → fridge scan + agent planning
- "Make something like my mom's chili but fit my macros" → RAG over uploaded docs
- "Am I on track for protein this week?" → reads macro totals, explains gap

---

### 3a. Embeddings + vector store

**New:** `backend/services/embeddings.py`

- ChromaDB (local persistent mode, no server needed)
- Two collections: `recipes` and `documents`
- Recipe embedding text: `"{title}. Macros: {cal}kcal, {protein}g protein, {carbs}g carbs, {fat}g fat. Ingredients: {ingredients}. Instructions: {instructions}"`
- Embed on: recipe upsert (add to existing `_upsert_recipe`), and a one-time backfill endpoint `POST /ingest/backfill`
- Query: top-k cosine similarity, return recipe IDs or doc chunk text
- Embedding model: `text-embedding-3-small` (OpenAI) **or** Anthropic embeddings (same API key already in use)

> Note: if staying Claude-only, use a lightweight local model (e.g. `sentence-transformers`) or switch to OpenAI embeddings — both are small additions to `requirements.txt`.

---

### 3b. Agent tools

**New:** `backend/services/agent.py`

Define Claude tool-use functions. Each tool maps to an existing backend capability:

| Tool name | What it does |
|-----------|-------------|
| `get_current_week` | Returns the week's slots and macro totals |
| `get_macro_goals` | Returns daily macro targets |
| `search_recipes_semantic` | Queries ChromaDB recipe collection |
| `search_recipes_spoonacular` | Calls Spoonacular (fallback for fresh results) |
| `assign_slot` | PUT a recipe to a day/meal slot |
| `clear_slot` | DELETE a slot |
| `autogenerate_week` | POST /meals/autogenerate |
| `get_grocery_list` | Returns structured ingredient list |
| `get_profile` | Returns diet + allergens |
| `search_documents` | Queries ChromaDB documents collection |

The agent loop:
1. Retrieve relevant context (recent memory + RAG top-k)
2. Call Claude with system prompt + conversation history + retrieved context + tool definitions
3. If Claude returns tool calls → execute → append results → loop
4. Stream final text response tokens to the client via SSE

---

### 3c. Chat route

**New:** `backend/routes/chat.py`

```
POST /chat
Body: { session_id, message, context?: { scan_result? } }
Response: SSE stream of { type: "token"|"tool_call"|"tool_result"|"done" }
```

- Session ID (UUID from frontend) scopes history and memory
- On each request: load last N messages + retrieve memory summary + run agent loop
- Persist each turn to `chat_history` table
- After N turns, condense history into a memory summary embedding and store in `memory` collection

---

### 3d. Document ingest

**New:** `backend/routes/ingest.py`

```
POST /ingest/document  — multipart upload (PDF or text)
POST /ingest/backfill  — embed all existing cached recipes
GET  /ingest/documents — list indexed documents
DELETE /ingest/documents/{id} — remove from vector store
```

- PDFs parsed with `pypdf`
- Chunk at ~500 tokens with 50-token overlap
- Each chunk embedded and upserted into `documents` collection
- Metadata: filename, chunk index, page number

---

### 3e. Chat UI

**New:** `frontend/src/components/ChatPanel.tsx` + `frontend/src/pages/Chat.tsx`

- Full page (`/chat`) reachable from nav
- Message thread: user bubbles left, assistant right, streaming tokens
- **Action cards** — when agent assigns a slot or autogenerates, show a confirmation card ("Added Grilled Salmon → Thursday dinner ✓")
- **Citation chips** — when agent retrieves a recipe from RAG, show the source recipe name as a tappable chip
- Input bar with optional image attachment (triggers fridge scan → agent instead of the standalone scanner)
- Doc upload button → `POST /ingest/document`
- After agent completes an action, invalidate React Query keys (`["week"]`, `["grocery-list"]`) so planner updates live

---

### 3f. Upgrade fridge scanner to agent entry point

Current: `POST /scan` → Claude vision → ingredient list → Spoonacular suggestions → static list.

Phase 3: after extracting ingredients, hand off to the agent:
```
"I found these ingredients in your fridge: [eggs, spinach, chicken, lemon].
 Your goals are 2500 kcal, 180g protein. You have 3 empty dinner slots this week.
 Plan those dinners using what's available."
```

The agent can then call `search_recipes_semantic`, `assign_slot`, and `get_grocery_list` to produce a natural-language plan with actions taken.

---

### 3g. Conversation memory

After every 10 turns:
1. Call Claude to summarize the session: preferences, dislikes, frequently used recipes, goals mentioned
2. Embed the summary
3. Upsert into `memory` collection keyed by `session_id`
4. On future sessions, retrieve similar memories at start of each conversation

This lets the agent say "I remember you said you don't like cilantro" without re-reading full history.

---

## API Summary

| Route | Purpose |
|-------|---------|
| `GET /health` | Health check |
| `GET /meals?week_start=` | Week plan + daily/weekly macro totals |
| `PUT /meals/{day}/{meal_type}` | Assign recipe to slot |
| `DELETE /meals/{day}/{meal_type}` | Clear slot |
| `POST /meals/autogenerate` | Fill empty slots using macro goals |
| `GET /recipes/search?query=` | Spoonacular search (respects profile filters) |
| `GET /recipes/{id}` | Fetch + cache recipe |
| `POST /recipes/{id}/favorite` | Toggle favorite |
| `GET/PUT /goals` | Daily macro targets |
| `GET/PUT /profile` | Diet type + allergens + zip + budget |
| `GET /files/budget-summary` | Weekly budget vs estimated grocery total |
| `POST /scan` | Image → agent → plan actions |
| `GET /files/grocery-list/data` | Grocery list JSON |
| `GET /files/grocery-list` | Grocery list HTML download |
| `GET /files/recipe-book` | Recipe book HTML download |
| `POST /email/send` | Send weekly digest |
| `POST /chat` | SSE agent chat stream |
| `POST /ingest/document` | Upload + embed a document |
| `POST /ingest/backfill` | Embed all cached recipes |
| `GET /ingest/documents` | List indexed documents |
| `DELETE /ingest/documents/{id}` | Remove document from index |

---

## Environment Variables

```
ANTHROPIC_API_KEY=        # Claude (vision + agent reasoning)
SPOONACULAR_API_KEY=      # Recipe search + nutrition
RESEND_API_KEY=           # Weekly email digest
EMAIL_RECIPIENT=          # Digest recipient address
APIFY_API_TOKEN=          # Optional — Apify Walmart grocery price estimates
CHROMA_PATH=./chroma_db   # Local ChromaDB index path
```

---

## Phase 4 — Budget-Aware Pricing & Location

### Overview

Reintroduce budget as a planning constraint without regressing macro goals, RAG copilot, or grocery list UX. Uses **Apify Walmart (two-tier) + Spoonacular `maxPrice` + USDA fallback** with AP-style cached prices (never block UI on Apify outage).

### 4a. Profile + schema

- `UserProfile`: `zip_code`, `weekly_budget` (legacy `store_name` / `kroger_location_id` columns unused)
- `Recipe`: `estimated_cost_per_serving`, `price_source`
- `price_cache` table with 24h Walmart / 30d USDA TTL (zip-scoped via `location_id`)

### 4b. Pricing layer

- `backend/services/apify_walmart.py` — Tier 1 Unfenced search+zip, Tier 2 detail enrichment
- `backend/services/usda.py` — commodity fallback from bundled JSON
- `backend/services/pricing.py` — orchestrator: cache → Apify → USDA

### 4c. Recipe search + autogenerate

- Spoonacular `maxPrice` when `weekly_budget > 0` (per-meal = budget / 21)
- Autogenerate soft penalty + hard per-meal cap when budget set

### 4d. Priced grocery + exports

- `build_grocery_list()` returns item prices + `budget_summary`
- HTML exports: price column, budget bar, "Estimated Walmart prices for ZIP …" footer
- Email attachments: separate priced grocery list + recipe book

### 4e. Frontend

- Profile: zip + weekly budget (no store picker)
- `BudgetTracker` on planner, cost badge on `RecipeCard`, prices in `GroceryList`

### 4f. Agent

- Extended `get_profile`, `get_budget_summary`; system prompt respects weekly budget

---

## Build Order (Phase 3)

1. **Embeddings service** — ChromaDB setup, `embeddings.py`, backfill endpoint for existing recipes
2. **Agent tools** — `agent.py` with tool definitions, Claude tool-use loop, SSE streaming
3. **Chat route** — `POST /chat`, session + history persistence, memory condensation
4. **Chat UI** — `ChatPanel.tsx`, `Chat.tsx`, SSE client, action cards, citation chips
5. **Doc ingest** — `ingest.py`, PDF parsing, chunk + embed pipeline, document management UI
6. **Scanner upgrade** — wire scan results into agent instead of static Spoonacular list
7. **Memory** — per-session preference summaries, retrieval at conversation start

---

## Build Order (Phase 4)

1. **Schema + profile** — UserProfile budget/zip fields, `price_cache` table
2. **Pricing layer** — `apify_walmart.py`, `usda.py`, `pricing.py` with AP cache (24h Walmart, 30d USDA)
3. **Recipe budget filter** — Spoonacular `maxPrice`, `estimated_cost_per_serving` on recipes
4. **Budget autogenerate** — soft/hard cost scoring in `/meals/autogenerate`
5. **Priced grocery + exports** — JSON/HTML grocery list with prices, email attachments
6. **Frontend** — Profile zip+budget, BudgetTracker, RecipeCard cost badge, GroceryList prices
7. **Agent** — `get_budget_summary`, extended `get_profile`

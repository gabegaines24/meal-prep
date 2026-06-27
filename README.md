# Meal Prep — Personal Meal Planner

A personal meal planning web app with a weekly calendar view, macro tracking, fridge scanning via AI image recognition, and a weekly email digest.

**Stack:** React (Vite) · FastAPI · SQLite · Claude API · Spoonacular API · Resend

---

## Features

- **Weekly Meal Planner** — Mon–Sun calendar with breakfast, lunch, and dinner slots. Assign recipes manually or auto-generate a full week based on your macro goals.
- **Macro Tracking** — Set daily targets for calories, protein, carbs, and fat. Each recipe displays its macros and the weekly view shows progress toward your goals.
- **Recipe Database** — Search recipes and nutrition data via the Spoonacular API. Favorited and used recipes are cached locally in SQLite.
- **Fridge Scanner** — Upload a photo of your fridge. Claude identifies the ingredients and Spoonacular suggests matching recipes.
- **Weekly Email Digest** — Every Sunday at 6 PM, an automated email delivers the upcoming week's meal plan, a macro summary, and an aggregated shopping list.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A free account at each of the four API providers listed below

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd "meal prep"
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your four API keys (see [API Keys](#api-keys) below).

### 3. Backend

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Start the API server (runs on http://localhost:8000)
uvicorn backend.main:app --reload
```

### 4. Frontend

```bash
cd frontend
npm install

# Start the dev server (runs on http://localhost:5173)
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## API Keys

All four services have a free tier sufficient for personal use.

| Key | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `SPOONACULAR_API_KEY` | [spoonacular.com/food-api](https://spoonacular.com/food-api) — 150 points/day free |
| `RESEND_API_KEY` | [resend.com/api-keys](https://resend.com/api-keys) — 3,000 emails/month free |
| `EMAIL_RECIPIENT` | Your own email address (recipient of the weekly digest) |

---

## Project Structure

```
meal prep/
├── backend/
│   ├── main.py               # FastAPI app, CORS, APScheduler cron
│   ├── database.py           # SQLAlchemy engine + session
│   ├── models/models.py      # ORM: Recipe, MealPlan, MacroGoals
│   ├── routes/               # meals, recipes, scan, email
│   ├── services/             # claude, spoonacular, resend
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/       # WeeklyPlanner, MacroSummary, FridgeScanner, RecipeCard
│       ├── pages/            # Planner, Goals, Scanner
│       └── api/              # typed fetch wrappers
├── .env.example
├── .gitignore
└── PLAN.md                   # architecture and build-order notes
```

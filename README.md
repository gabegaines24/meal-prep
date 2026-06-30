# Meal Prep — Personal Meal Planner

A personal meal planning web app with a weekly calendar view, macro tracking, nutrition-driven auto-generate, grocery lists, fridge scanning via AI image recognition, an AI meal copilot, and a weekly email digest.

**Stack:** React (Vite) · FastAPI · SQLite · Claude API · Spoonacular API · ChromaDB · Resend

---

## Features

- **Weekly Meal Planner** — Mon–Sun calendar with breakfast, lunch, and dinner slots. Assign recipes manually or auto-generate a full week scored against your macro goals.
- **Macro Tracking** — Set daily targets for calories, protein, carbs, and fat. Each recipe displays its macros and the planner shows weekly progress and gaps.
- **Grocery Lists** — Ingredients from your planned meals are aggregated, categorized, and shown in-app with checkboxes. Download a printable HTML list or get it in your weekly email.
- **Recipe Library** — Search recipes via Spoonacular (respects diet and allergen settings). Favorite recipes for faster planning and auto-generate.
- **Fridge Scanner** — Upload a photo of your fridge. Claude identifies ingredients and Spoonacular suggests matching recipes. Hand off to the copilot to plan meals from what you have.
- **AI Meal Copilot** — Chat with an agent that reads your plan, searches recipes and uploaded documents (RAG), and can assign slots, autogenerate weeks, and build grocery lists.
- **Weekly Email Digest** — Every Sunday at 6 PM, an automated email delivers the upcoming week's meal plan, macro summary, grocery list, and recipe book.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- API keys for Anthropic, Spoonacular, and Resend (see below)

---

## Setup

### 1. Clone the repo

```bash
git clone <repo-url>
cd meal-prep
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys (see [API Keys](#api-keys) below).

### 3. Backend

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r backend/requirements.txt

uvicorn backend.main:app --reload
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## API Keys

| Key | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `SPOONACULAR_API_KEY` | [spoonacular.com/food-api](https://spoonacular.com/food-api) — 150 points/day free |
| `RESEND_API_KEY` | [resend.com/api-keys](https://resend.com/api-keys) — 3,000 emails/month free |
| `EMAIL_RECIPIENT` | Your own email address (recipient of the weekly digest) |

---

## Project Structure

```
meal-prep/
├── backend/
│   ├── main.py
│   ├── models/models.py
│   ├── routes/          # meals, recipes, goals, profile, scan, files, email
│   └── services/        # spoonacular, claude, resend, file_gen, grocery
├── frontend/
│   └── src/
│       ├── components/  # WeeklyPlanner, GroceryList, MacroSummary, RecipeCard, FridgeScanner
│       ├── pages/       # Planner, Goals, Scanner, Profile
│       └── api/
├── .env.example
└── PLAN.md
```

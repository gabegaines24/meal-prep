from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Base, engine
from backend.routes import email, files, goals, meals, profile, recipes, scan


def create_tables():
    Base.metadata.create_all(bind=engine)


def send_weekly_digest():
    """Called by APScheduler every Sunday at 18:00."""
    import httpx

    try:
        httpx.post("http://localhost:8000/email/send", timeout=30)
    except Exception as exc:
        print(f"Weekly digest cron failed: {exc}")


scheduler = BackgroundScheduler()
scheduler.add_job(
    send_weekly_digest,
    CronTrigger(day_of_week="sun", hour=18, minute=0),
    id="weekly_digest",
    replace_existing=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Meal Planner API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meals.router, prefix="/meals", tags=["meals"])
app.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
app.include_router(scan.router, prefix="/scan", tags=["scan"])
app.include_router(email.router, prefix="/email", tags=["email"])
app.include_router(goals.router, prefix="/goals", tags=["goals"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(files.router, prefix="/files", tags=["files"])


@app.get("/health")
def health():
    return {"status": "ok"}
